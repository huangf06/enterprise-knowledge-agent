# Sprint 5 Frontier #4 Multi-LLM MoE (scaffold)

> **Pareto result:** [docs/sprint5_moe_pareto.md](sprint5_moe_pareto.md); fast-tier (n=10) replay across DeepSeek / Sonnet 4.6 / Haiku 4.5 / gpt-4o-mini.

Per-node routing config + cost-projection harness in place. Live dispatch wiring (translating Anthropic tool_use to OpenAI tools schema) is the Sprint 5 day-of integration step; the Pareto experiment above is a synthesize-only replay so the schema translation is not required to publish the result.

## What's ready

- `src/llm/moe_router.py`: `DEFAULT_MOE` config, `PRICING_USD_PER_1M` lookup, `route_for_node` + `estimate_cost` + `projected_per_query_cost`.
- `scripts/moe_projection.py`: reads the N2 baseline's per-node tokens and projects MoE-routed cost from `DEFAULT_MOE`.

## Honest projection from N2 baseline (post Sprint 5 default flip)

After the Sprint 5 Pareto measurement, `DEFAULT_MOE.synthesize` was flipped
from Sonnet 4.6 to DeepSeek (the v1 baseline route), because the measured
quality lift was within the n=10 noise floor and did not justify the 32x
cost. Latest `scripts/moe_projection.py`:

| Node | Baseline USD | MoE USD | Ratio |
|---|---:|---:|---:|
| plan | 0.0071 | 0.0069 | 0.98x |
| reflect | 0.0140 | 0.0140 | 1.00x |
| synthesize | 0.0160 | 0.0160 | 1.00x |
| tool_select | 0.0239 | 0.0218 | 0.91x |
| TOTAL | 0.0610 | 0.0587 | 0.96x |
| per-query avg | $0.00203 | $0.00196 | 0.96x |

Net effect: DEFAULT_MOE is ~the same cost as the v1 baseline, with critique
still on Haiku 4.5 (cheap structured-output endpoint for the closed
4-question checklist). The Pareto experiment that justified this flip lives
in [docs/sprint5_moe_pareto.md](sprint5_moe_pareto.md).

## Pre-flip context (kept for portfolio honesty)

Earlier projection with Sonnet 4.6 as the synthesize default showed total
cost ~12x baseline ($0.024 vs $0.002 per query). The v4.1 plan flagged
this as "too premium-heavy" before any measurement. The Sprint 5 Pareto
confirmed that projection's diagnosis: Sonnet's +0.07 ac quality lift sits
at the n=10 noise floor, so the premium does not earn its keep on this
workload.

## Vendor outage fallback (P8)

`route_for_node` returns the configured route. Live dispatch (not yet wired) should add: if upstream returns 5xx for 30s, fall back to DeepSeek for `synthesize` until upstream recovers. Documented in `docs/failure-modes.md` once Sprint 5 lands.

## Why we don't auto-run

The MoE projection is free (just arithmetic on cached token counts). A live MoE *measurement* requires running 30 scenarios per route variant on real APIs - 4 variants x 30 scenarios x ~$0.005-0.02 per call = $1-3 per ablation pass. Within budget but a Sprint 5 day-of decision, not autonomous.
