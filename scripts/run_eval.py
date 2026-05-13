#!/usr/bin/env python3
"""Run the self-authored eval. Supports a `--limit N` flag to run a subset.

Writes JSON to eval_results/runs/<timestamp>.json and prints a leaderboard summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval import load_scenarios, run_scenario  # noqa: E402

RUNS_DIR = REPO_ROOT / "eval_results" / "runs"


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"count": 0}
    metrics = (
        "answer_correctness",
        "completeness",
        "tool_selection_quality",
        "governance_compliance",
        "action_recommend_quality",
    )
    averages = {}
    for m in metrics:
        vals = [r["scores"].get(m, 0.0) for r in rows]
        averages[m] = round(sum(vals) / len(vals), 4)
    averages["avg_tool_calls"] = round(sum(r["tool_calls"] for r in rows) / len(rows), 2)

    latencies = [r["elapsed_s"] for r in rows]
    averages["avg_elapsed_s"] = round(sum(latencies) / len(latencies), 2)
    averages["p50_elapsed_s"] = round(_pct(latencies, 0.50), 2)
    averages["p95_elapsed_s"] = round(_pct(latencies, 0.95), 2)

    # Per-query agent cost (excludes judge cost which is eval-time only)
    agent_costs = [r.get("agent_usage", {}).get("cost_usd", 0.0) for r in rows]
    averages["agent_cost_usd_total"] = round(sum(agent_costs), 6)
    averages["agent_cost_usd_per_query"] = round(sum(agent_costs) / len(rows), 6)
    averages["p50_agent_cost_usd"] = round(_pct(agent_costs, 0.50), 6)
    averages["p95_agent_cost_usd"] = round(_pct(agent_costs, 0.95), 6)

    # Per-node agent breakdown
    per_node_totals: dict[str, dict] = {}
    for r in rows:
        for node, agg in r.get("agent_usage", {}).get("per_node", {}).items():
            entry = per_node_totals.setdefault(
                node,
                {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
            )
            entry["calls"] += agg.get("calls", 0)
            entry["input_tokens"] += agg.get("input_tokens", 0)
            entry["output_tokens"] += agg.get("output_tokens", 0)
            entry["cost_usd"] += agg.get("cost_usd", 0.0)
    for entry in per_node_totals.values():
        entry["cost_usd"] = round(entry["cost_usd"], 6)
    averages["per_node_agent"] = per_node_totals

    judge_costs = [r.get("judge_usage", {}).get("cost_usd", 0.0) for r in rows]
    averages["judge_cost_usd_total"] = round(sum(judge_costs), 6)

    averages["count"] = len(rows)
    return averages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N scenarios.")
    parser.add_argument("--category", default=None, help="Restrict to one category.")
    args = parser.parse_args()

    scenarios = load_scenarios()
    if args.category:
        scenarios = [s for s in scenarios if s.category == args.category]
    if args.limit is not None:
        scenarios = scenarios[: args.limit]

    print(f"Running {len(scenarios)} scenarios...", flush=True)
    rows = []
    started = time.time()
    for i, s in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] {s.id} ({s.category}/{s.difficulty})", flush=True)
        row = run_scenario(s)
        rows.append(row)
        print(
            f"    scores={row['scores']} tools={row['tools_used']} elapsed={row['elapsed_s']}s",
            flush=True,
        )

    summary = _summarize(rows)
    summary["total_wallclock_s"] = round(time.time() - started, 2)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUNS_DIR / f"eval-{stamp}.json"
    out_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, default=str))

    print()
    print("=" * 60)
    print("Leaderboard (self-authored cross-source scenarios)")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"  results saved: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
