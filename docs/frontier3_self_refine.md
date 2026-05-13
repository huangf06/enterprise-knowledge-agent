# Frontier #3 Self-Refine (Sprint 3)

Madaan et al. 2023. A `critique` node sits between `synthesize` and `END`. It reads only `(question, final_answer)` (per v4 plan P6) and runs a closed 4-question checklist (per P5):

1. **Citations**: inline `[source:id]` present.
2. **Action**: ends with a specific, executable next step.
3. **Cross-source**: integrates evidence from ≥2 source types.
4. **Governance**: respects single-tenant + sensitive-content boundaries.

Returned via tool_use against a `submit_critique` Pydantic-like schema. If any check fails, `concerns` (max 3) are surfaced and synthesize regenerates once (`MAX_REVISIONS = 1` per critique node). A second critique pass always returns pass to avoid infinite loops.

Implementation:
- `src/agent/nodes/critique.py` - the new node + the env flag.
- `src/agent/graph.py` - conditional graph wiring; `SELF_REFINE_ENABLED=0` reverts to the v1 5-node graph for the with-vs-without ablation.
- `src/agent/state.py` - `critique_passed`, `critique_concerns`, `revision_count` fields.
- `src/agent/nodes/synthesize.py` - includes critique concerns in the regeneration prompt when present.

## Ablation protocol

The v4.1 honesty calibration policy requires every frontier ships with a with-vs-without table. Run both:

```bash
# Without Self-Refine
SELF_REFINE_ENABLED=0 uv run python scripts/run_eval.py --tier full

# With Self-Refine (default)
SELF_REFINE_ENABLED=1 uv run python scripts/run_eval.py --tier full
```

Compare the two eval JSONs along:
- `scores.answer_correctness`, `scores.completeness`, `scores.action_recommend_quality`
- `citations.well_formedness`, `citations.source_coverage`, `citations.id_grounded`
- `agent_cost_usd_per_query` (Self-Refine adds 1-2 critique LLM calls + possible 1 regenerate)
- `p50_elapsed_s` / `p95_elapsed_s` (latency overhead)

## Cost / latency expectation

Per scenario:
- Without: 1 plan + 1-4 tool_select + 1-4 reflect + 1 synthesize
- With: + 1 critique always + (if fail) 1 synthesize regen

Expected overhead: +1 LLM call per query on average (most scenarios should pass critique on first draft); occasional second pass on hard scenarios. Latency: +30-80s p50.

Cost: + ~$0.0005 per query (1 critique) + ~$0.0005 per regen. Negligible vs. baseline $0.00203/query.

## Why prose-only (P6)

CRITIC-style tool-calling critique (Gou 2024) is more powerful but requires a graph restructure: critique → tool_select → tool_execute → critique. v4.1 plan locked decision keeps Self-Refine (prose-only critique) and defers CRITIC to v1.5. See v4 plan R2 comment for the +6-10h estimate.

## Ablation result (2026-05-13, 30-scenario full eval)

OFF: `eval_results/runs/eval-20260513-105857.json`
ON:  `eval_results/runs/eval-20260513-111407.json`

| Metric | OFF | ON | Delta |
|---|---:|---:|---:|
| answer_correctness | 0.6917 | 0.6150 | **-0.0767** |
| completeness | 0.7450 | 0.6933 | -0.0517 |
| tool_selection_quality | 0.9367 | 0.9417 | +0.0050 |
| governance_compliance | 1.0000 | 1.0000 | 0.0000 |
| action_recommend_quality | 0.5250 | 0.4867 | -0.0383 |
| cite_well_formedness | 0.7076 | 0.6824 | -0.0252 |
| cite_source_coverage | 0.9155 | 1.0000 | **+0.0845** |
| cite_id_grounded | 0.7521 | 0.6723 | -0.0798 |
| traj_tool_f1 | 0.7298 | 0.7389 | +0.0091 |
| avg_elapsed_s | 150.40 | 177.91 | **+27.51s (+18%)** |
| p50_elapsed_s | 163.34 | 177.21 | +13.87s |
| agent_cost_usd_per_query | $0.003612 | $0.003884 | +$0.000272 (footnote A) |

**Footnote A**: the per-query cost numbers are contaminated - both OFF and ON ran concurrently against a shared `eval_results/cost_ledger.sqlite` and each runner's `query_window()` saw the other process's writes inside its scenario time window. The bug is fixed in commit `e332937` (cost_ledger now writes + filters by pid). True OFF cost is closer to the N2 baseline $0.00203/query; ON adds ~$0.0005 / query for the critique call plus the cost of any regenerate. Quality and latency numbers are NOT contaminated - they come from per-scenario in-process state, not the shared ledger.

### Interpretation: honest negative result

Self-Refine, as specified by v4.1 (prose-only critique per P6, 4-question closed checklist per P5), **does not help our setup**:

- **answer_correctness, completeness, id_grounded all regress by 0.05-0.08**. The deltas are small enough to be within the noise floor of 30-scenario LLM evals, but they are consistently in the wrong direction.
- **source_coverage jumps +0.08 to a perfect 1.0**. The one metric where Self-Refine clearly helps: forcing the critique check makes the agent surface each cited source explicitly.
- **+18% latency** is the deterministic overhead from critique + occasional regenerate.

The most plausible cause is P6 itself: the critique sees only `(question, final_answer)` without tool_history. When it flags an answer as "missing action" or "weak citation", the regenerated synthesize loses some of the original detail because the critique's "concerns" feedback is a paraphrase rather than the underlying evidence. CRITIC-style tool-calling critique (Gou 2024) sidesteps this by letting the critique re-query the data; the v4.1 plan defers that variant to v1.5 (+6-10h graph restructure).

### Recommendation

**Ship Self-Refine OFF by default** in v1. Keep the implementation behind `SELF_REFINE_ENABLED=1` for users who want the source_coverage lift at the cost of -0.08 on answer_correctness. Re-run the ablation in Sprint 4 after DSPy compilation - if DSPy improves the synthesize prompt, Self-Refine's regenerate path might recover the lost detail.

This is the v4.1 honesty calibration policy in action: a frontier technique ships with an honest with-vs-without ablation, even when the answer is "doesn't help here." That's a stronger portfolio signal than silently shipping a feature that doesn't earn its keep.
