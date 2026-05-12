#!/usr/bin/env python3
"""Run adversarial scenarios. Each must result in blocked=True for governance to pass."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.adversarial import load_adversarial  # noqa: E402
from src.eval.adversarial.runner import run_adversarial  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    scenarios = load_adversarial()
    if args.limit is not None:
        scenarios = scenarios[: args.limit]

    rows = []
    blocked_total = 0
    for i, s in enumerate(scenarios, 1):
        print(f"[{i}/{len(scenarios)}] {s.id} ({s.vector})", flush=True)
        row = run_adversarial(s)
        rows.append(row)
        if row["blocked"]:
            blocked_total += 1
        print(f"    blocked={row['blocked']} leaks={row['leaks']}", flush=True)

    out_path = REPO_ROOT / "eval_results" / "adversarial.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "count": len(rows),
                "blocked": blocked_total,
                "block_rate": round(blocked_total / max(1, len(rows)), 4),
                "rows": rows,
            },
            indent=2,
            default=str,
        )
    )

    print()
    print("=" * 60)
    print("Adversarial governance regression")
    print("=" * 60)
    print(f"  blocked {blocked_total} / {len(rows)}  ({round(100 * blocked_total / max(1, len(rows)), 1)}%)")
    print(f"  results: {out_path.relative_to(REPO_ROOT)}")
    return 0 if blocked_total == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
