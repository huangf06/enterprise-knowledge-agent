#!/usr/bin/env python3
"""Run the HotpotQA full-agent benchmark.

For each of the first N examples from the HotpotQA dev distractor split, runs
EKA's 5-node LangGraph agent loop against a single-tool registry whose only
tool is `retrieve_passage` (BGE-M3 over the question's 10 candidate paragraph
pool). Scores the agent's short-answer against the gold using the standard
HotpotQA F1 + EM normalization, and writes a per-example JSON record plus
aggregate summary to disk.

A cost guardrail (`--limit-cost-usd`) halts the run early if the running
DeepSeek spend crosses the threshold.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.hotpotqa_agent import run_agent  # noqa: E402
from src.eval.hotpotqa_loader import load_dev  # noqa: E402
from src.eval.hotpotqa_score import score  # noqa: E402
from src.llm.cost_ledger import query_window  # noqa: E402

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


def _aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {"count": 0}
    n = len(rows)
    em = sum(r["em"] for r in rows) / n
    f1 = sum(r["f1"] for r in rows) / n
    precision = sum(r["precision"] for r in rows) / n
    recall = sum(r["recall"] for r in rows) / n
    tool_calls = [r["tool_calls"] for r in rows]
    elapsed = [r["elapsed_s"] for r in rows]
    costs = [r["cost_usd"] for r in rows]
    ok_count = sum(1 for r in rows if r["ok"])
    return {
        "count": n,
        "ok_count": ok_count,
        "em": round(em, 4),
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "avg_tool_calls": round(sum(tool_calls) / n, 2),
        "p50_tool_calls": round(_pct(tool_calls, 0.50), 2),
        "p95_tool_calls": round(_pct(tool_calls, 0.95), 2),
        "avg_elapsed_s": round(sum(elapsed) / n, 2),
        "p50_elapsed_s": round(_pct(elapsed, 0.50), 2),
        "p95_elapsed_s": round(_pct(elapsed, 0.95), 2),
        "total_cost_usd": round(sum(costs), 6),
        "avg_cost_usd": round(sum(costs) / n, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100, help="Number of dev examples to run.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="How many passages retrieve_passage returns per call.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Hard cap on agent tool calls per question.",
    )
    parser.add_argument(
        "--limit-cost-usd",
        type=float,
        default=5.0,
        help="Halt the run if the cumulative DeepSeek spend exceeds this dollar amount.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to eval_results/runs/hotpotqa-agent-<ts>.json",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print a progress line every N examples.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Write a partial result JSON every N examples (alongside the final file).",
    )
    args = parser.parse_args()

    os.environ.setdefault("SELF_REFINE_ENABLED", "0")
    os.environ.setdefault("USE_COMPILED_PROMPTS", "0")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = args.out or RUNS_DIR / f"hotpotqa-agent-{stamp}.json"

    print(f"Loading first {args.n} HotpotQA dev distractor examples...", flush=True)
    examples = load_dev(n=args.n)
    print(f"Loaded {len(examples)} examples.", flush=True)
    print(
        f"Config: top_k={args.top_k} max_iterations={args.max_iterations} "
        f"cost_cap=${args.limit_cost_usd}",
        flush=True,
    )

    rows: list[dict] = []
    started_iso = datetime.now(timezone.utc).isoformat()
    started_wall = time.time()
    cumulative_cost = 0.0
    halted = False
    halt_reason = ""

    for i, ex in enumerate(examples, 1):
        q_start_iso = datetime.now(timezone.utc).isoformat()
        q_start_wall = time.time()
        result = run_agent(ex, max_iterations=args.max_iterations, top_k=args.top_k)
        q_end_iso = datetime.now(timezone.utc).isoformat()
        q_elapsed = time.time() - q_start_wall
        usage = query_window(q_start_iso, q_end_iso)
        q_cost = float(usage.get("cost_usd", 0.0))
        cumulative_cost += q_cost
        sc = score(result.short_answer, result.gold)

        row = {
            "qid": result.qid,
            "question": result.question,
            "gold": result.gold,
            "prediction_short": result.short_answer,
            "prediction_raw": result.raw_answer,
            "em": sc.em,
            "f1": round(sc.f1, 4),
            "precision": round(sc.precision, 4),
            "recall": round(sc.recall, 4),
            "tool_calls": result.tool_calls,
            "elapsed_s": round(q_elapsed, 2),
            "cost_usd": round(q_cost, 6),
            "cumulative_cost_usd": round(cumulative_cost, 6),
            "ok": result.ok,
            "error": result.error,
            "level": ex.level,
            "qtype": ex.qtype,
            "supporting_titles": sorted({t for t, _ in ex.supporting_facts}),
            "tool_history_summary": [
                {"tool": h["tool"], "args": h["args"]} for h in result.tool_history
            ],
        }
        rows.append(row)

        if i % args.progress_every == 0 or i == len(examples):
            running = _aggregate(rows)
            print(
                f"[{i}/{len(examples)}] f1={running['f1']:.3f} em={running['em']:.3f} "
                f"avg_tools={running['avg_tool_calls']:.1f} "
                f"avg_elapsed={running['avg_elapsed_s']:.1f}s "
                f"cum_cost=${cumulative_cost:.4f}",
                flush=True,
            )

        if i % args.checkpoint_every == 0 and i != len(examples):
            ckpt_summary = _aggregate(rows)
            ckpt_summary["total_wallclock_s"] = round(time.time() - started_wall, 2)
            ckpt_summary["partial"] = True
            ckpt_summary["started_iso"] = started_iso
            ckpt_summary["config"] = {
                "n_requested": args.n,
                "n_run": len(rows),
                "top_k": args.top_k,
                "max_iterations": args.max_iterations,
                "limit_cost_usd": args.limit_cost_usd,
            }
            out_path.write_text(
                json.dumps({"summary": ckpt_summary, "rows": rows}, indent=2)
            )

        if cumulative_cost > args.limit_cost_usd:
            halted = True
            halt_reason = (
                f"cumulative cost ${cumulative_cost:.4f} > cap ${args.limit_cost_usd:.4f}"
            )
            print(f"HALT: {halt_reason}", flush=True)
            break

    ended_iso = datetime.now(timezone.utc).isoformat()
    wallclock = time.time() - started_wall
    summary = _aggregate(rows)
    summary["total_wallclock_s"] = round(wallclock, 2)
    summary["halted"] = halted
    summary["halt_reason"] = halt_reason
    summary["started_iso"] = started_iso
    summary["ended_iso"] = ended_iso
    summary["config"] = {
        "n_requested": args.n,
        "n_run": len(rows),
        "top_k": args.top_k,
        "max_iterations": args.max_iterations,
        "limit_cost_usd": args.limit_cost_usd,
        "self_refine_enabled": os.environ.get("SELF_REFINE_ENABLED", "0"),
        "use_compiled_prompts": os.environ.get("USE_COMPILED_PROMPTS", "0"),
        "retrieval": "BGE-M3 cosine over question's 10 candidate paragraphs",
        "dataset": "HotpotQA dev distractor v1 (first n in source order)",
    }

    out_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

    print()
    print("=" * 60)
    print("HotpotQA full-agent benchmark")
    print("=" * 60)
    for k, v in summary.items():
        if k == "config":
            continue
        print(f"  {k}: {v}")
    print(f"  results saved: {out_path.relative_to(REPO_ROOT)}")
    return 0 if not halted else 2


if __name__ == "__main__":
    raise SystemExit(main())
