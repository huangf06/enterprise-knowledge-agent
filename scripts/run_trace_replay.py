#!/usr/bin/env python3
"""A7 trace replay regression harness.

Compares a candidate eval JSON against the frozen gold trace set on structural
metrics only (tool_f1, citation_groundedness, governance_compliance). Exits
non-zero if any scenario regressed beyond the per-metric threshold - ready to
drop into a CI workflow.

Designate gold via `--gold <path>` or symlink `eval_results/gold/baseline.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.trace_replay import compare, is_pass  # noqa: E402

GOLD_DEFAULT = REPO_ROOT / "eval_results" / "gold" / "baseline.json"
RUNS = REPO_ROOT / "eval_results" / "runs"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", default=None, help="Gold trace JSON path. Default: eval_results/gold/baseline.json")
    p.add_argument("--candidate", default=None, help="Candidate eval JSON. Default: latest in eval_results/runs/")
    p.add_argument("--out", default=None, help="Output report JSON path")
    args = p.parse_args()

    gold = Path(args.gold) if args.gold else GOLD_DEFAULT
    if not gold.exists():
        print(f"ERROR: gold trace not found at {gold}")
        print("Freeze a gold trace with: cp eval_results/runs/eval-*-rejudged.json eval_results/gold/baseline.json")
        return 2

    if args.candidate:
        candidate = Path(args.candidate)
    else:
        runs = sorted(p for p in RUNS.glob("eval-*.json"))
        if not runs:
            print("ERROR: no candidate runs found in eval_results/runs/")
            return 2
        candidate = runs[-1]

    print(f"Gold:      {gold}")
    print(f"Candidate: {candidate}")

    report = compare(gold, candidate)
    passed = is_pass(report)

    print()
    print(f"Compared {report['n_compared']} scenarios.")
    print(f"Missing in candidate: {report['n_missing_in_candidate']}")
    print(f"New in candidate:     {report['n_new_in_candidate']}")
    print(f"Regressions:          {report['n_regressions']}")
    if report["regressions"]:
        print()
        print("Regressed scenarios:")
        for r in report["regressions"]:
            print(f"  {r['scenario_id']} on {r['regressed_on']} delta={r['delta']}")

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(f"\nsaved: {args.out}")

    print(f"\nverdict: {'PASS' if passed else 'FAIL (regressions detected)'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
