#!/usr/bin/env python3
"""F3 multi-judge consensus: re-score the latest eval run with 3 judges.

Reads the most recent (possibly rejudged) eval JSON, applies DeepSeek +
Anthropic Haiku + OpenAI gpt-4o-mini judges to each scenario, writes a
`-multijudge.json` file with per-judge + consensus + dispersion + inter-judge
Pearson correlation.

This is NOT run on every eval (cost ~$0.10/30 scenarios on Anthropic +
OpenAI). Sprint boundaries + DSPy ablation only. Daily fast-tier eval stays
DeepSeek-single-judge.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.multi_judge import DEFAULT_POOL, METRIC_KEYS, multi_judge, run_inter_judge_agreement  # noqa: E402
from src.eval.scenarios import load_scenarios  # noqa: E402
from src.llm.judge_client import get_judge_cost, reset_judge_cost  # noqa: E402

RUNS = REPO_ROOT / "eval_results" / "runs"


def _summary_consensus(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {k: 0.0 for k in METRIC_KEYS}
    out: dict[str, float] = {}
    for k in METRIC_KEYS:
        vals = [r["multi_judge"]["consensus"].get(k, 0.0) for r in rows if r.get("multi_judge")]
        out[k] = round(sum(vals) / len(vals), 4) if vals else 0.0
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Path to source eval JSON (default: latest)")
    parser.add_argument("--limit", type=int, default=None, help="First N scenarios only")
    args = parser.parse_args()

    if args.input:
        src = Path(args.input)
    else:
        runs = sorted(p for p in RUNS.glob("eval-*.json"))
        if not runs:
            print("No eval runs found")
            return 1
        src = runs[-1]

    print(f"Multi-judging from {src.name} with pool={list(DEFAULT_POOL)}")
    data = json.loads(src.read_text())
    rows = data["rows"]
    if args.limit is not None:
        rows = rows[: args.limit]

    scenarios = {s.id: s for s in load_scenarios()}
    reset_judge_cost()
    started = time.time()
    annotated_rows: list[dict] = []
    for i, r in enumerate(rows, 1):
        if not r.get("ok"):
            r["multi_judge"] = None
            annotated_rows.append(r)
            continue
        sc = scenarios.get(r["scenario_id"])
        if sc is None:
            print(f"  [{i}/{len(rows)}] WARN scenario {r['scenario_id']} not found, skipping")
            r["multi_judge"] = None
            annotated_rows.append(r)
            continue
        print(f"  [{i}/{len(rows)}] {r['scenario_id']}", flush=True)
        mj = multi_judge(sc, r["answer"], r["tools_used"])
        r["multi_judge"] = mj
        annotated_rows.append(r)
    elapsed = time.time() - started

    consensus_summary = _summary_consensus(annotated_rows)

    per_judge_rows = [r["multi_judge"]["per_judge"] for r in annotated_rows if r.get("multi_judge")]
    agreement = run_inter_judge_agreement(per_judge_rows)

    out = {
        "input_run": src.name,
        "pool": list(DEFAULT_POOL),
        "elapsed_s": round(elapsed, 2),
        "n_scored": sum(1 for r in annotated_rows if r.get("multi_judge")),
        "consensus_summary": consensus_summary,
        "inter_judge_pearson": agreement,
        "judge_cost_usd": {
            "deepseek": get_judge_cost("deepseek"),
            "anthropic": get_judge_cost("anthropic"),
            "openai": get_judge_cost("openai"),
        },
        "rows": annotated_rows,
    }
    out_path = src.with_name(src.stem.replace("-rejudged", "") + "-multijudge.json")
    out_path.write_text(json.dumps(out, indent=2, default=str))

    print()
    print("=" * 60)
    print(f"Multi-judge consensus (n={out['n_scored']}, elapsed={elapsed:.1f}s)")
    print("=" * 60)
    for k, v in consensus_summary.items():
        print(f"  {k}: {v}")
    print()
    print("Inter-judge Pearson correlation:")
    for pair, metrics in agreement.items():
        print(f"  {pair} mean={metrics['mean']}  per-metric={ {k: v for k, v in metrics.items() if k != 'mean'} }")
    print()
    print("Judge API cost (this run):")
    for p, c in out["judge_cost_usd"].items():
        print(f"  {p}: ${c}")
    print(f"\nsaved: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
