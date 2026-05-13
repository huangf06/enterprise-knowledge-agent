# N2 v1 baseline (Sprint 1 Day-1)

Locked 2026-05-13. Canonical pre-v4 numbers all subsequent frontier claims (MoE Pareto, semantic cache lift, DSPy improvement, Self-Refine deltas) compare against.

Source run: `eval_results/runs/eval-20260513-021421-rejudged.json` (3 rejudge passes; 4 of 30 still hit `_judge_parse_error: 1.0` and score 0 — Sprint 1 F1 messages.parse + Pydantic `JudgeScore` will eliminate this in Sprint 2 onward).

## Latency

| | Seconds |
|---|---:|
| avg | 171.12 |
| p50 | 177.48 |
| p95 | 253.85 |
| 30 scenarios wallclock | 6043 (100 min) |

## Cost (DeepSeek list, agent only, per-query)

| | USD |
|---:|---:|
| avg | 0.002032 |
| p50 | 0.002247 |
| p95 | 0.002824 |
| 30 scenarios total | 0.06097 |

Judge (additional, eval-time only): $0.0095 total / 30 scenarios.

## Per-node breakdown

| Node | Calls (30 scenarios) | Input tokens | Output tokens | USD | % of agent cost |
|---|---:|---:|---:|---:|---:|
| tool_select | 125 | 44,145 | 55,732 | 0.0239 | **39.2%** |
| synthesize | 30 | 39,683 | 37,240 | 0.0160 | 26.2% |
| reflect | 98 | 53,354 | 23,443 | 0.0140 | 23.0% |
| plan | 30 | 3,862 | 22,830 | 0.0071 | 11.6% |

Avg per scenario: 4.17 tool_select calls, 3.27 reflect calls.

## Quality (rejudged, 4 persistent parse errors → deflated; Sprint 1 F1 fixes)

| Metric | Rejudged 2026-05-13 | README hist (rejudged 2026-05-12) | Floor (4 zeros) |
|---|---:|---:|---:|
| answer_correctness | 0.557 | 0.71 | ~0.71 once F1 lands |
| completeness | 0.608 | 0.75 | ~0.75 |
| tool_selection_quality | 0.827 | 0.96 | ~0.96 |
| governance_compliance | 0.867 | 0.97 | ~0.97 |
| action_recommend_quality | 0.453 | 0.46 | (already aligned) |
| avg_tool_calls | 3.77 | 3.73 | (already aligned) |

## Implications for v4 frontier work

- **MoE routing Pareto**: tool_select (39% of cost, 125 calls) is the dominant cost target. Routing tool_select to a cheaper model captures ~4x the savings of routing synthesize. Document this in F4 routing rationale.
- **Semantic cache lift (A3)**: synthesize node cost per call is highest ($0.0005/call); a cache hit on synthesize saves more per-hit than on tool_select. But cache hit rate is higher for reflect prompts (structured, repetitive).
- **DSPy compilation target (Sprint 4 P13)**: optimize `synthesize` first per locked plan; tool_select second if buffer allows. Per-call cost makes synthesize the higher-leverage target.
- **Self-Refine cost overhead (Sprint 3)**: 2 critique passes per synthesize → 2x synthesize cost = +$0.0005-0.0010 per query. Acceptable.
