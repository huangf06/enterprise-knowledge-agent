# Morning report v2 — 2026-05-14

> Hand-off after the second autonomous session continuing from
> `docs/overnight-report.md`. All work within Fei's authorized scope
> (single-experiment spend < $5, no `fly deploy`, no force-push, no
> destructive ops).

## TL;DR

This session closes out the three frontier-technique ablations the previous
session left scaffolded but unrun:

1. **DSPy agent-level ablation** (Frontier #1): wired compiled JSON behind
   `USE_COMPILED_PROMPTS=1`, ran fast-tier (n=10) OFF vs ON, multi-judged
   both. **Honest negative**: 2-judge regime (DSPy training metric) shows
   +0.05 on `answer_correctness` but the 3-judge regime (the comparison
   metric used by every other v4 ablation) shows **-0.03** — a Goodhart
   effect that v4.1 N1+P15 was designed to catch. Plus -1.0 on
   `cite_source_coverage` because the DSPy signature dropped the six
   citation exemplars from `prompts/synthesize.md`. Action_recommend_quality
   regresses in both judge regimes (-0.05 to -0.13). Doc:
   `docs/sprint4_dspy_agent_ablation.md`. **Ship default
   `USE_COMPILED_PROMPTS=0`.**

2. **Counterfactual robustness** (Frontier #7): replay runner against three
   perturbations on n=10 fast-tier. **Governance held at 1.00 across
   entity_swap, noise_injection, and doc_deletion.** entity_swap leaves
   answer_correctness unchanged (judge is content-checking, not entity-name
   matching). noise_injection is essentially a no-op (-0.01 ac). doc_deletion
   crashes ac to 0.20 — the canonical source was removed and the agent can
   not recover, but it also does NOT hallucinate the missing IDs
   (cite_id_grounded stays at 0.83). Graceful degradation, governance held.
   Doc: `docs/sprint6_counterfactual_result.md`.

3. **MoE synthesize Pareto** (Frontier #4): replay across four routes on
   n=10. **All four routes lie on the Pareto frontier** — none strictly
   dominates the others on (quality, cost, latency). DeepSeek is the
   lowest-cost / mid-latency / mid-quality. Sonnet 4.6 is the highest
   quality (+0.07 ac vs DeepSeek), highest cost (32×), and fastest of the
   slow ones (12s vs 41s). gpt-4o-mini is the fastest + cheapest at a
   modest quality cost (-0.04 ac). Caveat: n=10 noise floor is ±0.07 so
   the Sonnet vs DeepSeek delta is statistically at-noise.
   **Recommend default DeepSeek, expose Sonnet 4.6 as per-request opt-in
   for quality-critical work.** Doc: `docs/sprint5_moe_pareto.md`.

Total API spend this session: **~$0.45** (multi-judge OFF $0.07, multi-judge
ON $0.02, DSPy ON eval ~$0.005, counterfactual fast-tier ~$0.05, MoE Pareto
$0.17 — Sonnet dominates that line at $0.131). Well under any threshold.

Commits land on `main`, no force-push.

## What landed (verifiable in git)

| Commit | What |
|---|---|
| `907722d` | DSPy wire + ablation + scaffolds for counterfactual / MoE / compare scripts |
| _(next)_ | Counterfactual + MoE Pareto results + docs + README leaderboard refresh + multi-judge OFF baseline |

## Decisions waiting on Fei

These are intentionally NOT taken autonomously.

1. **`fly deploy` for F7.** Full checklist in `docs/deploy-checklist.md`.
   Pre-flight + secrets + Qdrant decision are all written down. **Fei picks
   the Qdrant option (A: Cloud free / B: sister Fly app / C: defer) and runs
   the deploy command interactively.**

2. **Fix-forward DSPy signature?** Two paths:
   - (a) v1.5: rewrite `SynthesizeSignature.__doc__` to include the six
     citation exemplars + the "end with next action" line, recompile,
     re-ablate. ~3h work, $1-2 spend. Result expected: ON answer_correctness
     and citation-grounded both recover; the comparison-regime ac delta
     might still be statistically at-noise.
   - (b) Ship as-is with the honest negative; cite as a portfolio lesson
     about signature-as-prompt-engineering. ~0h work.

   I have NOT done (a). **Recommendation: (b)**. The honest negative is
   the more defensible portfolio framing.

3. **MoE production routing.** The Pareto table shows quality / cost /
   latency across four vendors. **Recommendation: default `synthesize` to
   DeepSeek (current state), expose Sonnet 4.6 as a per-request opt-in via
   `route_for_node` once `messages_create` is wired to read it.** The
   `DEFAULT_MOE` in `src/llm/moe_router.py` still points synthesize to
   Sonnet 4.6 — that should be flipped back to DeepSeek before the next
   `MOE_ENABLED=1` deploy. ~10 min edit, can do solo if Fei wants.

4. **Blog publishing.** Outline in `docs/blog-outline.md`. The numbers
   placeholders are now real and ready to be lifted in. Voice is yours.

5. **Demo video.** `docs/demo-script.md` is unchanged. The screen capture
   is yours.

## Memory updates I made

- `project_eka_v4_second_session.md` (new) — captures session-closing state
  including the 3 ablation outcomes, total spend, and the "what only Fei
  can do" set.
- `MEMORY.md` index updated to point at the new entry.

## What I did NOT do

- `fly deploy` — gated, requires Fei + Qdrant decision.
- `git push --force` or any destructive op — never.
- Modify `.env` or upload secrets — never.
- Re-run the OFF Self-Refine ablation (already done in prior session).
- DSPy MIPROv2 full compile (the cheaper BootstrapFewShot already converged
  to zero-shot; MIPROv2 at $50-150 budget would not change the answer per
  the prior result writeup).
- Flip `DEFAULT_MOE.synthesize` from Sonnet 4.6 back to DeepSeek — flagged
  in Decision #3 for your sign-off since changing it depends on which
  route you actually want as the production default.

## Total project state at sunrise

- **All 10 v4.1 frontier + foundation features live** (F1-F8, N2, A1-A7,
  Frontier #1/#3/#4/#7).
- **All four ablations have honest with-vs-without tables**: Self-Refine
  (prior session), DSPy (this session), Counterfactual (this session), MoE
  (this session).
- **3 honest negatives + 1 honest positive**: Self-Refine = no, DSPy = no
  (with diagnosis), MoE = "depends on what you value" (all 4 on Pareto
  frontier), Counterfactual = governance held under perturbation.
- **0 destructive ops, 0 force pushes, 0 unauthorized deploys.**
- **101/101 tests green** as of 14:32 CEST 2026-05-13.
- **Total project API spend across both sessions: under $1**.
