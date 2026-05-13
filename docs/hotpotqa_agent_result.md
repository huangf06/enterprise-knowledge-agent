# HotpotQA full-agent benchmark

A public benchmark anchor for EKA's agentic multi-hop reasoning. The
README already cites a retrieval-only HotpotQA F1 (BGE-M3 top-2 +
DeepSeek extraction, EM=0.28, F1=0.29). This page adds the FULL-AGENT
mode number, where the same 5-node LangGraph loop EKA uses for the
enterprise scenarios drives `retrieve_passage` over the question's
10-paragraph candidate pool, then synthesizes a short answer.

## 1. Setup

| Knob | Value |
|---|---|
| Dataset | HotpotQA dev distractor v1 (CMU mirror) |
| Sampling | First n=100 in source order (deterministic, no shuffle) |
| Retrieval pool | The question's own 10 candidate paragraphs (2 gold + 8 distractor) |
| Retrieval method | BGE-M3 cosine similarity, top-k=3 per call |
| Agent | EKA's 5-node LangGraph: plan / tool_select / tool_execute / reflect / synthesize |
| Tool registry | One tool: `retrieve_passage(query, top_k)` |
| LLM | DeepSeek V4 Pro via Anthropic-compatible endpoint |
| Self-Refine | OFF (its checks are enterprise-specific) |
| DSPy compiled prompts | OFF |
| Max agent iterations | 5 tool calls per question |
| Short-answer extraction | Single LLM call collapses the synthesize-node long-form draft to the canonical 1-5 word HotpotQA short answer |
| Scoring | Token-level F1 + EM on the normalized answer (lowercase, drop articles, strip punctuation, collapse whitespace), matching `hotpot_evaluate_v1.py` |

Reproduce:

```bash
SELF_REFINE_ENABLED=0 USE_COMPILED_PROMPTS=0 \
  uv run python scripts/run_hotpotqa_agent_eval.py --n 100 --limit-cost-usd 5
```

Output lands at `eval_results/runs/hotpotqa-agent-<ts>.json` with one
record per example plus an aggregate summary.

## 2. Result

<!-- RUN_RESULT_TABLE_START -->

| Metric | Value |
|---|---:|
| n | 100 / 100 |
| F1 (token-level, averaged) | **0.816** |
| Exact Match | **0.690** |
| Precision | 0.837 |
| Recall | 0.811 |
| Avg tool calls per question | 2.75 |
| p50 / p95 tool calls | 2.0 / 5.0 |
| Avg elapsed per question | 93.4 s |
| p50 / p95 elapsed | 79.2 s / 163.2 s |
| Total DeepSeek API cost | $0.140 |
| Avg cost per question | $0.0014 |
| Total wall-clock | 9336 s (2 h 35 m) |
| Halted (cost cap or error) | false |

Run JSON: `eval_results/runs/hotpotqa-agent-final.json` (one row per example plus the aggregate above).

Per-question-type split (first 100 dev examples are all `level=hard` in source order, no shuffle):

| qtype | n | F1 |
|---|---:|---:|
| comparison | 21 | 0.887 |
| bridge | 79 | 0.797 |

Comparison questions (typically yes/no over two entities) score noticeably higher than bridge questions (require chaining the answer of one hop into the next). The split is consistent with published agent results on HotpotQA distractor.

<!-- RUN_RESULT_TABLE_END -->

## 3. Comparison

| System | F1 | Notes |
|---|---:|---|
| ReAct (vanilla, dev distractor) | ~0.32-0.35 | Yao 2022 Table 2, PaLM-540B |
| ReAct + best prompt (dev distractor) | 0.473 | Yao 2022 Table 3, PaLM-540B |
| Retrieval-only (this repo, n=100, BGE-M3 top-2 + DeepSeek extraction) | 0.290 | retrieval table in README |
| **EKA full agent (this benchmark)** | **0.816** | n=100, dev distractor, BGE-M3 top-3, DeepSeek V4 Pro 5-node agent loop |

The 2.8x lift over the retrieval-only number in the same repo is the value of the agent loop (planning, multi-hop tool calls, reflection). The 1.7x lift over the strongest ReAct number in the paper reflects model+agent together: DeepSeek V4 Pro is a 2025-era model and PaLM-540B is 2022. The point of citing the older paper is not to claim a fair head-to-head with 2022 PaLM, but to anchor the order of magnitude against the most-cited published baseline.

## 4. Failure analysis

Five representative failures (F1=0 examples), all `level=hard`:

| Failure mode | Question (truncated) | Gold | Agent's answer |
|---|---|---|---|
| Multi-hop entity bridging (got a later role of the right person, not the asked one) | "What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?" | Chief of Protocol | United States Ambassador to Ghana |
| Polarity error on comparison | "Are Random House Tower and 888 7th Avenue both used for real estate?" | no | yes |
| Refused to commit when the number was retrievable | "Brown State Fishing Lake is in a country that has a population of how many inhabitants?" | 9,984 | unknown |
| Confused related characters in the same franchise | "This singer of A Rather Blustery Day also voiced what hedgehog?" | Sonic | Dr. Robotnik |
| Question-type misread (gave yes/no when an entity was asked) | "Kaiser Ventures corporation was founded by an American industrialist who became known as the father of modern American shipbuilding..." | Henry J. Kaiser | Yes |

The clusters above are not unique to this benchmark: bridge-hop entity confusion and yes/no polarity errors are the two failure modes ReAct paper Section 5 also flags. The "refused to commit" pattern is more idiosyncratic to the synthesize prompt EKA uses for the enterprise scenarios, where over-claiming on missing evidence is the bigger risk; a HotpotQA-specific prompt that pushes the model to commit when retrieval did return a candidate paragraph would likely close some of these.

## 5. What this doesn't claim

- This is dev distractor, not fullwiki. Open-book is harder.
- n=100 not the full 7405. The sampling protocol is deterministic so any
  later n-extension is reproducible.
- DeepSeek V4 Pro is a strong base model; the result reflects model + agent
  together, not the agent alone.
- The retrieval component sanity row (BGE-M3 top-2 + extraction, F1=0.29) is
  kept in the README leaderboard alongside this number, because the gap
  between the two is the value-add of the multi-hop agent loop.
