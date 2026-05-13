# A7 trace replay regression harness (Sprint 3)

Catches per-category regressions invisible in the headline rubric. Required by v4.1 honesty policy section 5: **if A7 is dropped, no DSPy ablation claim ships**, because trace replay is the only thing that keeps DSPy publication numbers honest.

## What it compares

Two eval JSONs, scenario-by-scenario, on structural fields only:

| Field | Source |
|---|---|
| `tool_f1` | `src/eval/trajectory.py` (F6) |
| `well_formedness` / `source_coverage` / `id_grounded` | `src/eval/citation.py` (F4) |
| `governance_compliance` | LLM-judge rubric, but score is a 0/1 step function so a swing is detectable structurally |

A scenario is flagged as a regression when the candidate drops below gold by more than `REGRESSION_THRESHOLDS[k]` (`src/eval/trace_replay.py`). Default thresholds: 0.10 on F1/citation, 0.05 on governance, 0.15 on id_grounded.

## What it does NOT compare

Per v4.1 plan P12: **no LLM-judge metrics in CI**. `answer_correctness`, `completeness`, `action_recommend_quality` are LLM-judged and intentionally not part of the replay harness. Running judges in CI would burn the $10/mo OpenAI cap inside a week of PR traffic.

LLM-judge regression checks happen at sprint boundaries via the full eval + multi-judge re-scoring pipeline.

## CLI

```bash
# Freeze a new gold:
cp eval_results/runs/eval-*-rejudged.json eval_results/gold/baseline.json

# Compare latest candidate to gold (exits non-zero on regression):
uv run python scripts/run_trace_replay.py

# Specific candidate:
uv run python scripts/run_trace_replay.py --candidate eval_results/runs/eval-XYZ.json --out replay-report.json
```

## CI wiring (suggested, not yet committed)

Add to `.github/workflows/eval-replay.yml`:

```yaml
name: eval-replay
on:
  pull_request:
    paths:
      - "src/agent/**"
      - "prompts/**"
      - "src/llm/**"
      - "src/eval/**"

jobs:
  replay:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run python scripts/run_eval.py --tier fast
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
      - run: uv run python scripts/run_trace_replay.py
```

Not committed tonight because: needs `DEEPSEEK_API_KEY` secret configured in repo Settings -> Secrets, and the `fast` tier still costs ~$0.02 per PR-run (acceptable but should be a deliberate choice). Document in `docs/deploy.md` morning-of decision items.

## Sanity

Self-comparison (gold vs gold) yields `n_regressions=0` PASS - the harness is correct.
