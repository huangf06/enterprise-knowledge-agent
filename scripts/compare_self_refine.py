#!/usr/bin/env python3
"""Self-Refine ablation: compare two eval JSONs (OFF vs ON) and print the table.

Usage:
  uv run python scripts/compare_self_refine.py --off PATH --on PATH [--out PATH]

Pulls the canonical metrics from each side and prints a markdown table sized
for README / docs/frontier3_self_refine.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS = REPO_ROOT / "eval_results" / "runs"

METRIC_KEYS = (
    "answer_correctness",
    "completeness",
    "tool_selection_quality",
    "governance_compliance",
    "action_recommend_quality",
)


def _summary(data: dict) -> dict:
    rows = data["rows"]
    out: dict = {}
    for k in METRIC_KEYS:
        vals = [r["scores"].get(k, 0.0) for r in rows if r.get("ok")]
        out[k] = round(sum(vals) / len(vals), 4) if vals else 0.0
    elapsed = [r["elapsed_s"] for r in rows]
    out["avg_elapsed_s"] = round(sum(elapsed) / len(elapsed), 2) if elapsed else 0.0
    out["p50_elapsed_s"] = round(median(elapsed), 2) if elapsed else 0.0
    out["agent_cost_usd_total"] = round(
        sum(r.get("agent_usage", {}).get("cost_usd", 0.0) for r in rows), 6
    )
    out["agent_cost_usd_per_query"] = round(out["agent_cost_usd_total"] / len(rows), 6) if rows else 0.0
    # Citation/trajectory only present in post-F4/F6 rows
    cite_vals = {
        k: [r.get("citations", {}).get(k, 0.0) for r in rows if r.get("ok")]
        for k in ("well_formedness", "source_coverage", "id_grounded")
    }
    for k, vals in cite_vals.items():
        out[f"cite_{k}"] = round(sum(vals) / len(vals), 4) if vals else 0.0
    traj_vals = [r.get("trajectory", {}).get("tool_f1", 0.0) for r in rows if r.get("ok")]
    out["traj_tool_f1"] = round(sum(traj_vals) / len(traj_vals), 4) if traj_vals else 0.0
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--off", required=True, help="Self-Refine OFF eval JSON")
    p.add_argument("--on", required=True, help="Self-Refine ON eval JSON")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    off_data = json.loads(Path(args.off).read_text())
    on_data = json.loads(Path(args.on).read_text())
    off = _summary(off_data)
    on = _summary(on_data)

    lines = [
        "# Self-Refine ablation table",
        "",
        f"Source OFF: `{args.off}`",
        f"Source ON:  `{args.on}`",
        "",
        "| Metric | OFF | ON | Delta |",
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
    lines.append(f"| avg_elapsed_s | {off['avg_elapsed_s']:.2f} | {on['avg_elapsed_s']:.2f} | +{on['avg_elapsed_s']-off['avg_elapsed_s']:.2f}s |")
    lines.append(f"| p50_elapsed_s | {off['p50_elapsed_s']:.2f} | {on['p50_elapsed_s']:.2f} | +{on['p50_elapsed_s']-off['p50_elapsed_s']:.2f}s |")
    lines.append(f"| agent_cost_usd_per_query | {off['agent_cost_usd_per_query']:.6f} | {on['agent_cost_usd_per_query']:.6f} | +{on['agent_cost_usd_per_query']-off['agent_cost_usd_per_query']:.6f} |")
    out_md = "\n".join(lines)
    print(out_md)
    if args.out:
        Path(args.out).write_text(out_md + "\n")
        print(f"\nsaved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
