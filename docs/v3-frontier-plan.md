# v3 Frontier Enhancement Plan

> Status: **active**. Supersedes `v2-frontier-plan.md`. Based on independent Opus review (`v2-plan-opus-review.md`).
> Locked 2026-05-12.

## Why v3

v2 was 8 frontier techniques + 9 foundation items. Independent Opus review verdict: **Christmas tree syndrome; every ornament defensible, the tree as a whole reads "AI-assembled portfolio"**. Cut to 4 frontier + add 3 production-engineering items + fix sequencing.

This plan implements the reviewer's "minimum viable top 5%" recommendation in full.

## Author + role + constraint context (unchanged)

- **Author**: Fei, ML Engineer (7+ years data infrastructure, bridging pipelines to production ML).
- **Goal**: land NL AI Engineer / GenAI Engineer / ML Engineer role. Hire peak ~Sept 2026 (~16 weeks).
- **Working mode**: solo. No external coordination.
- **Real time budget**: 95-100h wall-clock.
- **This is the LAST portfolio project.** All future work goes in this repo.

## v1 baseline state (unchanged, locked at commit b38a31d)

24 commits, 66/66 tests. Real numbers committed:
- answer_correctness 0.71 / completeness 0.75 / tool_selection 0.96 / governance 0.97 / action_recommend 0.46
- HotpotQA F1 0.077 → 0.29 (llm-answer mode)
- MS Marco MRR@10 0.54
- Adversarial 10/10 blocked

## What changed from v2 (delta only)

### Cut (from v2)

| Item | v2 plan | v3 status | Reason |
|---|---|---|---|
| Frontier #2 PRM step-level eval | 8-10h | **CUT** | Misnamed vs Lightman 2023 (real PRM = trained verifier, not LLM-judge). Per-node tracing already covered by Langfuse in F7. |
| Frontier #5 Constitutional self-supervision | 8-10h | **CUT** | Misnamed vs Bai 2022 (CAI = RLAIF training, not inference-time critique). Hard RBAC already 10/10. |
| Frontier #8 Long-context NIAH | 6-8h | **CUT** | DeepSeek-1M-specific, orthogonal to agent's job. Visual signal only. |
| F5 Reference answers for 30 scenarios | 4h | **CUT** | Anchoring LLM-judge with hand-written prose biases toward author style. Use RAGAS + algo citation as anchors. |
| F9 MCP server wrappers | 6h | **CUT** | 2-tool wrapper = toy demo. Re-evaluate post-launch if time. |
| Frontier #6 PAIR (full 1000 attempts) | 15-20h | **DEMOTED** | Cap at 200 attempts (~10h) if buffer remains, else skip. State attacker model strength explicitly. |

### Add (new in v3)

| Item | Hours | Source | Reason |
|---|---|---|---|
| **A1 Retrieval ablation chart** | 4h | Reviewer §5 add list | BM25 vs BGE-M3 vs hybrid vs +reranker on MS Marco + own 30 scenarios. Table-stakes for RAG project; missing was露怯. |
| **A2 Cohere/BGE reranker** | 4h | Reviewer §5 | Cheapest "fix v1's bad number"; MS Marco 0.54 → likely 0.65+. |
| **A3 Semantic cache + cost/latency leaderboard** | 8h | Reviewer §5 | GPTCache or homegrown. p50/p95 latency + $/1k queries on README. Highest production-eng signal. |
| **A4 Failure mode case study** | 6h | Reviewer §5 | 5 real failure traces, root cause + fix + delta. Most senior-feeling artifact, no paper needed. |
| **A5 quick-eval subset (5 scenarios)** | 2h | Reviewer §9 (under-appreciated risk) | Mitigates eval-loop slowness compounding. Built early in Sprint 2. |
| **A6 Honest ablation table per frontier technique** | embedded | Reviewer §5 | "With vs without" on same 30 scenarios. No projected numbers in README until measured. |

### Resequence

- **Day 1 of Sprint 1**: 3h dependency verification: DeepSeek 1M context coherence past 200K, Langfuse Cloud public dashboard, multi-vendor LLM keys (OpenAI + Anthropic). If any fail, switch fallback before building.
- **Public deploy F7 → Sprint 1** (was Sprint 2). Deploy v1 immediately, iterate against real traces.
- **Self-Refine BEFORE DSPy** (was DSPy before Self-Refine in v2). DSPy compiles prompts including critique node; reverse order = redo work.

### Calibration changes

- Time estimates recalibrated per reviewer §3. 90-105h → 120-140h wall-clock without cuts.
- After cuts: ~95-100h realistic.
- **All projected numbers in README header replaced with "TBD - see ablation table"** until measured. Honesty calibration is the game.

## v3 scope: what stays

### Foundation layer (~52h, locked)

(Numbering kept consistent with v2 for cross-reference. F5 and F9 from v2 cut.)

- **F1** Structured-output judge: `messages.parse` + Pydantic `JudgeScore` schema (4h). Fixes 25% parse failure rate.
- **F2** RAGAS 4-metric integration: faithfulness, answer_relevancy, context_precision, context_recall (8h). Industry standard.
- **F3** Multi-LLM-judge consensus + inter-judge kappa: DeepSeek + Claude Haiku + GPT-4o-mini median, flag on max spread > 0.3 (6h). Addresses same-model bias.
- **F4** Algorithmic citation groundedness: parse `[source:id]`, verify against synthetic data (4h). Hard metric, FActScore-adjacent.
- **F6** Trajectory eval: tool precision/recall/F1, redundancy, efficiency (6h). LangSmith / Inspect AI inspired.
- **F7** Public deploy + Langfuse public + OpenTelemetry (15h, revised up from 10h per reviewer §3).
- **F8** mkdocs-material documentation site (4h). GitHub Pages auto-deploy.

**Foundation subtotal: ~47h after cuts.**

### Frontier layer (4 techniques only, ~70h)

#### #3 Self-Refine critique loop (10-12h)
- **Paper**: Madaan et al. 2023, "Self-Refine: Iterative Refinement with Self-Feedback"
- **What**: Add `critique` node after `synthesize`. Max 2 critique rounds. Hard cap to prevent infinite loop.
- **Honest target**: 3-8% lift on action_recommend (not 18%). v1 is 0.46 → target 0.50-0.55, not 0.65+.
- **Why first**: fixes biggest v1 weakness (action_recommend); must precede DSPy compilation.

#### #1 DSPy compiled prompts (**30h budgeted, not 15-20h**)
- **Paper**: Khattab et al. 2023 (Stanford)
- **What**: Replace hand-tuned plan / tool_select / reflect / synthesize / critique prompts with DSPy modules. Optimize via BootstrapFewShot or MIPRO on 30 scenarios.
- **Honest target**: 0-9% lift on answer_correctness. Could be negative on small training set; document either way.
- **Risk fallback**: if 30h is exceeded by week 9, switch to "manual prompt iteration + clear ablation table" (10h scope). Document the abandonment honestly.

#### #4 Multi-LLM Mixture-of-Experts routing (10-12h)
- **Paper**: Ong et al. 2024 "RouteLLM"
- **What**: Sonnet 4.6 for plan/synthesize, Haiku 4.5 for tool_select/reflect, GPT-4o-mini for critique. Pareto chart on README.
- **Honest target**: 20-30% cost saving at <5% quality loss, OR 42% cost saving at 8-12% quality loss (don't pre-commit; measure).
- **Load-bearing**: Pareto chart is one of two interview-screenshot moments.

#### #7 Counterfactual robustness eval (12-15h)
- **Paper**: Liu et al. 2024 "Noise Robustness in RAG"; CRAG (Meta 2024)
- **What**: 3 perturbations per scenario: noise injection (5 distractor docs), doc deletion (remove ground-truth), entity swap (Sarah → Alice). degradation_rate = (clean - perturbed) / clean.
- **Load-bearing**: degradation curves are one of two interview-screenshot moments.

#### #6 PAIR adversarial: DEMOTED to optional, capped 200 attempts (~10h if buffer)
- Only if Sprint 7 has slack. Always state attacker model strength.

### Production-engineering additions (~24h)

| | Hours | Note |
|---|---|---|
| A1 Retrieval ablation (BM25 / BGE-M3 / hybrid / +reranker) | 4h | Build on existing MS Marco harness |
| A2 Reranker (Cohere rerank-v3 or BGE reranker) | 4h | Plugs into existing retrieval pipeline |
| A3 Semantic cache + cost/latency leaderboard | 8h | GPTCache or homegrown; p50/p95/$/1k queries |
| A4 Failure mode case study | 6h | 5 real traces + root cause + fix + delta |
| A5 quick-eval subset | 2h | 5-scenario subset, runs in <2 min |
| A6 Honest ablations per frontier | embedded | "with vs without" tables |

### Polish

- **Signature blog** (8h): "Honest evaluation when you built both sides of the eval loop"
- **README final pass + demo video recording** (4h)

## Total v3 budget

| Block | Wall-clock | With Codex 0.8x |
|---|---|---|
| Foundation (F1-F8 except F5/F9) | 47h | 38h |
| Frontier (4 techniques: #1, #3, #4, #7) | 60-70h | 48-56h |
| Production additions (A1-A6) | 24h | 19h |
| Polish (blog + video) | 12h | 10h |
| Optional Frontier #6 PAIR capped | 10h | 8h |
| **TOTAL (without PAIR)** | **143h** | **115h** |
| **TOTAL (with PAIR)** | **153h** | **123h** |

Reviewer estimate "~95-100h with Codex" was after all 6 cuts AND demoting PAIR. Achievable if **F7 deploy + A3 semantic cache + A5 quick-eval do not slip**. Build slip-tolerant.

## Sprint plan (revised per reviewer §6)

| Sprint | Weeks | Work | Hours wall-clock |
|---|---|---|---|
| 1 | 1-2 | **Day-1 deps verification (3h)** + F7 deploy + F1 structured outputs + A1 retrieval ablation + A2 reranker | 22h |
| 2 | 3-4 | F2 RAGAS + F3 multi-judge + F4 algo citation + F6 trajectory + **A5 quick-eval subset** + F8 mkdocs | 30h |
| 3 | 5-6 | Frontier #3 Self-Refine + A3 semantic cache | 20h |
| 4 | 7-9 | Frontier #1 DSPy (30h budgeted; fallback at week 10 if not converging) | 30h |
| 5 | 10-11 | Frontier #4 Multi-LLM MoE + A4 failure case study | 18h |
| 6 | 12-13 | Frontier #7 Counterfactual robustness | 14h |
| 7 | 14 | Signature blog + README final + demo video | 12h |
| Buffer | 15-16 | Optional Frontier #6 PAIR capped (10h) OR catch-up | 10h |

**Total**: 156h wall-clock / 125h with Codex. Targets 14 weeks core + 2 weeks buffer. Slip-tolerant.

## v3 final state (what ships)

### README header
```
# Enterprise Knowledge Agent

A cross-source enterprise AI agent over 6 SaaS surfaces (Slack/Jira/Calendar/
GitHub/GDocs/Email) with honest, production-grade evaluation.

🔗 Live: enterprise-knowledge-agent.fly.dev
📊 Public traces: <Langfuse URL>
📖 Docs: <username>.github.io/eka/
📝 Blog: "Honest evaluation when you built both sides of the loop"

## Four frontier techniques, each with honest ablation

│ Technique                    │ Paper                        │ Ablation table │
├──────────────────────────────┼──────────────────────────────┼────────────────┤
│ Self-Refine critique loop    │ Madaan 2023                  │ docs/abl-#3.md │
│ DSPy compiled prompts        │ Khattab 2023 (Stanford)      │ docs/abl-#1.md │
│ Multi-LLM MoE routing        │ Ong 2024 (RouteLLM)          │ docs/abl-#4.md │
│ Counterfactual robustness    │ Liu 2024, CRAG (Meta 2024)   │ docs/abl-#7.md │

## Production engineering

- Retrieval ablation (BM25 / BGE-M3 / hybrid / +reranker): see docs/retrieval-ablation.md
- Semantic cache + cost/latency leaderboard: p50/p95/$/1k queries on dashboard
- 5 documented failure case studies: see docs/failure-cases.md
- All metrics measured; no projected numbers
```

### Leaderboard (TBD post-measurement)

All cells "TBD - see ablation" until measured. **No pre-committed numbers.**

### Resume bullet
> Built **Enterprise Knowledge Agent** (Apache 2.0, live demo): cross-source AI agent integrating Self-Refine, DSPy-compiled prompts, Multi-LLM MoE routing, and counterfactual robustness eval. Includes retrieval ablation (BM25 vs BGE-M3 vs hybrid + reranker), semantic caching with cost/latency dashboard, and 5 documented failure case studies. Honest ablation table per technique; numbers measured not projected.

## Risk register (v3 with reviewer additions)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **(NEW) Eval-loop slowness compounds**; full eval 5min → 90min by Sprint 5 | **H** | **H** | A5 quick-eval subset (5 scenarios, <2min) built in Sprint 2. Cache aggressively. Use full eval only at sprint boundaries. |
| DSPy 30h budget exceeded | M | M | Week 10 hard checkpoint: if not converging, fallback to "manual + ablation table" (10h scope) |
| DeepSeek 1M context unstable | M | L | Day-1 verified; fallback 200K if needed |
| Multi-LLM MoE needs multi-vendor keys | M | M | Day-1 verified. Minimum: DeepSeek + Claude + OpenAI keys all working |
| Reranker API cost | L | L | BGE reranker is free local; Cohere only if free tier sufficient |
| Track A (job hunt) collision | H | M | +1 week per collision; do not cut scope mid-stream |
| Semantic cache cache-hit rate too low to demo well | M | L | Acceptable; report whatever measured, including "cache hit 8%" if that's reality |
| Burnout | M | H | 2-week buffer (Sprint 15-16). Hard cap 8h/week. |

## Honesty calibration policy (per reviewer §7)

1. **No projected numbers in README header.** All cells "TBD - see ablation".
2. **Every frontier technique ships with a "with vs without" ablation table** in docs/abl-*.md. If with < without, report that honestly.
3. **State attacker model strength** if PAIR is shipped. "0% breach against GPT-4o-mini attacker, N=200" not "0% breach rate".
4. **State cost/quality trade-off** for MoE routing. "30% cost saving at 4% quality loss" not "30% cost saving" alone.
5. **Honest README sentence** at the top: link to `docs/v3-frontier-plan.md` for the plan and `docs/v2-plan-opus-review.md` for the independent review that drove this revision.

## Locked decisions (do not revisit)

- Single repo, no PyPI split
- DeepSeek as primary LLM (MoE adds Claude + OpenAI for routing only)
- Apache 2.0
- Fly.io as deploy target
- Solo, no external coordination
- 14-week core + 2-week buffer, targeting Sept 2026
- All projected numbers replaced with measured (TBD until then)
- Reviewer's cut list accepted in full: #2 PRM, #5 Constitutional, #8 NIAH, F5 reference answers, F9 MCP all cut
- Reviewer's add list accepted: A1 retrieval ablation, A2 reranker, A3 semantic cache, A4 failure case study, A5 quick-eval, A6 ablations
- DSPy budgeted 30h with week-10 fallback gate
- PAIR demoted to optional buffer-only, capped 200 attempts

## What to do next

1. Day 1 of Sprint 1: dependency verification (3h)
2. F7 public deploy with v1 unchanged (~5h)
3. F1 structured-output judge rewrite (~4h)
4. A1 retrieval ablation chart (~4h) + A2 reranker (~4h)

Total Sprint 1 = 22h, target 2 weeks at 11h/week (push pace).
