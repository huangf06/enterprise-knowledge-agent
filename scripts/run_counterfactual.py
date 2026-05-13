#!/usr/bin/env python3
"""Frontier #7 Counterfactual robustness ablation (Sprint 6).

Replay-mode runner. For each scenario in a baseline eval, perturb its
tool_history with each of the three v4.1-locked perturbations and re-run
ONLY the synthesize node + judge. The rest of the agent flow (plan, tools,
reflect, critique) is held constant by replaying the recorded tool_history
under perturbation, which is cheaper, fully reproducible, and isolates the
synthesize layer's robustness from upstream noise.

Three perturbations per the v4.1 plan:
  - entity_swap (R3): non-protagonist entity rename. Tests entity confusion.
  - noise_injection (P10): pad results with plausible-irrelevant chatter.
    Tests whether the agent gets distracted into citing the noise.
  - doc_deletion (P11): drop the most-cited paragraph. Tests graceful
    degradation when the canonical source disappears.

Usage:
  uv run python scripts/run_counterfactual.py \\
    --baseline eval_results/runs/eval-20260513-105857.json \\
    --out eval_results/runs/counterfactual-<stamp>.json

Output JSON has rows tagged with `perturbation` so downstream comparison can
slice by mode.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.agent.prompts import render  # noqa: E402
from src.eval.citation import citation_groundedness  # noqa: E402
from src.eval.counterfactual import perturb_tool_history  # noqa: E402
from src.eval.judge import judge  # noqa: E402
from src.eval.scenarios import load_scenarios  # noqa: E402
from src.eval.trajectory import trajectory_metrics  # noqa: E402
from src.llm.anthropic_client import messages_create  # noqa: E402
from src.llm.cost_ledger import query_window  # noqa: E402

PERTURBATIONS = ("entity_swap", "noise_injection", "doc_deletion")


def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "(no tool calls were made)"
    lines = []
    for i, h in enumerate(history, 1):
        lines.append(f"--- call {i}: {h['tool']}({h['args']}) ---\n{h['result']}")
    return "\n\n".join(lines)


def _run_synthesize(*, scenario, plan: str, tool_history: list[dict[str, Any]]) -> str:
    prompt = render(
        "synthesize",
        query=scenario.question,
        user_name=scenario.user_name,
        user_role=scenario.user_role,
        plan=plan,
        tool_history=_format_history(tool_history),
    )
    resp = messages_create(
        messages=[{"role": "user", "content": prompt}], max_tokens=4096, node="synthesize"
    )
    return "\n".join(b.text for b in resp.content if b.type == "text").strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline eval JSON (rows must have populated tool_history).",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output JSON path; default eval_results/runs/counterfactual-<stamp>.json",
    )
    p.add_argument(
        "--modes",
        default=",".join(PERTURBATIONS),
        help=f"Comma-separated perturbation modes. Default: {','.join(PERTURBATIONS)}",
    )
    p.add_argument("--limit", type=int, default=None, help="Process only the first N scenarios.")
    p.add_argument(
        "--tier",
        choices=("smoke", "fast", "full"),
        default=None,
        help="A5 3-tier preset (filters by scenario_id). Overrides --limit.",
    )
    args = p.parse_args()
    FAST_IDS = {
        "brief-003", "brief-008",
        "decision-003", "decision-005",
        "qa-003", "qa-006",
        "conflict-001", "conflict-003",
        "multi-002", "multi-003",
    }
    SMOKE_IDS = {"brief-003", "conflict-001", "qa-003"}

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in modes:
        if m not in PERTURBATIONS:
            raise SystemExit(f"unknown perturbation mode: {m}")

    baseline_path = Path(args.baseline)
    data = json.loads(baseline_path.read_text())
    base_rows = data["rows"]
    if args.tier == "fast":
        base_rows = [r for r in base_rows if r["scenario_id"] in FAST_IDS]
    elif args.tier == "smoke":
        base_rows = [r for r in base_rows if r["scenario_id"] in SMOKE_IDS]
    elif args.limit is not None:
        base_rows = base_rows[: args.limit]

    scenarios = {s.id: s for s in load_scenarios()}
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_path = (
        Path(args.out)
        if args.out
        else REPO_ROOT / "eval_results" / "runs" / f"counterfactual-{stamp}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Counterfactual replay from {baseline_path.name}\n"
        f"  scenarios: {len(base_rows)}\n"
        f"  modes: {modes}\n"
        f"  out: {out_path.relative_to(REPO_ROOT)}",
        flush=True,
    )

    started = time.time()
    out_rows: list[dict[str, Any]] = []
    for i, br in enumerate(base_rows, 1):
        sid = br["scenario_id"]
        sc = scenarios.get(sid)
        if sc is None or not br.get("ok") or not br.get("tool_history"):
            print(f"  [{i}/{len(base_rows)}] SKIP {sid} (no ok+tool_history)", flush=True)
            continue
        plan = ""  # baseline rows don't persist plan text; pass empty (synthesize tolerates)
        tools_used = br.get("tools_used", [])
        for mode in modes:
            perturbed = perturb_tool_history(br["tool_history"], mode=mode)
            t0 = time.time()
            iso_start = datetime.now(timezone.utc).isoformat()
            try:
                answer = _run_synthesize(scenario=sc, plan=plan, tool_history=perturbed)
                ok = True
            except Exception as exc:  # noqa: BLE001
                answer = f"SYNTHESIZE ERROR: {exc}"
                ok = False
            iso_end = datetime.now(timezone.utc).isoformat()
            usage = query_window(iso_start, iso_end)

            scores = (
                judge(sc, answer, tools_used)
                if ok
                else {
                    "answer_correctness": 0.0,
                    "completeness": 0.0,
                    "tool_selection_quality": 0.0,
                    "governance_compliance": 1.0,
                    "action_recommend_quality": 0.0,
                    "_synthesize_error": 1.0,
                }
            )
            citations = citation_groundedness(answer, perturbed) if ok else {
                "well_formedness": 0.0,
                "source_coverage": 0.0,
                "id_grounded": 0.0,
                "n_citations": 0,
                "n_brackets": 0,
            }
            trajectory = trajectory_metrics(tools_used, sc.expected_sources, len(perturbed))
            out_rows.append(
                {
                    "scenario_id": sid,
                    "category": sc.category,
                    "difficulty": sc.difficulty,
                    "perturbation": mode,
                    "ok": ok,
                    "answer": answer,
                    "scores": scores,
                    "citations": citations,
                    "trajectory": trajectory,
                    "elapsed_s": round(time.time() - t0, 2),
                    "agent_usage": usage,
                    "tools_used": tools_used,
                }
            )
            print(
                f"  [{i}/{len(base_rows)}] {sid} ({mode}) -> ac={scores.get('answer_correctness'):.2f} "
                f"gov={scores.get('governance_compliance'):.2f} cite={citations.get('id_grounded', 0):.2f} "
                f"t={round(time.time() - t0, 1)}s",
                flush=True,
            )

    out = {
        "baseline": baseline_path.name,
        "modes": modes,
        "total_wallclock_s": round(time.time() - started, 2),
        "summary": _summarize(out_rows, modes),
        "rows": out_rows,
    }
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"saved: {out_path.relative_to(REPO_ROOT)}")
    print()
    for mode in modes:
        s = out["summary"].get(mode, {})
        print(
            f"  [{mode}] ac={s.get('answer_correctness')} comp={s.get('completeness')} "
            f"gov={s.get('governance_compliance')} cite_grounded={s.get('cite_id_grounded')} "
            f"cite_cov={s.get('cite_source_coverage')}"
        )
    return 0


def _summarize(rows: list[dict[str, Any]], modes: list[str]) -> dict[str, Any]:
    metric_keys = (
        "answer_correctness",
        "completeness",
        "tool_selection_quality",
        "governance_compliance",
        "action_recommend_quality",
    )
    cite_keys = ("well_formedness", "source_coverage", "id_grounded")
    out: dict[str, Any] = {}
    for mode in modes:
        subset = [r for r in rows if r["perturbation"] == mode]
        if not subset:
            continue
        agg: dict[str, float] = {}
        for k in metric_keys:
            vals = [r["scores"].get(k, 0.0) for r in subset]
            agg[k] = round(sum(vals) / len(vals), 4)
        for k in cite_keys:
            vals = [r.get("citations", {}).get(k, 0.0) for r in subset]
            agg[f"cite_{k}"] = round(sum(vals) / len(vals), 4)
        agg["count"] = len(subset)
        out[mode] = agg
    return out


if __name__ == "__main__":
    raise SystemExit(main())
