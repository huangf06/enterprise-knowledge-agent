#!/usr/bin/env python3
"""MoE Pareto projection from N2 baseline (Sprint 5 prep).

Takes the latest 30-scenario eval, reads per-node token counts from agent_usage,
projects the same tokens under DEFAULT_MOE routing. Reports baseline vs MoE
per-query USD and per-node USD shift. No new LLM calls; pure arithmetic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import os

os.environ["MOE_ENABLED"] = "1"  # turn the router on for projection

from src.llm.moe_router import DEFAULT_MOE, projected_per_query_cost  # noqa: E402

RUNS = REPO_ROOT / "eval_results" / "runs"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=None)
    args = p.parse_args()

    if args.input:
        src = Path(args.input)
    else:
        runs = sorted(p for p in RUNS.glob("eval-*-rejudged.json"))
        if not runs:
            print("No rejudged runs found")
            return 1
        src = runs[-1]

    data = json.loads(src.read_text())
    rows = [r for r in data["rows"] if r.get("ok") and r.get("agent_usage")]
    if not rows:
        print("No usable rows")
        return 1

    print(f"Source: {src.name}, n_rows={len(rows)}")
    print(f"MoE config: {DEFAULT_MOE}")
    print()

    baseline_total = 0.0
    moe_total = 0.0
    per_node_baseline: dict[str, float] = {}
    per_node_moe: dict[str, float] = {}
    for r in rows:
        per_node = r["agent_usage"]["per_node"]
        baseline_total += r["agent_usage"]["cost_usd"]
        for node, agg in per_node.items():
            per_node_baseline[node] = per_node_baseline.get(node, 0.0) + agg["cost_usd"]
        moe, per_node_usd = projected_per_query_cost(per_node)
        moe_total += moe
        for node, usd in per_node_usd.items():
            per_node_moe[node] = per_node_moe.get(node, 0.0) + usd

    n = len(rows)
    print(f"{'node':<14} {'baseline USD':>14} {'MoE USD':>14} {'ratio':>8}")
    print("-" * 56)
    for node in sorted(set(per_node_baseline) | set(per_node_moe)):
        b = per_node_baseline.get(node, 0.0)
        m = per_node_moe.get(node, 0.0)
        ratio = m / b if b > 0 else float("inf")
        print(f"  {node:<12} {b:>14.6f} {m:>14.6f} {ratio:>7.2f}x")
    print("-" * 56)
    print(f"  {'TOTAL':<12} {baseline_total:>14.6f} {moe_total:>14.6f} {moe_total/baseline_total:>7.2f}x")
    print(f"\nPer-query avg: baseline=${baseline_total/n:.6f}  MoE=${moe_total/n:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
