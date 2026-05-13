# F2 RAGAS 4-metric eval (Sprint 2)

Standard RAGAS metrics layered on top of our self-authored judge:

| Metric | Question it answers |
|---|---|
| `answer_relevancy` | Does the agent's answer address the user's question? |
| `faithfulness` | Does every claim in the answer entail from the retrieved contexts? (hallucination check) |
| `context_precision` | Of the retrieved contexts, which fraction contain the reference information? |
| `context_recall` | Of the reference information, which fraction is covered by retrieved contexts? |

Implementation: `src/eval/ragas_scoring.py`. RAGAS is configured with our DeepSeek client as the LLM (via langchain-anthropic Chat wrapper) and BGE-M3 as the embeddings model, so a full 4-metric run on 30 scenarios costs ~$0.20-0.40 of DeepSeek inference and no external embedding spend.

CLI: `python scripts/run_ragas.py [--input PATH] [--limit N] [--metrics M1,M2,...]`.

## Why ship this on top of our own judge

Single LLM-judge scores are widely known to be unreliable. Three layered checks make the v4 leaderboard defensible:

1. **Self-authored judge** (`src/eval/judge.py`, F1 structured): the rubric numbers in the README - human-designed prompt, structured output. Lives in the eval row's `scores` field.
2. **Multi-judge consensus** (`src/eval/multi_judge.py`, F3): DeepSeek + Anthropic Haiku + OpenAI gpt-4o-mini median, with pairwise Pearson agreement. Sprint boundaries only. Lives in `-multijudge.json`.
3. **RAGAS standardized** (this doc, F2): industry-recognizable terms, third-party algorithm. Lives in `-ragas.json`.

If a frontier technique improves both #1 and #3 in the same direction, the lift is real. If only one moves, the move is a methodological artifact.

## Known issues

- **Faithfulness timeouts.** RAGAS faithfulness generates statements then verifies each against context. DeepSeek's reasoner thinking blocks can take 30-90s per call; some faithfulness verifications exceed the default RAGAS timeout. Our `RunConfig(timeout=600, max_retries=3, max_workers=2)` mitigates but does not eliminate. F4 algorithmic citation (`src/eval/citation.py`) covers the same conceptual space (hallucinated ID detection) deterministically and is the recommended hallucination metric for daily eval. RAGAS faithfulness is a Sprint 2 polishing target - tighten max_tokens or move faithfulness LLM to Haiku.
- **No HF_TOKEN.** BGE-M3 downloads anonymously from HuggingFace Hub. Set `HF_TOKEN` to lift rate limits for fast initial deploy.
- **ChatAnthropic max_tokens=8192.** Required to fit DeepSeek reasoner thinking; lower values reliably hit `LLMDidNotFinishException`.

## Sprint 2 acceptance

- `answer_relevancy` PASS: produces sensible per-scenario values on smoke (0.68-0.88 on briefings).
- `faithfulness`: scaffold in place, expected to require a final tuning pass before publication numbers (move judge to Haiku, recompute with 4-judge median).
- `context_precision` / `context_recall`: scaffold in place, expected to run cleanly with the same timeout tuning as faithfulness.
