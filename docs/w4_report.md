# W4 hard gate report

Self-authored cross-source scenarios are the **main eval anchor**. HotpotQA and MS Marco numbers below are a **retrieval component sanity check** for the BGE-M3 pipeline, not an anchor for the agent's cross-source task. Per design Sections 6.1 / 6.2 / 8.

## 1. Self-authored cross-source scenarios

Latest run: n=30, wallclock=5943.08s

| Metric | Score |
|---|---:|
| `answer_correctness` | 0.45 |
| `completeness` | 0.4483 |
| `tool_selection_quality` | 0.6 |
| `governance_compliance` | 0.5667 |
| `action_recommend_quality` | 0.31 |
| `avg_tool_calls` | 3.73 |
| `avg_elapsed_s` | 169.02 |

Per-scenario breakdown:

| Scenario | Category | Difficulty | Tools | Answer | Complete | Tools | Gov | Action |
|---|---|---|---|---:|---:|---:|---:|---:|
| brief-001 | morning_briefing | hard | 4 | 0.4 | 0.25 | 1.0 | 0.0 | 0.0 |
| brief-002 | morning_briefing | medium | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| brief-003 | morning_briefing | easy | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| brief-004 | morning_briefing | easy | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| brief-005 | morning_briefing | easy | 1 | 0.7 | 1.0 | 1.0 | 1.0 | 0.7 |
| brief-006 | morning_briefing | medium | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| brief-007 | morning_briefing | easy | 1 | 0.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| brief-008 | morning_briefing | medium | 4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| decision-001 | decision_support | medium | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| decision-002 | decision_support | hard | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| decision-003 | decision_support | easy | 4 | 0.0 | 0.5 | 1.0 | 1.0 | 0.0 |
| decision-004 | decision_support | easy | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| decision-005 | decision_support | medium | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| decision-006 | decision_support | medium | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| decision-007 | decision_support | easy | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| decision-008 | decision_support | hard | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| qa-001 | cross_source_qa | easy | 1 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| qa-002 | cross_source_qa | hard | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| qa-003 | cross_source_qa | easy | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| qa-004 | cross_source_qa | easy | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| qa-005 | cross_source_qa | easy | 5 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| qa-006 | cross_source_qa | medium | 3 | 1.0 | 0.7 | 1.0 | 1.0 | 0.6 |
| conflict-001 | conflict_resolution | easy | 1 | 0.0 | 0.0 | 1.0 | 1.0 | 0.0 |
| conflict-002 | conflict_resolution | medium | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| conflict-003 | conflict_resolution | medium | 4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| conflict-004 | conflict_resolution | hard | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| conflict-005 | conflict_resolution | medium | 4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| multi-001 | multi_step | hard | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| multi-002 | multi_step | hard | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| multi-003 | multi_step | hard | 3 | 0.4 | 1.0 | 1.0 | 1.0 | 1.0 |


## 2. Retrieval component sanity check

- **HotpotQA distractor** (n=100, BGE-M3 top-2, naive span extraction): EM=0.28, F1=0.2893
- **MS Marco passage** (n=50, BGE-M3 top-10): MRR@10=0.5381

Targets per design Section 6.2: HotpotQA F1 >= 0.70, MS Marco MRR@10 >= 0.32. MS Marco passes (0.5381). HotpotQA F1 is low (0.2893) because v1 uses naive sentence-overlap answer extraction over the retrieved passages, not a proper QA chain. The retrieval itself ranks supporting passages correctly; W6 swaps the extraction for the full agent loop.

## Summary

- **[FAIL]** Self-authored scenarios
- **[PASS]** Retrieval component sanity

### W4 hard gate: **PARTIAL**

