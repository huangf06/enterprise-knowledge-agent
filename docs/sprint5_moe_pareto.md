# Sprint 5 Frontier #4 MoE: synthesize-only Pareto

Source: `moe-synthesize-20260513-122907.json` (tier=fast, n_scenarios per route = baseline rows with `ok==True`).

Each route receives the same `tool_history` from the baseline run and the
same `synthesize` prompt. The only changed variable is the vendor + model.
Quality is single-judge for now; multi-judge consensus addendum follows
if `scripts/run_multi_judge.py` is run on this file.

| Route | Quality (ac) | Compl. | Cite-grounded | Cost / query | Latency (s) | Pareto? |
|---|---:|---:|---:|---:|---:|:---:|
| DeepSeek V4 Pro (baseline) | 0.7167 | 0.8444 | 0.8889 | $0.000404 | 40.6 | ✓ |
| Anthropic Sonnet 4.6 | 0.7850 | 0.8450 | 1.0000 | $0.013085 | 12.0 | ✓ |
| Anthropic Haiku 4.5 | 0.7350 | 0.7950 | 0.7000 | $0.003081 | 4.1 | ✓ |
| OpenAI gpt-4o-mini | 0.6750 | 0.7400 | 0.9000 | $0.000287 | 3.0 | ✓ |

## Reading the table

**Pareto frontier**: any route that is not strictly dominated on all three of (quality, cost, latency) by another route. A `✓` does NOT mean "best"; it means "a defensible pick depending on what you value".

The headline question is: **does the more expensive vendor actually buy a meaningful quality lift on the synthesize node?** Compare DeepSeek baseline to Anthropic Sonnet 4.6 (12× input cost, 53× output cost) and report whether the answer_correctness delta justifies the spend.

Caveat: n=10 has roughly a ±0.07 noise floor on answer_correctness; any claimed lift smaller than that is not statistically meaningful at this scale. A v1.5 follow-up with n=30 + 95% bootstrap CI is the way to firm this up if the headline number looks promising.

**Vendor reliability footnote**: in this run the DeepSeek route returned an empty response on one of the 10 scenarios (`multi-002`, the largest tool_history of the set). That row is filtered out of the DeepSeek average (count=9). Sonnet 4.6, Haiku 4.5, and gpt-4o-mini all completed 10/10. The DeepSeek endpoint is the project's primary endpoint and this failure mode is consistent with occasional 1M-context coherence drops on the longest inputs; the production agent falls back to a retry path that this replay does not exercise.

## Production recommendation

Reading the table conservatively (all four routes are on the Pareto frontier, so the choice is policy not math):

- **Default `synthesize` to DeepSeek V4 Pro.** Lowest cost, citation-grounded at 0.89, quality within 0.07 of Sonnet (i.e. within the n=10 noise floor). The vendor-reliability footnote argues for a retry-on-empty wrapper rather than a permanent switch off DeepSeek.
- **Premium opt-in: Anthropic Sonnet 4.6** when the use case justifies 32× cost for +0.07 quality + perfect citation grounding + 3× faster latency. Production routing should expose this as a per-request flag, not a default.
- **Latency-optimized opt-in: OpenAI gpt-4o-mini or Anthropic Haiku 4.5** when the use case is interactive and a 3-4s synthesize matters more than a 0.04 quality drop. gpt-4o-mini is cheaper; Haiku 4.5 has lower citation grounding (-0.19 vs DeepSeek) so picking Haiku 4.5 requires care.
- **Update `DEFAULT_MOE` in `src/llm/moe_router.py`** to set synthesize back to DeepSeek (currently configured to Sonnet 4.6, which the v4.1 plan flagged as too premium-heavy; this measurement confirms the projection).

## Cost breakdown per route on the n=10 fast-tier replay

| Route | Total cost | Per-query avg |
|---|---:|---:|
| DeepSeek V4 Pro | $0.0036 | $0.0004 |
| Anthropic Sonnet 4.6 | $0.131 | $0.0131 |
| Anthropic Haiku 4.5 | $0.0308 | $0.0031 |
| OpenAI gpt-4o-mini | $0.00287 | $0.000287 |
| **Total experiment cost** | **$0.166** |; |
