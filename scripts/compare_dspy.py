#!/usr/bin/env python3
"""DSPy agent-level ablation: compare two eval JSONs (OFF vs ON) and print the table.

Mirrors compare_self_refine.py but reads compiled-DSPy vs manual-prompt runs.
Filters both inputs to a common set of scenario_ids so partial OFF (e.g. a
30-scenario baseline) can be compared against a 10-scenario fast-tier ON run.

Usage:
  uv run python scripts/compare_dspy.py \\
    --off eval_results/runs/eval-20260513-105857.json \\
    --on  eval_results/runs/eval-<dspy-on>.json \\
    --out docs/sprint4_dspy_agent_ablation.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parents[1]

METRIC_KEYS = (
    "answer_correctness",
    "completeness",
    "tool_selection_quality",
    "governance_compliance",
    "action_recommend_quality",
)


def _summary(rows: list[dict]) -> dict:
    out: dict = {}
    for k in METRIC_KEYS:
        vals = [r["scores"].get(k, 0.0) for r in rows if r.get("ok")]
        out[k] = round(sum(vals) / len(vals), 4) if vals else 0.0
    elapsed = [r["elapsed_s"] for r in rows]
    out["avg_elapsed_s"] = round(sum(elapsed) / len(elapsed), 2) if elapsed else 0.0
    out["p50_elapsed_s"] = round(median(elapsed), 2) if elapsed else 0.0
    costs = [r.get("agent_usage", {}).get("cost_usd", 0.0) for r in rows]
    out["agent_cost_usd_total"] = round(sum(costs), 6)
    out["agent_cost_usd_per_query"] = round(sum(costs) / len(rows), 6) if rows else 0.0
    cite_vals = {
        k: [r.get("citations", {}).get(k, 0.0) for r in rows if r.get("ok")]
        for k in ("well_formedness", "source_coverage", "id_grounded")
    }
    for k, vals in cite_vals.items():
        out[f"cite_{k}"] = round(sum(vals) / len(vals), 4) if vals else 0.0
    traj_vals = [r.get("trajectory", {}).get("tool_f1", 0.0) for r in rows if r.get("ok")]
    out["traj_tool_f1"] = round(sum(traj_vals) / len(traj_vals), 4) if traj_vals else 0.0
    out["count"] = len(rows)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--off", required=True)
    p.add_argument("--on", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    off_rows = json.loads(Path(args.off).read_text())["rows"]
    on_rows = json.loads(Path(args.on).read_text())["rows"]
    on_ids = {r["scenario_id"] for r in on_rows}
    off_rows = [r for r in off_rows if r["scenario_id"] in on_ids]

    off = _summary(off_rows)
    on = _summary(on_rows)

    lines = [
        "# DSPy compiled-prompt ablation (synthesize node, agent-level)",
        "",
        f"Source OFF (manual prompt): `{args.off}`",
        f"Source ON  (DSPy compiled):  `{args.on}`",
        f"Shared scenarios: {off['count']} (filtered to ON's set)",
        "",
        "Both runs were executed with `SELF_REFINE_ENABLED=0` so the only changed",
        "variable is the synthesize prompt path. Per v4.1 P15 the ablation also",
        "reports multi-judge consensus (separate file `-multijudge.json`).",
        "",
        "| Metric | OFF (manual) | ON (compiled) | Delta |",
        "|---|---:|---:|---:|",
    ]
    for k in METRIC_KEYS:
        d = round(on[k] - off[k], 4)
        sign = "+" if d > 0 else ""
        lines.append(f"| {k} | {off[k]:.4f} | {on[k]:.4f} | {sign}{d:.4f} |")
    for k in ("cite_well_formedness", "cite_source_coverage", "cite_id_grounded", "traj_tool_f1"):
        d = round(on[k] - off[k], 4)
        sign = "+" if d > 0 else ""
        lines.append(f"| {k} | {off[k]:.4f} | {on[k]:.4f} | {sign}{d:.4f} |")
    lines.append("|  |  |  |  |")
    lines.append(
        f"| avg_elapsed_s | {off['avg_elapsed_s']:.2f} | {on['avg_elapsed_s']:.2f} | "
        f"+{on['avg_elapsed_s'] - off['avg_elapsed_s']:.2f}s |"
    )
    lines.append(
        f"| p50_elapsed_s | {off['p50_elapsed_s']:.2f} | {on['p50_elapsed_s']:.2f} | "
        f"+{on['p50_elapsed_s'] - off['p50_elapsed_s']:.2f}s |"
    )
    delta_cost = on["agent_cost_usd_per_query"] - off["agent_cost_usd_per_query"]
    cost_sign = "+" if delta_cost > 0 else ""
    lines.append(
        f"| agent_cost_usd_per_query | {off['agent_cost_usd_per_query']:.6f} | "
        f"{on['agent_cost_usd_per_query']:.6f} | {cost_sign}{delta_cost:.6f} |"
    )
    out_md = "\n".join(lines)
    print(out_md)
    if args.out:
        Path(args.out).write_text(out_md + "\n")
        print(f"\nsaved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
