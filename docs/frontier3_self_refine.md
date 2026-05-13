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
