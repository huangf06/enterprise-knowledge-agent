# Sprint 5 Frontier #4 Multi-LLM MoE (scaffold ready)

Per-node routing config + cost-projection harness in place. Live dispatch wiring (translating Anthropic tool_use to OpenAI tools schema) is the Sprint 5 day-of integration step.

## What's ready

- `src/llm/moe_router.py`: `DEFAULT_MOE` config, `PRICING_USD_PER_1M` lookup, `route_for_node` + `estimate_cost` + `projected_per_query_cost`.
- `scripts/moe_projection.py`: reads the N2 baseline's per-node tokens and projects MoE-routed cost from `DEFAULT_MOE`.

## Honest projection from N2 baseline

`scripts/moe_projection.py` over the post-F1 rejudged baseline:

| Node | Baseline USD | MoE USD | Ratio |
|---|---:|---:|---:|
| plan | 0.0071 | 0.0069 | 0.98x |
| reflect | 0.0140 | 0.0140 | 1.00x |
| synthesize | 0.0160 | **0.6776** | **42.4x** |
| tool_select | 0.0239 | 0.0218 | 0.91x |
| TOTAL | 0.0610 | 0.7204 | 11.8x |
| per-query avg | $0.00203 | **$0.02401** | 11.8x |

**Hard finding**: routing synthesize to Sonnet 4.6 makes total cost ~12x. DEFAULT_MOE is too premium-heavy for the high-frequency `synthesize` calls in our 30-scenario eval (synthesize fires once per query, but the input grows with tool_history so per-call cost is high on Sonnet).

## Sprint 5 decision points

The MoE Pareto demo is the v4 hero feature for "I tested real cost/quality trade-offs". Before shipping `DEFAULT_MOE` as the production deploy config, decide:

1. **synthesize routing**:
   - Sonnet 4.6 (current default): 12x cost, presumably higher quality. Need to measure.
   - Haiku 4.5: ~3-4x cost, modest quality lift.
   - gpt-4o-mini: ~1.5x cost, comparable quality to DeepSeek.
   - DeepSeek (no MoE): 1x cost, the v1 baseline.
2. **measurement plan**: run the same 30 scenarios under each route, compare 3-judge consensus answer_correctness. Lift > 0.05 justifies the cost; below that, ship the cheaper variant.

## Vendor outage fallback (P8)

`route_for_node` returns the configured route. Live dispatch (not yet wired) should add: if upstream returns 5xx for 30s, fall back to DeepSeek for `synthesize` until upstream recovers. Documented in `docs/failure-modes.md` once Sprint 5 lands.

## Why we don't auto-run

The MoE projection is free (just arithmetic on cached token counts). A live MoE *measurement* requires running 30 scenarios per route variant on real APIs - 4 variants x 30 scenarios x ~$0.005-0.02 per call = $1-3 per ablation pass. Within budget but a Sprint 5 day-of decision, not autonomous.
