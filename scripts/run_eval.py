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
