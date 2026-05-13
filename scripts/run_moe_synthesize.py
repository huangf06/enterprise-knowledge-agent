#!/usr/bin/env python3
"""Frontier #4 Multi-LLM MoE: synthesize-only Pareto experiment (Sprint 5).

Replay-mode runner. Takes a baseline eval JSON, holds plan/tool_history
constant, and re-runs ONLY the synthesize node against four routes:

  - deepseek: DeepSeek-V4-Pro via the Anthropic-compatible endpoint (baseline)
  - anthropic_sonnet: claude-sonnet-4-6 via api.anthropic.com
  - anthropic_haiku: claude-haiku-4-5-20251001 via api.anthropic.com
  - openai_gpt4o_mini: gpt-4o-mini via api.openai.com

Each route runs on the fast-tier (10 scenarios). The output JSON groups rows
by route so a downstream comparison can emit the cost / quality Pareto table.

Why synthesize-only: the synthesize node returns plain text (no tool_use), so
no cross-vendor tool schema translation is needed; that lets us measure
"which vendor writes the best answer given the same evidence" in isolation.
The Sprint 5 scaffold doc notes a full agent-level MoE route would also need
tool_use schema translation for plan/tool_select/reflect which is deferred.

Usage:
  uv run python scripts/run_moe_synthesize.py \\
    --baseline eval_results/runs/eval-20260513-105857.json \\
    --tier fast
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

import anthropic  # noqa: E402
from openai import OpenAI  # noqa: E402

from src.agent.prompts import render  # noqa: E402
from src.eval.citation import citation_groundedness  # noqa: E402
from src.eval.judge import judge  # noqa: E402
from src.eval.scenarios import load_scenarios  # noqa: E402
from src.eval.trajectory import trajectory_metrics  # noqa: E402
from src.llm.anthropic_client import messages_create as deepseek_messages  # noqa: E402

# Pricing in USD per 1M tokens; aligned with src/llm/moe_router.PRICING_USD_PER_1M
PRICING = {
    "deepseek": {"in": 0.14, "out": 0.28},
    "anthropic_sonnet": {"in": 3.00, "out": 15.00},
    "anthropic_haiku": {"in": 1.00, "out": 5.00},
    "openai_gpt4o_mini": {"in": 0.15, "out": 0.60},
}

FAST_IDS = (
    "brief-003", "brief-008",
    "decision-003", "decision-005",
    "qa-003", "qa-006",
    "conflict-001", "conflict-003",
    "multi-002", "multi-003",
)

ROUTES = ("deepseek", "anthropic_sonnet", "anthropic_haiku", "openai_gpt4o_mini")


def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "(no tool calls were made)"
    lines = []
    for i, h in enumerate(history, 1):
        lines.append(f"--- call {i}: {h['tool']}({h['args']}) ---\n{h['result']}")
    return "\n\n".join(lines)


def _build_prompt(scenario, plan: str, tool_history: list[dict[str, Any]]) -> str:
    return render(
        "synthesize",
        query=scenario.question,
        user_name=scenario.user_name,
        user_role=scenario.user_role,
        plan=plan,
        tool_history=_format_history(tool_history),
    )


def _call_deepseek(prompt: str) -> tuple[str, int, int]:
    resp = deepseek_messages(
        messages=[{"role": "user", "content": prompt}], max_tokens=4096, node="synthesize_moe"
    )
    text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    in_tok = getattr(resp.usage, "input_tokens", 0) or 0
    out_tok = getattr(resp.usage, "output_tokens", 0) or 0
    return text, in_tok, out_tok


def _call_anthropic_official(prompt: str, model: str) -> tuple[str, int, int]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set; required for anthropic_* routes")
    client = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    in_tok = getattr(resp.usage, "input_tokens", 0) or 0
    out_tok = getattr(resp.usage, "output_tokens", 0) or 0
    return text, in_tok, out_tok


def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> tuple[str, int, int]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set; required for openai_* routes")
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        max_completion_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = (resp.choices[0].message.content or "").strip()
    usage = resp.usage
    in_tok = getattr(usage, "prompt_tokens", 0) or 0
    out_tok = getattr(usage, "completion_tokens", 0) or 0
    return text, in_tok, out_tok


def _route(route: str, prompt: str) -> tuple[str, int, int]:
    if route == "deepseek":
        return _call_deepseek(prompt)
    if route == "anthropic_sonnet":
        return _call_anthropic_official(prompt, model="claude-sonnet-4-6")
    if route == "anthropic_haiku":
        return _call_anthropic_official(prompt, model="claude-haiku-4-5-20251001")
    if route == "openai_gpt4o_mini":
        return _call_openai(prompt, model="gpt-4o-mini")
    raise ValueError(f"unknown route: {route}")


def _cost_usd(route: str, in_tok: int, out_tok: int) -> float:
    px = PRICING[route]
    return (in_tok * px["in"] + out_tok * px["out"]) / 1_000_000


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True, help="Baseline eval JSON")
    p.add_argument("--tier", choices=("smoke", "fast", "full"), default="fast")
    p.add_argument(
        "--routes",
        default=",".join(ROUTES),
        help=f"Comma-separated routes. Default: {','.join(ROUTES)}",
    )
    p.add_argument("--out", default=None)
    args = p.parse_args()

    selected_routes = [r.strip() for r in args.routes.split(",") if r.strip()]
    for r in selected_routes:
        if r not in ROUTES:
            raise SystemExit(f"unknown route: {r}")

    baseline_path = Path(args.baseline)
    data = json.loads(baseline_path.read_text())
    base_rows = data["rows"]
    if args.tier == "fast":
        wanted = set(FAST_IDS)
        base_rows = [r for r in base_rows if r["scenario_id"] in wanted]
    elif args.tier == "smoke":
        base_rows = base_rows[:3]

    scenarios = {s.id: s for s in load_scenarios()}
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_path = (
        Path(args.out)
        if args.out
        else REPO_ROOT / "eval_results" / "runs" / f"moe-synthesize-{stamp}.json"
    )

    print(
        f"MoE synthesize replay\n"
        f"  baseline: {baseline_path.name}\n"
        f"  scenarios: {len(base_rows)} (tier={args.tier})\n"
        f"  routes: {selected_routes}",
        flush=True,
    )

    started = time.time()
    out_rows: list[dict[str, Any]] = []
    for i, br in enumerate(base_rows, 1):
        sid = br["scenario_id"]
        sc = scenarios.get(sid)
        if sc is None or not br.get("ok") or not br.get("tool_history"):
            print(f"  [{i}/{len(base_rows)}] SKIP {sid}", flush=True)
            continue
        prompt = _build_prompt(sc, plan="", tool_history=br["tool_history"])
        tools_used = br.get("tools_used", [])
        for route in selected_routes:
            t0 = time.time()
            try:
                answer, in_tok, out_tok = _route(route, prompt)
                ok = bool(answer)
            except Exception as exc:  # noqa: BLE001
                answer = f"ROUTE ERROR ({route}): {exc}"
                in_tok = out_tok = 0
                ok = False
            elapsed = time.time() - t0
            cost = _cost_usd(route, in_tok, out_tok) if ok else 0.0

            scores = (
                judge(sc, answer, tools_used)
                if ok
                else {
                    "answer_correctness": 0.0,
                    "completeness": 0.0,
                    "tool_selection_quality": 0.0,
                    "governance_compliance": 1.0,
                    "action_recommend_quality": 0.0,
                    "_route_error": 1.0,
                }
            )
            citations = citation_groundedness(answer, br["tool_history"]) if ok else {
                "well_formedness": 0.0,
                "source_coverage": 0.0,
                "id_grounded": 0.0,
                "n_citations": 0,
                "n_brackets": 0,
            }
            trajectory = trajectory_metrics(tools_used, sc.expected_sources, len(br["tool_history"]))
            out_rows.append(
                {
                    "scenario_id": sid,
                    "category": sc.category,
                    "difficulty": sc.difficulty,
                    "route": route,
                    "ok": ok,
                    "answer": answer,
                    "scores": scores,
                    "citations": citations,
                    "trajectory": trajectory,
                    "elapsed_s": round(elapsed, 2),
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": round(cost, 6),
                    "tools_used": tools_used,
                }
            )
            print(
                f"  [{i}/{len(base_rows)}] {sid} ({route}) ac={scores.get('answer_correctness'):.2f} "
                f"cite={citations.get('id_grounded', 0):.2f} "
                f"t={round(elapsed, 1)}s cost=${cost:.6f}",
                flush=True,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "baseline": baseline_path.name,
        "routes": selected_routes,
        "tier": args.tier,
        "summary": _summarize(out_rows, selected_routes),
        "total_wallclock_s": round(time.time() - started, 2),
        "rows": out_rows,
    }
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nsaved: {out_path.relative_to(REPO_ROOT)}")
    for route in selected_routes:
        s = out["summary"].get(route, {})
        print(
            f"  [{route}] ac={s.get('answer_correctness')} cite_grounded={s.get('cite_id_grounded')} "
            f"avg_cost=${s.get('avg_cost_usd')} avg_latency={s.get('avg_elapsed_s')}s"
        )
    return 0


def _summarize(rows: list[dict[str, Any]], routes: list[str]) -> dict[str, Any]:
    metric_keys = (
        "answer_correctness",
        "completeness",
        "tool_selection_quality",
        "governance_compliance",
        "action_recommend_quality",
    )
    cite_keys = ("well_formedness", "source_coverage", "id_grounded")
    out: dict[str, Any] = {}
    for route in routes:
        subset = [r for r in rows if r["route"] == route and r.get("ok")]
        if not subset:
            continue
        agg: dict[str, float | int] = {}
        for k in metric_keys:
            vals = [r["scores"].get(k, 0.0) for r in subset]
            agg[k] = round(sum(vals) / len(vals), 4)
        for k in cite_keys:
            vals = [r.get("citations", {}).get(k, 0.0) for r in subset]
            agg[f"cite_{k}"] = round(sum(vals) / len(vals), 4)
        latencies = [r["elapsed_s"] for r in subset]
        costs = [r["cost_usd"] for r in subset]
        agg["avg_elapsed_s"] = round(sum(latencies) / len(latencies), 2)
        agg["avg_cost_usd"] = round(sum(costs) / len(costs), 6)
        agg["total_cost_usd"] = round(sum(costs), 6)
        agg["count"] = len(subset)
        out[route] = agg
    return out


if __name__ == "__main__":
    raise SystemExit(main())
