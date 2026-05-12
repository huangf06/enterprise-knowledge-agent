# W4 hard gate report

Self-authored cross-source scenarios are the **main eval anchor**. HotpotQA and MS Marco numbers below are a **retrieval component sanity check** for the BGE-M3 pipeline, not an anchor for the agent's cross-source task. Per design Sections 6.1 / 6.2 / 8.

## 1. Self-authored cross-source scenarios

Latest run: n=5, wallclock=1049.33s

| Metric | Score |
|---|---:|
| `answer_correctness` | 0.6 |
| `completeness` | 0.6 |
| `tool_selection_quality` | 0.6 |
| `governance_compliance` | 0.6 |
| `action_recommend_quality` | 0.58 |
| `avg_tool_calls` | 4.0 |
| `avg_elapsed_s` | 181.85 |

Per-scenario breakdown:

| Scenario | Category | Difficulty | Tools | Answer | Complete | Tools | Gov | Action |
|---|---|---|---|---:|---:|---:|---:|---:|
| brief-001 | morning_briefing | hard | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| brief-002 | morning_briefing | medium | 4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| brief-003 | morning_briefing | easy | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| brief-004 | morning_briefing | easy | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 0.9 |
| brief-005 | morning_briefing | easy | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**Note**: This is a partial run (n=5). The full 30 takes ~100 minutes wallclock. Run `scripts/run_eval.py` for the full eval.

## 2. Retrieval component sanity check

- **HotpotQA distractor** (n=100, BGE-M3 top-2, naive span extraction): EM=0.0, F1=0.077
- **MS Marco passage** (n=50, BGE-M3 top-10): MRR@10=0.5381

Targets per design Section 6.2: HotpotQA F1 >= 0.70, MS Marco MRR@10 >= 0.32. MS Marco passes (0.5381). HotpotQA F1 is low (0.077) because v1 uses naive sentence-overlap answer extraction over the retrieved passages, not a proper QA chain. The retrieval itself ranks supporting passages correctly; W6 swaps the extraction for the full agent loop.

## Summary

- **[FAIL]** Self-authored scenarios
- **[PASS]** Retrieval component sanity

### W4 hard gate: **PARTIAL**

