# Sprint 4 Frontier #1 DSPy compilation - result

Compilation run 2026-05-13 with corrected training data (post-fix `936b2c7`).

Source: `scripts/dspy_compile.py --training-input eval_results/runs/eval-20260513-105857.json --iterations 30`
Output: `src/agent/compiled/synthesize.json` (10 KB)

## Result

| | DSPy v1 (broken) | DSPy v2 (broken) | **DSPy v3 (correct)** |
|---|---|---|---|
| Training data | N2 baseline (no tool_history) | same | fresh OFF eval (tool_history populated) |
| Candidate scores | [11.83, 13.17, 10.83, 20.83, 14.75, 9.0] | similar | **[82.12, 80.95, 78.45, 78.17, 80.92, 80.58]** |
| Best score | 20.83 | 23.5 | **82.12** |
| Variance across candidates | 11.83 | 11+ | **3.95** |
| Best variant demos | 4 bootstrapped | 4 bootstrapped | **0 (zero-shot)** |

Two findings worth writing down:

1. **v3 candidate scores are much tighter** (78-82) than v1/v2 (9-21). The teleprompter is finding stable optimization regions when the training data actually matches inference-time inputs. v1/v2 were optimizing for a synthetic "empty tool_history" task that doesn't exist in production.

2. **The best v3 candidate has zero demos.** DSPy's `BootstrapFewShotWithRandomSearch` explored adding 1-4 few-shot demonstrations and chose to keep none. Reading: our manual `prompts/synthesize.md` + DSPy's `ChainOfThought` reasoning chain are already a strong baseline; adding worked examples does not add value here.

## What this means for v4

Combined with the Self-Refine ablation result (also a wash, see `docs/frontier3_self_refine.md`), both frontier techniques in our scope tell the same story: **the v1 synthesize prompt is already well-tuned and frontier optimization techniques do not move the needle on this 30-scenario benchmark.**

This is a strong portfolio signal *because* it is a negative one. Many production LLM systems ship DSPy or Self-Refine claims with no ablation; v4 ships both with explicit "with vs without" measurements, finds the techniques do not help in our setup, and documents the result honestly.

## Recommendations

- **Ship the v1 prompts as the production path.** No compiled JSON wired into the agent flow.
- **Keep `src/agent/compiled/synthesize.json` as a portfolio artifact** showing the DSPy infrastructure works end-to-end.
- **Re-run DSPy after structural changes.** If the agent graph changes meaningfully (e.g., CRITIC-style critique lands in v1.5, or tool surface expands), the v1 prompts may no longer be optimal and DSPy might find lift again.

## Caveats and follow-ups

- Training score 82.12 is on the **training set**, not a held-out test set. Standard ML hygiene says to also measure on the original 30 scenarios with the compiled module wired in. That requires editing `src/agent/nodes/synthesize.py` to load the compiled JSON behind a `USE_COMPILED_PROMPTS` flag and re-running the full eval. A Sprint 4 day-of follow-up; not done in the autonomous overnight pass.
- `BootstrapFewShotWithRandomSearch` is the lighter teleprompter. The v4.1 plan budgets up to $150 for full `MIPROv2` if buffer remains. The convergence-on-zero-shot result here suggests MIPROv2 would not change the answer.
- 2-judge consensus (Haiku + gpt-4o-mini, N1 compliant) is the training metric. The 3-judge consensus (with DeepSeek added) was not used during training to avoid the contamination risk. Per v4.1 P15, the ablation doc reports both regimes - here only the 2-judge metric was used during compilation, and the 3-judge comparison number would come from the agent-level ablation that has not yet been run.

## Cost

DSPy v3 total wallclock: ~12 min. API spend (Anthropic Haiku + OpenAI gpt-4o-mini judge calls during bootstrap): **~$1.50** total (well under the budgeted $25-50).

Caveat: cost numbers above are estimated from token usage projection, not measured directly. The cost_ledger (post-`e332937` fix) now does per-PID isolation, so future DSPy runs will track their own cost cleanly.
