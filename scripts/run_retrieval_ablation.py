#!/usr/bin/env python3
"""Run A1 retrieval ablation on MS Marco subset.

Output: docs-ready table + JSON dump under eval_results/retrieval_ablation.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.retrieval_ablation import run_ablation  # noqa: E402

OUT_PATH = REPO_ROOT / "eval_results" / "retrieval_ablation.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50, help="MS Marco subset size")
    parser.add_argument("--top-k", type=int, default=10, help="Cutoff K")
    parser.add_argument(
        "--methods",
        default=None,
        help="Comma-separated subset of methods to run (default: all)",
    )
    args = parser.parse_args()

    methods = args.methods.split(",") if args.methods else None
    started = time.time()
    rows = run_ablation(n_queries=args.n, top_k=args.top_k, methods=methods)
    elapsed = time.time() - started

    print()
    print(f"A1 retrieval ablation (n={args.n}, top_k={args.top_k}, elapsed={elapsed:.1f}s)")
    print(f"{'method':<22} {'MRR@10':>10} {'NDCG@10':>10}")
    print("-" * 44)
    for r in rows:
        print(f"  {r['method']:<20} {r['mrr@10']:>10.4f} {r['ndcg@10']:>10.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"params": vars(args), "rows": rows, "elapsed_s": round(elapsed, 2)}, indent=2))
    print(f"\nsaved: {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
