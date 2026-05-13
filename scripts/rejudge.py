#!/usr/bin/env python3
"""Re-judge scenarios that hit a JSON parse error.

Reads the latest eval run, re-runs the judge on rows flagged with
_judge_parse_error, writes a re-judged file alongside.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval import load_scenarios  # noqa: E402
from src.eval.judge import judge  # noqa: E402

RUNS = REPO_ROOT / "eval_results" / "runs"


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

    agent_costs = [r.get("agent_usage", {}).get("cost_usd", 0.0) for r in rows]
    averages["agent_cost_usd_total"] = round(sum(agent_costs), 6)
    averages["agent_cost_usd_per_query"] = round(sum(agent_costs) / len(rows), 6)
    averages["p50_agent_cost_usd"] = round(_pct(agent_costs, 0.50), 6)
    averages["p95_agent_cost_usd"] = round(_pct(agent_costs, 0.95), 6)

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
    runs = sorted(p for p in RUNS.glob("eval-*.json") if "-rejudged" not in p.stem)
    if not runs:
        print("No runs found")
        return 1
    base = runs[-1]
    rejudged = base.with_name(base.stem + "-rejudged.json")
    # Prefer the rejudged file if it exists - we want to keep already-good scores
    src = rejudged if rejudged.exists() else base
    print(f"Re-judging from {src.name}")
    data = json.loads(src.read_text())
    rows = data["rows"]
    scenarios = {s.id: s for s in load_scenarios()}
    fixed_count = 0
    still_broken = 0
    for r in rows:
        if r["scores"].get("_judge_parse_error", 0) != 1.0:
            continue
        sc = scenarios[r["scenario_id"]]
        new_scores = judge(sc, r["answer"], r["tools_used"])
        if new_scores.get("_judge_parse_error", 0) == 1.0:
            still_broken += 1
            print(f"  STILL BROKEN: {r['scenario_id']}")
        else:
            fixed_count += 1
            r["scores"] = new_scores
            print(f"  fixed:        {r['scenario_id']} {new_scores}")

    rejudged_data = {"summary": _summarize(rows), "rows": rows}
    out = rejudged
    out.write_text(json.dumps(rejudged_data, indent=2, default=str))

    print()
    print(f"fixed: {fixed_count}, still broken: {still_broken}")
    print("Re-judged leaderboard:")
    for k, v in rejudged_data["summary"].items():
        print(f"  {k}: {v}")
    print(f"saved: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
