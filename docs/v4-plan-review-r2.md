# Second-pass review of v4 frontier plan

> Critique on 2026-05-12. Second round of independent review (after Codex round 1 on v3).
> Verdict: ship after 3 surgical corrections, no replan needed.
> Corrections applied as v4.1 patch in `docs/v4-frontier-plan.md` (same file).

## Verdict

Ship after fixing the Sprint 1 math and the CRITIC effort estimate. The two non-negotiables (N1 DSPy contamination, N2 baseline) and the five recommendations all landed correctly. There are three genuine residual hazards in v4 itself that did not exist in v3, plus two budget arithmetic errors that flatter the plan by ~10-15 hours.

## A. What v4 captured cleanly

- N1 DSPy contamination locked precisely. F3 pool = Haiku + GPT-4o-mini during Sprint 4 compilation, DeepSeek excluded. Exactly the surgical fix.
- N2 baseline moved to Sprint 1 day-1, 2h budgeted, scope right (per-node tokens, USD, p50/p95).
- R3 non-protagonist swap locks the entity perturbation to "EY → PwC" not "Sarah → Alice". Avoids the synthetic-data regen rabbit hole and the injection-guard collision in one move.
- R5 day-1 checklist went from 3 items to 11. Cohere quota, RAGAS dep tree, DNS propagation prep, OpenAI cost cap — all there.
- P1-P11 process locks are clean. P3 (redact `expected_topics` from judge during DSPy) is the right surgical guard against keyword-leak reward hacking.
- O1-O3 citations correctly demoted to doc-level (no implementation cost).

## B. Residual hazards v4 introduced or didn't fully close

### 1. CRITIC is NOT a 0h cite swap (R2)

v4 line 29 marks it "0h (cite swap, impl same)." That's wrong. Self-Refine's critique node reads prose only; CRITIC's value is that the critique step calls tools to verify claims. On this LangGraph (`src/agent/graph.py:27-41`), `tool_execute` is a separate node downstream of `tool_select`. To let the critique node call tools you either:
- restructure the graph so critique can route back into tool_select → tool_execute → critique, or
- give the critique node its own tool-calling capability inline.

Either is +6-10h, not zero. If R2 ships as written, the critique node will not actually call tools and you'll have cited CRITIC while implementing Self-Refine, which is exactly the misnaming failure mode Opus flagged on PRM. **Fix**: either budget the +6-10h honestly, or revert citation to Self-Refine (Madaan 2023) and ship the cheaper prose-only critique.

### 2. CRITIC latency multiplier ignored

Self-Refine: 2 critique rounds × 1 LLM call each = 2 extra LLM calls per query. CRITIC: each critique round triggers tool calls (2-4 tool calls × 3-15s each at current latency) + LLM. Per-query latency on v1's 169s base goes to ~300-400s with CRITIC. Sprint 3 eval at 30 scenarios = 2.5-3 hours per pass, not 100 minutes. The A5 three-tier quick-eval (smoke 3 / fast 10 / full 30) mitigates this but should be stated: full eval at Sprint 3 EOW only, fast tier daily.

### 3. F3 dual-regime evaluation

Under N1, DSPy in Sprint 4 trains against a 2-judge consensus (Haiku + GPT-4o-mini). Every other ablation (Sprints 2-3, 5-7) uses the 3-judge consensus that includes DeepSeek. The DSPy ablation table numbers are therefore not directly comparable to the other ablation tables. v4 doesn't address this. Two fixes are acceptable: (a) report DSPy on BOTH metrics in its ablation doc (2-judge + 3-judge), with a paragraph explaining why; (b) re-run all ablations against the 2-judge metric after DSPy compilation. (a) is cheap, (b) is honest but expensive — pick (a).

### 4. A7 trace replay needs a metric-scope line

v4 lists trace replay (A7, 6-8h) without specifying what runs per replay. If it runs the full LLM judge per replay in CI, you'll burn the OpenAI $100/month cap inside a week. **Required scope**: trace replay in CI runs ONLY structural metrics (tool F1, citation algorithmic, governance assertions); LLM-judge metrics run at sprint boundaries only. Add this as P12.

### 5. P2 single-node DSPy scope is not in the sprint plan

v4 process P2 says "optimize one node at a time, start with synthesize." But the Sprint 4 row (line 143) just says "Frontier #1 DSPy (30h budgeted, week-9 day-2 gate)." Without P2 explicitly in the sprint description, scope creep is the default and 30h evaporates against a joint Module. **Fix**: Sprint 4 should read "Frontier #1 DSPy on synthesize node only; if buffer remains, extend to plan node."

## C. Budget arithmetic that flatters v4

Sprint 1 is undercounted by ~7h. Day-1 checklist (3h) + N2 baseline (2h) + F7 deploy (15h, per F7 foundation line 77) + F1 structured outputs (4h) + A1 retrieval ablation (4h) + A2 reranker (4h) = 32h. v4 row says 25h. Either F7 dropped to ~8h silently or there's a 7h hole. At 32h over 2 weeks that's 16h/week, well over the 8h/week burnout cap.

Sprint 2 is 33h / 2 weeks = 16.5h/week. Also over cap.

Counterfactual range math is off. v4 line 86: "12-15h − 2-4h R3 + 2h P10 + 2-3h P11; net 14-16h". Correct range is 12 − 4 + 2 + 2 = 12 to 15 − 2 + 2 + 3 = 18, i.e., 12-18h, not 14-16h. Minor but the upper end matters when total is already tight.

Realistic v4 total: ~185h wall-clock / ~148h with Codex, not 177/142. That's above 16 weeks × 8h/week = 128h. v4 will drop both PAIR AND likely one of {A7 trace replay, A4 case study, O1-O3 polish}. Plan for that explicitly: state which is the next-to-drop after PAIR.

## D. One thing I'd add to v4

A single line in `docs/v4-frontier-plan.md` under "Honesty calibration policy": **"If A7 trace replay is dropped due to buffer overrun, then no DSPy ablation claim ships — the per-category regression check is the only thing that makes DSPy numbers honest, and without it the headline number can hide a regression."** This makes the dependency chain visible: trace replay isn't optional polish, it gates DSPy publishing.

## E. Final calibration

Execute v4 with three corrections, no replan:

1. **Re-mark R2 effort honestly.** Either +6-10h for real tool-calling CRITIC, or revert to Self-Refine cite.
2. **Recompute Sprint 1 and Sprint 2 totals.** State the 12-16h/week pace honestly so the 8h/week cap can be revisited or sprints replanned.
3. **Add P12** (trace replay = structural metrics in CI only) **and the "A7 gates DSPy publishing" line**.

Everything else is locked correctly. Two non-negotiables addressed, five recommendations adopted, eleven process improvements logged — Codex's fixes survived translation to v4 faithfully. The remaining issues are arithmetic and one mis-scoped item, not strategic.
