# Eval methodology

> Status: calibrated, single-author scope. External-reviewer spot-check is v1.5 scope. Honest closed-loop chapter per design Section 7.G.

## The closed-loop problem

The 30 self-authored scenarios were written by the same person who designed the agent, generated the data, wrote the LLM-judge rubric, and produced the synthetic ground-truth citations. That is a closed loop, and the scores reported here should be read as **system-internal calibration**, not third-party benchmark numbers.

We mitigate (not eliminate) this with four practices:

1. **External retrieval sanity check.** HotpotQA and MS Marco run on the same retrieval pipeline. MS Marco MRR@10 of 0.5381 (vs the BGE-M3 published baseline of ~0.45) shows the retrieval primitive isn't degenerate. HotpotQA F1 lifted from 0.077 (naive span extraction) to 0.29 (llm-answer mode in W6), still below the 0.70 design target; the remaining gap is the simple 2-passage retrieval and no QA-specific fine-tune, not the retrieval primitive.
2. **Determinism.** Synthetic data, scenarios, and judge prompts are byte-deterministic from a single seed. Anyone can reproduce the run and inspect every step.
3. **Adversarial regression.** 10 cross-source attack vectors check that the agent refuses what it should refuse, not just answers what it should answer. Governance compliance is a separate axis from answer correctness.
4. **External reviewer slot.** The W7 hard gate planned 1-2 NL tech-contact spot-checks of 5-10 scenarios. The pre-launch slot did not happen; the README header therefore declares "LLM-judge with single-author calibration" explicitly. External-reviewer review is v1.5 scope.

## What the leaderboard means

Each scenario has:
- An expected source set (which tools should be called)
- Expected topics (which concepts should appear in the answer)
- Expected citations (which synthetic-data IDs should be referenced)
- Expected action (what next step the agent should recommend)
- Governance constraints (what must NOT leak)

The LLM-as-judge prompt scores each axis 0..1. Tool selection is also algorithmically scored by comparing actual `tools_used` to `expected_sources` — the LLM judge's `tool_selection_quality` is a tiebreaker.

## What we won't claim

- That this benchmark generalizes to other cross-source enterprise corpora.
- That the LLM-judge's calibration matches a panel of human raters; we publish the rubric and the answers so anyone can re-judge.
- That HotpotQA/MS Marco numbers reflect agent quality; they reflect retrieval pipeline health only.

## How to re-run

```bash
docker compose up -d
uv sync --extra dev
uv run python scripts/generate_data.py --seed 42
uv run python scripts/run_retrieval_sanity.py
uv run python scripts/run_eval.py
uv run python scripts/run_adversarial.py
```

Results land in `eval_results/`.
