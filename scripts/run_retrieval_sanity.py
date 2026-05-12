#!/usr/bin/env python3
"""Run HotpotQA EM/F1 + MS Marco MRR@10 retrieval component sanity check.

This is NOT the main eval anchor: it just demonstrates that the BGE-M3 retrieval
pipeline works on standard benchmarks. See docs/w4_report.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.retrieval_sanity import score_hotpotqa, score_msmarco  # noqa: E402


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--hotpotqa-mode", choices=["naive", "llm-answer"], default="naive")
    parser.add_argument("--hotpotqa-n", type=int, default=100)
    parser.add_argument("--msmarco-n", type=int, default=50)
    args = parser.parse_args()

    print(f"Scoring HotpotQA (n={args.hotpotqa_n}, BGE-M3 top-2, mode={args.hotpotqa_mode})...", flush=True)
    hp = score_hotpotqa(n=args.hotpotqa_n, mode=args.hotpotqa_mode)
    print(f"  HotpotQA: EM={hp['em']} F1={hp['f1']} (n={hp['n']}, mode={hp['mode']})")

    print(f"Scoring MS Marco (n={args.msmarco_n}, BGE-M3 top-10)...", flush=True)
    ms = score_msmarco(n=args.msmarco_n)
    print(f"  MS Marco: MRR@10={ms['mrr@10']} (n={ms['n']})")

    out = REPO_ROOT / "eval_results" / "retrieval_sanity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"hotpotqa": hp, "ms_marco": ms}, indent=2))
    print(f"  saved: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
