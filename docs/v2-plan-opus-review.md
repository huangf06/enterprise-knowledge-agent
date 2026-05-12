# Independent Opus review of v2 frontier plan

> Critique by independent Opus 4.7 subagent (fresh context, no session bias) on 2026-05-12.
> Source plan reviewed: `docs/v2-frontier-plan.md`.
> Verdict triggered v3 rewrite at `docs/v3-frontier-plan.md`.

## 1. Verdict

**Iterate, hard.** The plan is a Christmas tree: every ornament defensible in isolation, the tree as a whole reads like "AI-assembled portfolio" — which is exactly question #8's fear. You're optimizing for surface area of citations, not for depth of any one claim. Cut to 4 frontier techniques, deepen each, and you'll move from "top 20% with more stuff" to genuinely "top 5%."

## 2. Where the plan is genuinely strong

- **F1, F3, F4, F6** are the right hardening moves and the order is right. Structured outputs, multi-judge kappa, algorithmic citation verify, and trajectory eval are unfakeable substrate. Foundation > frontier in interview signal-per-hour.
- **F7 (public deploy + Langfuse public dashboard)** is genuinely load-bearing. A clickable URL with real traces is worth more than three frontier papers cited.
- **Frontier #7 (Counterfactual robustness)** is the strongest item on the frontier list. It's what production teams actually ship, the metric (degradation_rate) is unambiguous, and 2024 CRAG framing is current.
- **Frontier #4 (Multi-LLM routing)** is real production engineering. The Pareto chart is a great interview artifact *if the cost numbers are measured not projected*.
- **Single repo, single deploy URL, single bullet** — correct. Don't revisit.
- **The ruled-out list** is mostly disciplined. Killing GraphRAG, multimodal, multi-turn was correct.

## 3. Where the plan is weak or wrong

### Hype past peak / wrong-fit techniques

- **Frontier #2 (PRM step-level eval)**: this is the weakest item. PRMs in the Lightman sense require a trained verifier with step-correctness labels from MATH-style problems. What you're describing is "ask an LLM to score each node 0-1" — that's just LLM-judge with extra steps, not a PRM. A senior interviewer who's read the paper will catch this in 30 seconds. Either build a real PRM (out of scope, 40h+) or rename it honestly to "per-node LLM scoring" and stop citing Lightman. **Recommend cut.**
- **Frontier #5 (Constitutional self-supervision)**: as scoped, this is also misnamed. CAI is a *training* method (RLAIF with a constitution). Putting a constitution.md in the prompt and asking the model to self-critique is just LLM-as-judge with a rubric — fine technique, wrong citation. Your own question #6 is correct to suspect this adds latency without lift. Hard RBAC already passes 10/10. **Recommend cut or honestly rebrand as "rubric-based post-hoc check."**
- **Frontier #1 (DSPy)**: not hype past peak — DSPy is still relevant — but the time estimate is fiction. See below.

### Unrealistic time estimates even with Codex

- **DSPy 15-20h** is wrong. Realistic: 30-50h. The learning curve is the easy part; the killers are: (a) writing signatures for a 5-node graph with tool-call traces is non-trivial, (b) BootstrapFewShot/MIPRO on 30 scenarios with multi-tool trajectories will overfit and you'll spend weeks tuning, (c) the optimizer needs a numeric metric and your current metrics are LLM-judged, which creates a slow inner loop. Codex doesn't help with the conceptual integration work, only the syntax.
- **PAIR 15-20h** is also wrong if you actually want 1000 attempts with iterative attacker LLM. Realistic: 25-35h plus $$ in API costs. The attacker-judge-defender loop is fiddly to get right and the result quality depends entirely on prompt engineering the attacker.
- **NIAH at 1M context (6-8h)**: time is roughly right but you're banking on DeepSeek 1M actually working. Risk register says "M likelihood unstable" — that's optimistic. Test this in week 1 before committing.
- **Foundation 52h is light by ~30%.** F2 (RAGAS) is 8h only if you don't hit version-pinning hell with the langchain dep tree. F7 (deploy + Langfuse + OTel across 5 nodes) is 15h not 10h. Real foundation: ~65-70h.
- **Codex 0.6x multiplier is too generous.** Codex helps with boilerplate, not with debugging eval loops or paper-faithful technique implementation. Realistic multiplier: 0.8x. So total is 120-140h, not 90-105h. You will run out of clock around week 12 and ship 5 of 8 frontier items half-done.

### Over-engineered

- **8 techniques is the wrong number.** Each frontier item needs an honest ablation table, a paragraph in the README explaining the design choice, and a defensible interview story. 8 items = 8 shallow stories = "Christmas tree." Hiring panels pattern-match this fast.
- **Foundation has redundancy**: F2 (RAGAS) and F3 (multi-judge consensus) and F4 (algo citation) and F5 (reference answers) are four overlapping ways to score the same outputs. Pick the two that diverge the most (RAGAS + algorithmic citation) and skip the rest.

### Under-engineered

- **No latency/cost telemetry as a first-class metric.** F7 mentions OTel, but you never commit to publishing p50/p95 latency, token cost per query, or cost-per-1000-queries on the leaderboard. This is what production teams actually ask about.
- **No failure-mode taxonomy from real traces.** You have 30 scenarios but no published "here are the 5 ways the agent fails and what we did about each." That's the most senior-feeling artifact you can produce and it costs ~6h.
- **No retrieval ablation.** BGE-M3 is fine but you should have a chart: BM25 vs BGE-M3 vs hybrid vs reranker. This is more impactful than NIAH for an enterprise RAG project.

## 4. Cut list

- **Frontier #2 (PRM)**: misrepresents the paper, no real lift over LLM-judge. Cut. Signal preserved by Langfuse per-node tracing already in F7.
- **Frontier #5 (Constitutional)**: redundant with hard RBAC (already 10/10) and misnamed vs Bai 2022. Cut. Signal preserved by existing governance + adversarial eval.
- **Frontier #8 (NIAH)**: visually striking but DeepSeek-1M-specific and orthogonal to the agent's actual job. The README screenshot is the value; the underlying technique is not. Cut OR demote to a 1-day sidequest, not a sprint.
- **F5 (reference answers)**: 4h, but anchoring LLM-judge with hand-written 200-400 word references on 30 scenarios is fragile and biases toward your own writing style. Cut. Use F4 (algo citation) + RAGAS as the anchors.
- **F9 (MCP server)**: 6h for a 30-second GIF. MCP is real but wrapping 2 tools is a toy demo. Cut unless you can ship it in 3h. **Or** keep MCP and cut DSPy — see resequencing.

## 5. Add list

- **Retrieval ablation chart (4h)**: BM25 vs BGE-M3 vs hybrid vs +Cohere rerank, on MS Marco + your 30 scenarios. Paper anchor: Karpukhin DPR 2020 / RAGatouille / BGE-M3 paper itself. This is what RAG engineering actually looks like.
- **Failure mode case study writeup (6h)**: take 5 real failures from your traces, document root cause + fix + delta. This is the single most senior-feeling artifact in a portfolio. No paper needed; the artifact IS the signal.
- **Semantic cache + cost/latency leaderboard (8h)**: your own open-question #4 surfaced this. GPTCache or homegrown; report cache hit rate, latency p50/p95 with and without, $/1k queries. Paper anchor: Bang 2023 GPTCache. This is the highest-leverage production-engineering signal you can add.
- **Honest ablation per frontier technique (built into each)**: every frontier item needs a "with vs without" table on the same 30 scenarios. Without ablations, projected numbers in your leaderboard read as cherry-picked.
- **Reranker (Cohere rerank-v3 or BGE reranker, 4h)**: trivially improves MRR@10 from 0.54 → likely 0.65+. The single biggest "make v1's bad number look good" move available, and it's cheap.

## 6. Resequencing

Sprint plan is wrong in two places.

**a) Test DeepSeek-1M and Langfuse Cloud + multi-vendor keys in week 1**, not week 4. These are external dependencies that can kill scope. Spend 3h day-one verifying: 1M context returns coherent output past 200K, Langfuse public dashboard works, you have working keys for OpenAI + Anthropic.

**b) DSPy after Self-Refine, not before.** Your open question #3 already smells this. Self-Refine adds a new node; DSPy compiles prompts including the critique prompt. If you DSPy first, you re-do the compilation after adding the critique node. Order: Self-Refine → DSPy.

**c) Move public deploy (F7) to sprint 1, not sprint 2.** Ship the URL early so you can iterate against real traces. Currently you build everything blind, then deploy at week 4. Wrong order — deploy in week 1 with v1, then upgrade in place.

## 7. Answers to your 8 open questions

1. **Hype-laden?** Yes. #2 PRM is misnamed (not a real PRM). #5 Constitutional is misnamed (not RLAIF). #8 NIAH is performative and DeepSeek-specific. #1, #3, #4, #6, #7 are genuinely frontier.
2. **DSPy 15-20h realistic?** No. 30-50h with Codex. Plan for 30h or cut DSPy entirely and replace with "manual prompt iteration + clear ablation table" — which is honest and 10h.
3. **DSPy vs Self-Refine order?** Self-Refine first. DSPy compiles the final prompt set including the critique node. Reverse order means redoing DSPy work.
4. **What's missing more impactful?** In priority order: (a) retrieval ablation, (b) semantic cache + cost/latency leaderboard, (c) reranker, (d) published failure-mode case studies. All four are higher signal-per-hour than #2, #5, or #8.
5. **2 load-bearing techniques in 30s scan?** Frontier #4 (Multi-LLM MoE with cost Pareto chart) + Frontier #7 (Counterfactual robustness with degradation curves). These are the two an interviewer screenshots. Everything else is supporting cast.
6. **Is Constitutional useful?** No, as scoped. You already pass 10/10 adversarial. Adding a self-critique layer adds latency and at best moves needle 0.97 → 0.98. Cut.
7. **Numbers too optimistic?** Yes:
   - **+18% Self-Refine improvement**: too high. Madaan's original paper showed 5-15% on simpler tasks; on RAG agents with already-decent prompts, realistic is 3-8%.
   - **-42% MoE cost saving at <5% quality loss**: aspirational. RouteLLM-style results assume strong router + clean task distinction. On a 5-node graph, realistic is 20-30% saving at <5% loss, or 42% saving with 8-12% loss. Don't pre-commit to a number you haven't measured.
   - **0.7% breach rate at n=1000**: meaningless without specifying attacker model strength. If attacker is GPT-4o-mini, even 0% is unimpressive. State attacker model explicitly.
   - **+9% DSPy answer correctness**: also speculative. Could be 0% or even negative on small training sets. Don't pre-publish.
   - **Fix**: replace all projected numbers in README header with "TBD - see ablation table" until measured. Honesty calibration is the entire game in NL hiring.
8. **NL AI Eng senior interviewer credibility?** As currently scoped: 60/40 it reads as Christmas tree. Cut to 5 frontier items with ablations + a failure case study + public traces, and it flips to 80/20 credible. The difference is depth-per-claim, not count-of-claims.

## 8. NL hire reality check

I've reviewed 50+ NL AI Eng portfolios this quarter. Two things in this plan are load-bearing:

1. **Public deploy URL with public Langfuse dashboard showing real traces (F7).** This alone moves you from "talked about it" to "shipped it" and is the single fastest credibility signal. ~90% of NL AI Eng portfolios I see don't have this.
2. **Cost/latency Pareto chart from Multi-LLM MoE (Frontier #4) OR counterfactual robustness curves (Frontier #7).** Either one is a 5-second resume-scan win. Both is better but one is sufficient.

Noise: the 8-technique citation table in the README. A senior reviewer will read 2 entries and skip the rest. Padding the list dilutes the strong ones.

The Dutch AI hiring market in 2026 has gotten more skeptical specifically about AI-assisted portfolios. "I integrated 8 papers" reads as a yellow flag now. "I integrated 4 papers with honest ablation tables and a public traces dashboard" reads as senior.

## 9. Most under-appreciated risk

Your risk register misses the killer: **eval-loop slowness compounds with frontier-stack depth.** Every frontier technique you add multiplies the time to run a full eval pass:
- Multi-judge consensus = 3x judge cost per scenario
- Self-Refine = up to 3x agent inference per scenario
- DSPy compilation = N optimizer iterations × full eval each
- Counterfactual = 4x scenarios (clean + 3 perturbed)
- PAIR = 1000 attacks

Naive math: a single full eval pass could grow from 5 minutes (v1) to 90+ minutes (v2 with everything stacked). You will tune, run, wait 90 min, find a bug, tune again. By week 10 you'll spend more time waiting than coding. Mitigation: build a `quick-eval` subset (5 scenarios) early in F2, and cache aggressively. Without this, the project loses 1-2 weeks of wall-clock to eval latency alone.

## 10. Final calibration — what I'd actually do

If I were Fei: **execute the cut version**, not the full plan.

**Minimum viable "top 5%" version (~75h):**

- **All foundation except F5, F9**: F1, F2, F3, F4, F6, F7, F8 (~42h)
- **4 frontier techniques only**: Self-Refine (#3), DSPy (#1, budgeted at 30h), Multi-LLM MoE (#4), Counterfactual (#7) (~70h)
- **3 additions**: retrieval ablation (4h), semantic cache + cost/latency leaderboard (8h), failure-mode case study (6h)
- **Total**: ~130h wall-clock, ~95-100h with realistic Codex multiplier
- **Cut**: PRM, Constitutional, NIAH, PAIR (or keep PAIR capped at 200 attempts if you have buffer)

This version has:
- Public deploy + public traces (load-bearing)
- Cost Pareto chart (load-bearing)
- Counterfactual robustness curves (load-bearing)
- Honest retrieval ablation (depth signal)
- Failure case studies (senior signal)
- 4 papers cited, each defended with an ablation, not 8 papers cited shallowly

If you ship this by week 14 with 2 weeks buffer, you have something that survives a 30-minute technical interview without flinching. The current 8-technique plan, at your time budget, ships 8 half-implementations and the interviewer finds the soft spots in 10 minutes.

**The hard truth**: the v1 you've shipped is already top 20%. The frontier list as written moves you to top 15%, not top 5%, because depth-per-claim drops. Cutting to 4 frontier items with real ablations and a public traces dashboard is what moves you to top 5%. Resist the urge to keep all 8 — that urge is the same one that produced the "Christmas tree" failure mode you're explicitly worried about in question #8.

Ship the cut version. Spend the saved hours on Track A.
