#!/usr/bin/env python3
"""Frontier #7 Counterfactual: compare perturbed runs vs the baseline they replay from.

Reads the counterfactual JSON (which references its source baseline by name),
loads both, and emits a per-perturbation delta table. The load-bearing metric
is `governance_compliance` — if it stays at 1.0 across perturbations, the
governance layer is robust to the kind of noise these perturbations inject.

Usage:
  uv run python scripts/compare_counterfactual.py \\
    --counterfactual eval_results/runs/counterfactual-<stamp>.json \\
    --baseline eval_results/runs/eval-20260513-105857.json \\
    --out docs/sprint6_counterfactual_result.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

METRIC_KEYS = (
    "answer_correctness",
    "completeness",
    "tool_selection_quality",
    "governance_compliance",
    "action_recommend_quality",
)

CITE_KEYS = ("well_formedness", "source_coverage", "id_grounded")


def _base_summary(base_rows: list[dict], scenario_ids: set[str]) -> dict[str, float]:
    rows = [r for r in base_rows if r["scenario_id"] in scenario_ids and r.get("ok")]
    out: dict[str, float] = {}
    if not rows:
        return out
    for k in METRIC_KEYS:
        vals = [r["scores"].get(k, 0.0) for r in rows]
        out[k] = round(sum(vals) / len(vals), 4)
    for k in CITE_KEYS:
        vals = [r.get("citations", {}).get(k, 0.0) for r in rows]
        out[f"cite_{k}"] = round(sum(vals) / len(vals), 4)
    out["count"] = len(rows)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--counterfactual", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    cf = json.loads(Path(args.counterfactual).read_text())
    base_rows = json.loads(Path(args.baseline).read_text())["rows"]
    modes = cf["modes"]
    cf_rows = cf["rows"]

    scenario_ids = {r["scenario_id"] for r in cf_rows}
    base = _base_summary(base_rows, scenario_ids)

    lines = [
        "# Sprint 6 Frontier #7 Counterfactual robustness — ablation result",
        "",
        f"Baseline: `{Path(args.baseline).name}` (subset n={base.get('count', 0)})",
        f"Counterfactual: `{Path(args.counterfactual).name}` (3 modes × subset)",
        "",
        "Each perturbation modifies the tool_history that the synthesize node sees;",
        "the agent flow (plan + tool_select + tool_execute + reflect) is held constant",
        "by replay. The judge scores the new answer against the original scenario",
        "rubric — so a perturbed entity name lowers `answer_correctness` because the",
        "expected_topics no longer match, BUT `governance_compliance` must stay at 1.0",
        "for the governance layer to be called robust. That is the load-bearing test.",
        "",
        "| Metric | Baseline |",
    ]
    header_row = "|---|---:|"
    for mode in modes:
        lines[-1] += f" {mode} | Δ |"
        header_row += "---:|---:|"
    lines.append(header_row)
    summaries: dict[str, dict[str, float]] = cf.get("summary", {})
    for k in METRIC_KEYS:
        row = f"| {k} | {base.get(k, 0):.4f} |"
        for mode in modes:
            s = summaries.get(mode, {})
            v = s.get(k, 0.0)
            d = v - base.get(k, 0)
            sign = "+" if d > 0 else ""
            row += f" {v:.4f} | {sign}{d:.4f} |"
        lines.append(row)
    for k in CITE_KEYS:
        bk = f"cite_{k}"
        row = f"| cite_{k} | {base.get(bk, 0):.4f} |"
        for mode in modes:
            s = summaries.get(mode, {})
            v = s.get(bk, 0.0)
            d = v - base.get(bk, 0)
            sign = "+" if d > 0 else ""
            row += f" {v:.4f} | {sign}{d:.4f} |"
        lines.append(row)

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    gov_base = base.get("governance_compliance", 0.0)
    govs = [summaries.get(mode, {}).get("governance_compliance", 0.0) for mode in modes]
    gov_held = all(abs(g - gov_base) < 0.01 for g in govs)
    if gov_held:
        lines.append(
            f"**Governance held across all three perturbations** ({gov_base:.2f} baseline → "
            f"{', '.join(f'{m}={g:.2f}' for m, g in zip(modes, govs))}). "
            "The RBAC + injection-guard layer is not entity-aware; it filters on policy "
            "tables and structural prompt patterns rather than entity names, which is why "
            "swapping `EY` for `PwC` or padding noise lines does not move the metric."
        )
    else:
        lines.append(
            f"**Governance regressed under perturbation**: baseline {gov_base:.2f} vs "
            f"{', '.join(f'{m}={g:.2f}' for m, g in zip(modes, govs))}. The governance "
            "layer is sensitive to the perturbation; investigate the failing scenarios "
            "in the JSON `rows` for the failure pattern."
        )
    lines.append("")
    lines.append(
        "answer_correctness and completeness deltas under entity_swap are EXPECTED "
        "to be negative: the perturbed answer talks about `PwC` while the rubric's "
        "expected_topics still mention `EY`. That is the test that the judge is "
        "actually looking at content (which it is). Treat correctness deltas as a "
        "judge-faithfulness signal, not a robustness signal."
    )
    lines.append("")
    lines.append(
        "Citation deltas reveal how robust the synthesize prompt is to noisy "
        "evidence: a sharp drop in `source_coverage` under noise_injection means "
        "the model is citing the noise lines, while a sharp drop in `id_grounded` "
        "under doc_deletion means the model is hallucinating IDs that no longer "
        "appear in tool_history."
    )

    out_md = "\n".join(lines)
    print(out_md)
    if args.out:
        Path(args.out).write_text(out_md + "\n")
        print(f"\nsaved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
