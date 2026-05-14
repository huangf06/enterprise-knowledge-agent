# v4 Frontier Enhancement Plan

> Status: **active**. Supersedes `v3-frontier-plan.md`. Based on an independent review of v3.
> Locked 2026-05-12.

## Why v4

v3 was reviewed by Codex (OpenAI ecosystem, orthogonal to Opus) and the verdict was **"Iterate, one targeted change. Opus 90% right. Two genuine misses."** Both misses are technical, load-bearing, and were not visible to Opus:

1. **DSPy contamination**: judge uses same client as agent. DSPy optimization in Sprint 4 would reward-hack against its own model class. v3 schedules multi-judge in Sprint 2 but does not gate DSPy's training metric to exclude the agent's model. Locked fix.
2. **No v1 cost/latency baseline**: README already shows "169s avg latency" but no $/query, no p50/p95, no token-per-node breakdown. Without this, MoE / cache / DSPy claims are unfalsifiable. Locked fix.

Plus 6 smaller hazards across the 4 frontier techniques, 8 missing Sprint 1 day-1 verifications, and 3 orthogonal 2024-2025 papers Opus didn't cite.

## What changed from v3 (delta only)

### Non-negotiable changes (locked)

| # | Change | Source | Effort |
|---|---|---|---|
| **N1** | **DSPy training metric excludes the agent's model class.** Multi-judge median in Sprint 4 = Haiku 4.5 + GPT-4o-mini only; DeepSeek (the agent's primary) dropped from judge pool during DSPy compilation. State this in DSPy ablation doc explicitly. | Codex B1 | +0h (process change) |
| **N2** | **v1 cost/latency baseline in Sprint 1 day-1.** Full eval run with token counts per node, USD/query at DeepSeek list price, p50/p95 latency. Becomes the BASELINE all subsequent claims (MoE Pareto, semantic cache lift, DSPy improvement) compare against. | Codex B2 | +2h |

### Strongly recommended additions (accepted)

| # | Change | Source | Effort |
|---|---|---|---|
| **R1** | **Add A7 trace replay regression harness.** Capture real traces from F7 Sprint-1 deploy, serialize with gold answers, replay against every new graph version in CI. Catches per-category regressions invisible in headline metric. Generates A4 case study material organically. Keep A4 (failure case study) AND add trace replay — they compound. | Codex F | +6-8h |
| **R2** (v4.1 corrected) | **Keep Self-Refine (Madaan 2023) cite.** Critique node reads `(question, final_answer)` only per P6 — prose-only. CRITIC-style tool-calling critique (Gou 2024) is v1.5 next-step; requires graph restructure (+6-10h) to route critique → tool_select → tool_execute → critique, which doesn't fit the v4 budget. Reverting cite avoids the misnaming failure mode (citing CRITIC while implementing Self-Refine). | Codex B4 + r2 B1 | 0h |
| **R3** | **Counterfactual entity-swap restricted to non-protagonist entities.** "EY contract" → "PwC contract", NOT "Sarah" → "Alice". Avoids regenerating synthetic data + avoids retesting injection guard on names it wasn't tuned for. | Codex B5, B6 | -2 to -4h (saves regeneration) |
| **R4** | **Quick-eval at 3 tiers**: smoke (3 scenarios, <30s), fast (10 scenarios, <5min), full (30 scenarios). Mitigates eval-loop slowness as scope compounds. | Codex D | +1h |
| **R5** | **Sprint 1 day-1 checklist expanded from 3 → 11 items.** See section "Sprint 1 day-1 checklist" below. | Codex E | +1-2h |

### Process improvements (locked, no time cost)

| # | Change | Source |
|---|---|---|
| **P1** | DSPy: gate at **week 9 day 2** (not week 10) if not converging; switch to manual-prompt-iteration fallback | Codex C/DSPy |
| **P2** | DSPy: optimize **ONE node at a time** (start with `synthesize`), not joint Module across 5 nodes | Codex C/DSPy |
| **P3** | DSPy: **redact `expected_topics` from judge view** during DSPy training to prevent keyword leak | Codex C/DSPy + B1 |
| **P4** | DSPy: design signatures with **frozen cache prefix + varying suffix**; budget $50-150 for compilation API cost | Codex B3 |
| **P5** | Self-Refine (now CRITIC): **closed 4-question checklist** (citation? action? cross-source? governance?); refuse open-ended critique | Codex C/Self-Refine |
| **P6** | Self-Refine: **drop tool_history from critique signature**; critique sees `(question, final_answer)` only | Codex C/Self-Refine |
| **P7** | MoE: **USD-only Pareto**, never tokens. Document chain p95 = sum-of-nodes, not max | Codex C/MoE |
| **P8** | MoE: vendor outage fallback documented in failure-modes.md (synthesize → DeepSeek if Anthropic down) | Codex C/MoE |
| **P9** | MoE: extend F1 structured outputs to critique node, not just judge (cross-vendor parser differences) | Codex C/MoE |
| **P10** | Counterfactual noise-injection: explicit 2h budget for retrieval wrapper | Codex C/Counterfactual |
| **P11** | Counterfactual doc-deletion: explicit 2-3h budget for ground-truth doc IDs in scenarios.json | Codex C/Counterfactual |
| **P12** (v4.1 new) | **Trace replay (A7) CI runs ONLY structural metrics** (tool F1, citation algo verify, governance assertions). LLM-judge metrics run at sprint boundaries only, never in CI. Without this the OpenAI $100/month cap burns in <1 week. | r2 B4 |
| **P13** (v4.1 new) | **Sprint 4 DSPy scope = `synthesize` node only.** If buffer remains, extend to `plan` node. Joint optimization across 5 nodes on 30 scenarios is the failure mode. Sprint description in plan must read "DSPy on synthesize node only first." | r2 B5 |
| **P14** (v4.1 new) | **Full eval (30 scenarios) ONLY at sprint boundaries.** Fast tier (10 scenarios) daily during active sprint. CRITIC/Self-Refine adds 2x agent inference per query; full eval at Sprint 3 = ~2.5-3 hours, not 100 min. | r2 B2 |
| **P15** (v4.1 new) | **DSPy ablation reports on BOTH judge regimes**: 2-judge consensus (Haiku + GPT-4o-mini, the training metric) AND 3-judge consensus (+ DeepSeek, the comparison metric used by every other ablation). One paragraph in DSPy ablation doc explaining why. Cheap fix vs re-running all ablations. | r2 B3 |

### Optional (doc-level only, no implementation)

| # | Change | Source |
|---|---|---|
| **O1** | Cite Deliberative Alignment (Guan 2024) [OpenAI, Dec 2024] in `docs/governance-design.md` to replace Constitutional cut framing. Honest reframe: "Cut because RBAC already 10/10, not because inference-time policy is fake." | Codex D + G |
| **O2** | Cross-reference BFCL v3 (Berkeley 2025) tool-call benchmark in F6 trajectory eval doc, as alternative to HotpotQA framing | Codex G |
| **O3** | One-paragraph TextGrad (Yuksekgonul Sept 2024) compare-and-contrast in DSPy ablation doc | Codex G |

### Rejected from v3 review (Codex disagreed with Opus, kept v3 stance)

- **PRM cut**: Codex agrees with cut but offered "rescue" via ProcessBench / Generative Reward Models. Rescue rejected — Langfuse per-node tracing already gives the visible artifact, no need to reintroduce.
- **Constitutional cut**: Codex agrees with cut but corrects Opus's reasoning. Stance now: "Cut because marginal lift is zero, not because technique is fake." Captured in O1.
- **DSPy 30h budget pessimistic**: Codex argues 15-25h realistic. Keep 30h as ceiling for safety; gate at week 9 day 2 (not week 10) per P1.
- **NIAH cut**: both reviewers agree, keep cut.
- **PAIR demotion**: both agree, keep demoted to optional buffer-only.

## v4 final scope

### Foundation layer (~49h after additions)

(F1-F8 same as v3 except F5/F9 cut; +2h for v1 baseline run on day 1)

- F1 Structured outputs judge (4h) — extended P9 to also cover critique node
- F2 RAGAS 4-metric integration (8h)
- F3 Multi-LLM-judge consensus + inter-judge kappa (6h) — N1 locks DeepSeek out during DSPy training
- F4 Algorithmic citation groundedness (4h)
- F6 Trajectory eval (6h) — O2 adds BFCL cross-reference
- F7 Public deploy + Langfuse + OpenTelemetry (15h)
- F8 mkdocs documentation site (4h)
- **N2 v1 cost/latency baseline (2h)** — NEW Sprint 1 day-1

### Frontier layer (4 techniques, ~70h, slightly leaner)

- Frontier #3 **Self-Refine (Madaan 2023)**: 10-12h. Critique node reads `(question, final_answer)` only, closed 4-question checklist per P5/P6. CRITIC tool-calling variant deferred v1.5.
- Frontier #1 DSPy compiled prompts: 30h budget, week-9 day-2 gate; P1-P4 locked
- Frontier #4 Multi-LLM MoE: 10-12h + P7-P9; +4h vendor outage fallback if shipping; total 14-16h
- Frontier #7 Counterfactual robustness: 12-15h - 2-4h saved by R3, + 2h retrieval wrapper P10, + 2-3h doc-ID scenarios P11; net **12-18h** (v4.1: arithmetic correction; upper bound matters when total is tight)

### Production-engineering additions (~31h, +7h vs v3)

- A1 Retrieval ablation (BM25/BGE-M3/hybrid/+reranker) (4h)
- A2 Reranker (Cohere or BGE) (4h)
- A3 Semantic cache + cost/latency leaderboard (8h)
- A4 Failure mode case study (6h) — generated from trace replay data
- A5 Quick-eval 3-tier (smoke/fast/full) (2h+1h = 3h with R4)
- A6 Honest ablation table per frontier technique (embedded)
- **A7 Trace replay regression harness (6-8h)** — NEW per R1

### Polish

- Signature blog (8h)
- README final + demo video (4h)
- O1/O2/O3 doc-level paper citations (1h)

## Total v4 budget (v4.1 corrected)

| Block | Wall-clock | With Codex 0.8x |
|---|---|---|
| Foundation (F1-F8 + N2 baseline) | 49h | 39h |
| Frontier (4 techniques: Self-Refine + DSPy + MoE+outage + Counterfactual 12-18h) | 68-76h | 54-61h |
| Production additions (A1-A7) | 31h | 25h |
| Polish (blog + video + doc citations) | 13h | 10h |
| Optional Frontier #6 PAIR capped | 10h | 8h |
| **TOTAL (without PAIR)** | **161-169h** | **128-135h** |
| **TOTAL (with PAIR)** | **171-179h** | **137-143h** |

**Honesty note (per r2 review §C)**: Sprint 1 (32h / 2 weeks = 16h/week) and Sprint 2 (33h / 2 weeks = 16.5h/week) exceed the 8h/week burnout cap stated in the risk register. Two paths:
- **(a)** accept 12-16h/week pace for sprints 1-2 only, then taper to 8h/week from Sprint 3 onward
- **(b)** stretch sprints 1-2 to 4 weeks each (8 weeks total), pushing project completion week 18 not week 14

Reviewer recommended (a). Track A collision in those 4 weeks → automatically falls back to (b).

**Next-to-drop order if buffer overrun (after PAIR)**:
1. PAIR (already optional)
2. MoE vendor outage fallback (4h) — document risk in failure-modes.md instead
3. F8 mkdocs site (4h) — use GitHub-rendered docs/ folder instead
4. A2 reranker (4h) — keep BGE-M3 single-stage retrieval
5. O1-O3 paper citations (1h) — minimal loss
6. (stop) — any further cut hits load-bearing items; replan instead

v3 was 143h/115h. v4 adds 18-23h for Codex's non-negotiables + recommendations.

## Sprint 1 day-1 checklist (expanded per Codex E)

Must verify BEFORE writing any new code (~3h budget):

1. **DeepSeek 1M context coherence past 200K tokens** — test with synthetic 250K-token prompt, verify output not gibberish
2. **Langfuse Cloud public dashboard reachable** — sign up, verify public read-only mode works
3. **Multi-vendor LLM keys validated**: Anthropic + OpenAI keys both produce non-zero responses
4. **Cohere rerank-v3 API key + free-tier quota** — verify 1000-call quota sufficient for eval × ablation × counterfactual
5. **RAGAS langchain dep tree compatibility** — `uv add ragas` + import test + check langchain-core version conflicts with langgraph
6. **OpenAI prompt-cache + token budget alarms** — set hard usage cap ($100/month) via dashboard
7. **Anthropic prompt-caching beta header path** — EU region account may need explicit opt-in; test cache_read_input_tokens > 0 on repeat
8. **Fly.io paid plan + region (ams) + memory tier** — verify free tier insufficient; commit to ~$5-10/month
9. **v1 cost/latency baseline run** (N2) — 30 scenarios with per-node token counts, USD at DeepSeek list, p50/p95
10. **DSPy 2.5+ version pin** in pyproject.toml + signature compatibility check with existing prompts
11. **GitHub Pages + custom domain DNS prep** for F8 — start propagation now since may take 24-48h

The first 3 are blocking; 4-8 will silently fail in week 4-7 without day-1 verification; 9 is the load-bearing baseline; 10-11 are cheap prep.

## Sprint plan (revised)

| Sprint | Weeks | Work | Hours wall-clock |
|---|---|---|---|
| Sprint | Weeks | Work | Hours wall-clock |
|---|---|---|---|
| 1 | 1-2 | **Day-1 11-item checklist (3h)** + F7 deploy (15h) + F1 structured outputs (4h) + A1 retrieval ablation (4h) + A2 reranker (4h) + **N2 v1 baseline (2h)** | **32h** (v4.1 corrected; 16h/week) |
| 2 | 3-4 | F2 RAGAS (8h) + F3 multi-judge (6h) + F4 algo citation (4h) + F6 trajectory (6h) + **A5 3-tier quick-eval (3h)** + F8 mkdocs (4h) | **31h** (15.5h/week) |
| 3 | 5-6 | Frontier #3 Self-Refine (10-12h) + A3 semantic cache (8h) + **A7 trace replay scaffold (6-8h)** | 24-28h (12-14h/week) |
| 4 | 7-9 | Frontier #1 DSPy **on `synthesize` node only first** per P13 (30h budgeted, **week-9 day-2 gate**, P1-P4 locked) | 30h (10h/week, 3 weeks) |
| 5 | 10-11 | Frontier #4 Multi-LLM MoE (with vendor outage fallback) + A4 failure case study (from trace replay data) | 22h (11h/week) |
| 6 | 12-13 | Frontier #7 Counterfactual (R3 non-protagonist swap, P10-P11 wrappers + doc IDs) | **12-18h** (v4.1 corrected) |
| 7 | 14 | Signature blog + README final + demo video + O1/O2/O3 paper citations | 13h |
| Buffer | 15-16 | Optional PAIR capped OR catch-up | 10h |

**Total**: 174-184h wall-clock / 139-147h with Codex (v4.1 corrected upward from 177/142). Expect to drop PAIR + 1-2 items from next-to-drop list in buffer.

## Honesty calibration policy (v4.1)

(v3 + v4 items retained; v4.1 new additions marked.)

1. No projected numbers in README header; all cells "TBD - see ablation"
2. Every frontier technique ships with "with vs without" ablation table
3. State attacker model strength explicitly if PAIR ships
4. State cost/quality trade-off for MoE routing
5. **(v4.1 NEW per r2 D)** **If A7 trace replay is dropped due to buffer overrun, then no DSPy ablation claim ships** — the per-category regression check is the only thing that makes DSPy numbers honest, and without it the headline number can hide a regression. A7 is not optional polish; it gates DSPy publishing.
6. **(v4.1 NEW per P15)** DSPy ablation doc reports BOTH 2-judge (training metric, no DeepSeek) AND 3-judge (comparison metric used elsewhere) numbers, with one paragraph explaining the dual regime.
7. Honest README sentence: link to `docs/v4-frontier-plan.md` for the active plan.

## Risk register (v4 with Codex additions)

(All v3 risks retained; new from Codex review marked **NEW**.)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Eval-loop slowness compounds | H | H | A5 3-tier quick-eval. Cache aggressively. Full eval only at sprint boundaries. |
| **(NEW) DSPy contamination via same-model judge** | H | **CRITICAL** | N1 locks: DSPy metric excludes DeepSeek during compilation. Multi-judge median = Haiku + GPT-4o-mini only. |
| **(NEW) Anthropic cache invalidation during DSPy** | H | M | P4: signature design freezes cache prefix, varies suffix. Budget $50-150 for compilation. |
| **(NEW) No v1 baseline → unfalsifiable claims** | M | H | N2 locks: 2h baseline run on Sprint 1 day-1. |
| **(NEW) Counterfactual entity-swap collides w/ injection guard** | M | M | R3: restrict to non-protagonist entities. Sarah stays Sarah; EY → PwC. |
| **(NEW) Vendor outage with MoE pin** | L | H | P8: synthesize falls back to DeepSeek if Anthropic outage. +4h impl. |
| DSPy 30h exceeded | M | M | P1: week-9 day-2 gate (not week-10); switch to manual + ablation table fallback (10h scope) |
| DeepSeek 1M unstable | M | L | Day-1 verified; fallback 200K |
| Multi-LLM MoE needs multi-vendor keys | M | M | Day-1 verified all 3 keys |
| Track A collision | H | M | +1 week per collision; do not cut scope mid-stream |
| Burnout | M | H | 2-week buffer (Sprint 15-16). Hard cap 8h/week. |

## Locked decisions (do not revisit)

Same as v3, plus:

- **N1**: DSPy training metric excludes DeepSeek as judge (Sprint 4 lock)
- **N2**: v1 cost/latency baseline run on Sprint 1 day-1 (2h, non-negotiable)
- **R1**: Add A7 trace replay regression harness; keep A4 (case study)
- **R2** (v4.1 corrected): Cite Self-Refine (Madaan 2023), prose-only critique. CRITIC tool-calling variant deferred v1.5 (+6-10h graph restructure).
- **R3**: Counterfactual entity-swap = non-protagonist entities only
- **R4**: Quick-eval at 3 tiers
- **R5**: Sprint 1 day-1 = 11 verification items
- **P1-P15** (P12-P15 v4.1 new): process improvements locked, no time cost

## What to do next

Sprint 1 day-1 — the 11-item verification checklist + v1 baseline run + Fly.io deploy + F1 structured outputs.

**Specifically:**

1. Run the 3-hour day-1 verification checklist
2. Execute 2-hour v1 baseline (N2): full 30-scenario eval with per-node token logging, USD/query, p50/p95
3. Deploy v1 to Fly.io (F7 ~5h)
4. Rewrite judge.py with `messages.parse` + Pydantic `JudgeScore` (F1 ~4h)
5. A1 retrieval ablation (~4h) + A2 reranker (~4h)

Sprint 1 target: **32h over 2 weeks at 16h/week** (v4.1 corrected; exceeds 8h/week burnout cap — accept higher pace for Sprints 1-2 only, taper from Sprint 3).
