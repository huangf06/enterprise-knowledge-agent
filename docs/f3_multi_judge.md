# F3 multi-judge consensus + inter-judge agreement (Sprint 2)

3 judges score every (scenario, answer) pair: DeepSeek (the agent's own model), Anthropic Haiku 4.5, OpenAI gpt-4o-mini. Implementation in `src/eval/multi_judge.py`; CLI in `scripts/run_multi_judge.py`. Cost: ~$0.07 per 30-scenario pass on Anthropic + OpenAI.

## Why three vendors

Single LLM-judge scores are vulnerable to self-preference bias (model rates outputs from its own class higher). Three vendors with different training pipelines give an independent corroboration of the rubric numbers.

**N1 contamination lock (v4.1)**: during DSPy compilation (Sprint 4), the DeepSeek judge is dropped from the pool. The training metric uses Haiku + gpt-4o-mini consensus only, so DSPy cannot reward-hack against its own model class. Other ablations (Sprint 2-3, 5-7) use all three judges. The DSPy ablation doc reports both regimes (P15).

## Baseline result (run 2026-05-13)

Source: `eval_results/runs/eval-20260513-021421-multijudge.json`. Re-scoring of the N2 baseline run.

### Consensus (median of 3 judges)

| Metric | Consensus | Single-judge (DeepSeek) |
|---|---:|---:|
| answer_correctness | 0.738 | 0.643 |
| completeness | 0.669 | 0.700 |
| tool_selection_quality | 0.847 | 0.930 |
| governance_compliance | 1.000 | 1.000 |
| action_recommend_quality | 0.492 | 0.530 |

The single-judge DeepSeek tends to be slightly stricter on tool selection / completeness and slightly more lenient on answer_correctness vs the consensus. None of the deltas exceed 0.1, so the v1 leaderboard headline numbers are within the consensus envelope.

### Inter-judge Pearson correlation (mean across 4 non-trivial metrics)

| Pair | Mean r |
|---|---:|
| anthropic_vs_openai | **0.609** |
| anthropic_vs_deepseek | 0.521 |
| deepseek_vs_openai | 0.436 |

`governance_compliance` is excluded from the mean because the v1 agent scores 1.0 across all scenarios on all three judges (constant series, undefined correlation).

### Interpretation

- **Anthropic Haiku is the most agreeable judge** - it correlates well with both DeepSeek and OpenAI.
- **DeepSeek vs OpenAI is the weakest pair** (r=0.44). They are training-line-independent and have the largest scoring variance.
- The **moderate agreement (r=0.4-0.6)** is the textbook signal that single-judge scores should not be treated as ground truth. The consensus + dispersion fields capture this honestly.

## Sprint boundary policy

- **Daily fast-tier eval**: DeepSeek single-judge (free, fast). Lives in `scores`.
- **Sprint boundary full eval**: re-run with `scripts/run_multi_judge.py`. Lives in `-multijudge.json` and is the number the leaderboard publishes.
- **DSPy ablation (Sprint 4)**: 2-judge pool (Haiku + gpt-4o-mini) for training metric; full 3-judge consensus for ablation comparison. Both reported in the DSPy ablation doc (P15).
