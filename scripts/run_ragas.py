#!/usr/bin/env python3
"""F2 RAGAS 4-metric evaluation runner.

Reads the latest eval run, scores via ragas (DeepSeek as LLM, BGE-M3 as
embeddings - no remote spend besides DeepSeek). Writes a `-ragas.json`
alongside.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.ragas_scoring import score_rows  # noqa: E402
from src.eval.scenarios import load_scenarios  # noqa: E402

RUNS = REPO_ROOT / "eval_results" / "runs"

DEFAULT_METRICS = ["answer_relevancy", "faithfulness", "context_precision", "context_recall"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--metrics", default=",".join(DEFAULT_METRICS))
    args = p.parse_args()

    if args.input:
        src = Path(args.input)
    else:
        runs = sorted(p for p in RUNS.glob("eval-*.json") if "-ragas" not in p.stem)
        if not runs:
            print("No eval runs found")
            return 1
        src = runs[-1]

    print(f"RAGAS scoring from {src.name}")
    data = json.loads(src.read_text())
    rows = data["rows"]
    if args.limit is not None:
        rows = rows[: args.limit]

    scenarios_by_id = {s.id: s for s in load_scenarios()}
    metrics = [m for m in args.metrics.split(",") if m.strip()]

    t0 = time.time()
    out = score_rows(rows, scenarios_by_id, metrics=metrics)
    elapsed = time.time() - t0
    out["params"] = {"input": src.name, "limit": args.limit, "metrics": metrics}
    out["elapsed_s"] = round(elapsed, 2)

    out_path = src.with_name(src.stem.replace("-rejudged", "") + "-ragas.json")
    out_path.write_text(json.dumps(out, indent=2, default=str))

    print()
    print(f"RAGAS averages (n={out['n']}, elapsed={elapsed:.1f}s):")
    for k, v in out.get("averages", {}).items():
        print(f"  {k}: {v}")
    print(f"\nsaved: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
