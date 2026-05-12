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
    averages["avg_elapsed_s"] = round(sum(r["elapsed_s"] for r in rows) / len(rows), 2)
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
