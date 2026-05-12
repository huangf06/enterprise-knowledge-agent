# Independent Codex review of v3 frontier plan

> Critique by Codex (OpenAI ecosystem) on 2026-05-12. Orthogonal second-opinion after Opus v2 review was already accepted.
> Verdict triggered v4 plan at `docs/v4-frontier-plan.md`.

## A. Verdict

Iterate, one targeted change. v3 is roughly the right plan but it has a single load-bearing technical contamination Opus did not name: the LLM-judge in `src/eval/judge.py:14,79` uses the same client as the agent, so DSPy's optimizer (Sprint 4) would maximize a metric produced by its own model class. Without surgical fixes around the metric pipeline this becomes a self-training loop dressed as ablation. Other items below are smaller. Ship after fixing the metric contamination and adding a baseline cost run.

## B. Orthogonal blind spots Opus missed

1. **The judge-vs-agent same-model contamination is the real DSPy hazard.** `src/eval/judge.py:14` imports `messages_create` from the same anthropic client the agent uses, and `judge.py:79` calls it with default model. DSPy on this metric will reward-hack the model's own aesthetics (verbosity, citation pattern parroting, `expected_topics` keyword echoing — note that `judge.py:23` literally hands the judge `expected_topics` and `expected_action`, both of which the agent's compiled prompt could learn to mention by name). v3 schedules F3 (multi-judge consensus) in Sprint 2 and DSPy in Sprint 4. That ordering is fine but v3 never states DSPy must train against the multi-judge median, with the agent's own model excluded from the judge pool. Without that clause, the DSPy ablation table is contaminated regardless of how honest the numbers look. **Mitigation**: in Sprint 4 lock DSPy metric = GPT-4o-mini + Haiku consensus only; DeepSeek-as-judge dropped during compilation.

2. **v3 has no v1 cost/latency baseline.** A3 promises a cost/latency leaderboard but the README leaderboard at line 17 already shows "Avg latency per query 169s" without dollars per query, p50/p95, or token breakdown. Before MoE routing can claim a Pareto win, v1's current cost must be measured. Add 2h to Sprint 1: full eval run with token counts logged per node, dollars per query at DeepSeek list price. Without this baseline the MoE cost-saving claim is unfalsifiable.

3. **Anthropic prompt-cache invalidation under DSPy compilation** [orthogonal]. DSPy will mutate the system prompt across iterations. Anthropic prompt caching (and OpenAI's auto-cache since Oct 2024) keys on exact prefix match ≥1024 tokens. Every BootstrapFewShot iteration that touches the prefix → 100% cache miss → 10x cost during optimization. Anthropic's own docs: cache breakpoints must be stable across calls. Plan needs an explicit "freeze cache prefix, vary suffix" signature design or DSPy compilation costs $50-150 not the implied "small."

4. **CRITIC dominates Self-Refine for tool-augmented agents.** Madaan 2023 Self-Refine was designed for monolithic generation tasks. For a 5-node tool-using ReAct graph, the better citation is CRITIC (Gou 2024) [orthogonal] — same critique structure, but the critique step is allowed to call tools to verify claims. That maps to the 6-tool catalog this project already has. Opus didn't suggest this swap. Effort: identical (10-12h). Result: the critique node can call `slack_query` or `gdocs_search` to verify a claim before signaling revise, which is a much stronger artifact than "critique on prose only."

5. **Counterfactual eval has no ground-truth regeneration story.** The plan says entity-swap Sarah → Alice. The 30 scenarios are seeded against Sarah Chen's synthetic data (`docs/STATUS.md:51-52` confirms 30-user seed, Sarah is the canonical user). Swapping the name in the query but not in the synthetic data means the agent retrieves nothing for Alice and degrades 100% trivially. Real options: (a) regenerate the synthetic data with Alice's life mirroring Sarah's, then regenerate gold answers per scenario (heavy), or (b) constrain entity-swap to non-protagonist entities only (e.g., the customer "EY contract" → "PwC contract", which doesn't require gold regeneration since the answer template stays the same). v3 must commit to (b) explicitly or budget the regeneration cost.

6. **Counterfactual entity swap collides with W1 injection patterns.** The injection guard at `src/governance/injection_guard.py` was tuned on Sarah-specific patterns per W1 design. Swapping protagonist names re-tests injection on names the guard wasn't trained on; the 10/10 adversarial result becomes incomparable. Either restrict perturbation to query-only entities (per item 5b) or accept governance regression as part of the ablation.

## C. Implementation hazards per frontier technique

### Self-Refine on the 5-node LangGraph (`src/agent/graph.py`)

- **Critique node hallucinating fake gaps.** `expected_topics` is in the eval scenario, not in AgentState at runtime. The critique node has nothing to compare against except the agent's own trajectory. It will invent gaps because LLMs default to "be helpful, find improvement." Mitigation: structure critique as a closed checklist of 4 questions (citation present? action item present? cross-source synthesis present? governance constraint respected?). Refuse open-ended "is there anything else."
- **Critique cost spiral.** Current latency 169s. Two critique rounds + potential re-synthesize = up to 4x agent inference per query. Eval pass goes 100min → 400min. This is the eval-loop slowness Opus flagged but Self-Refine specifically multiplies it most.
- **Tool-history bleeding into critique.** `graph.py:36-40` keeps state across nodes. The critique node will read `tool_execute` results and critique the tools, not the answer. Lock the critique signature to `(question, final_answer)` only; explicitly drop tool history from its context.
- **No real critic signal.** Madaan's original work showed gains on tasks where the model could verify (math, code). On open-ended RAG synthesis there is no verification signal. Honest target 3-8% on action_recommend (plan acknowledges 0.46 → 0.50-0.55) is right; consider it might be 0%.

### DSPy compiled prompts on 30 scenarios

- **30 is below DSPy's minimum viable.** BootstrapFewShot defaults assume 50+ examples; MIPROv2 wants 100+. Train/val split of 30 → 20/10 means val signal is dominated by noise. Mitigation: optimize ONE node at a time (synthesize first), not a joint Module across 5 nodes. Joint optimization on 30 examples is the failure mode.
- **Reward hacking against `expected_topics` keyword leak.** `judge.py:23` includes `expected_topics` in the judge prompt. DSPy will learn that mentioning the literal token in `expected_topics` raises score. The judge prompt must redact `expected_topics` from the judge's view OR `expected_topics` must be removed from the agent's optimizer signature.
- **Compilation churn against Anthropic cache.** Per blind spot 3.
- **MIPROv2 may be cheaper than budgeted 30h.** DSPy 2.5+ defaults to MIPROv2; on 30 examples it converges in 6-15h. Opus said 30-50h pessimistic. Realistic: 15-25h if scoped to one node. 30h is fine as budget but week-10 fallback at "still not converging" is too late — gate at week 9 day 2.

### Multi-LLM MoE with 3 vendors

- **Cost-per-query has 3 incompatible token meterings.** OpenAI bills BPE input/output, Anthropic bills char-based, DeepSeek bills its own. The Pareto chart must be in USD only, never tokens. Make this explicit.
- **Latency variance dominates p95.** If plan node (Sonnet) p95 = 12s, tool_select (Haiku) p95 = 3s, critique (GPT-4o-mini) p95 = 4s, your chain p95 is the sum, not the max. v1 already at 169s; expect MoE chain p95 → 200-250s. Report this honestly; "MoE is faster" is not the claim.
- **Vendor outage.** No vendor failover in v3. Anthropic had a 6-hour outage in Mar 2026. With plan/synthesize pinned to Sonnet, an Anthropic outage = full agent down. Decide: do you ship a fallback (e.g., synthesize falls back to DeepSeek)? If yes, that's another 4h. If no, document that single-vendor outage = full outage in failure mode.
- **Structured-output divergence.** OpenAI gpt-4o-mini `parse` API uses JSON Schema strict mode. Anthropic uses tool-use for structured. DeepSeek's Anthropic-compatible endpoint may not honor every Anthropic field. The critique node returning Pydantic JudgeScore from GPT-4o-mini vs JudgeScore from Haiku will hit different parser paths. F1 (structured output) was scoped only for the judge; extend to the critique node or accept regressions.

### Counterfactual entity swap

- Ground-truth regeneration: see blind spot 5.
- Injection guard collision: see blind spot 6.
- **Noise injection needs retrieval hook.** `src/retrieval/` doesn't currently expose a "inject N distractor docs and re-rank" entry point. Wrapping it requires either patching the retriever (intrusive) or post-hoc append to the LLM context. The latter is what most papers do; budget 2h for the wrapper, not "embedded in 12-15h."
- **Doc-deletion needs ground-truth doc IDs.** `data/eval/scenarios.json` tracks `expected_sources` at the source level (slack/jira/etc.), not at the doc-id level. To delete the supporting doc you'd need to add ground-truth doc IDs per scenario. That's 2-3h of scenario authoring not budgeted.

## D. Where Opus was wrong or partial

- **PRM cut: correct decision, missed rescue.** Opus said "real PRM = trained verifier." That is true for Lightman 2023. But ProcessBench (Zheng 2024) [orthogonal] and Generative Reward Models (Mahan 2024) frame LLM-as-judge process supervision honestly. v3 could have kept "per-node LLM scoring" and cited Zheng. Net effect: small, because Langfuse per-node traces already cover the visible artifact. Don't reintroduce.
- **Constitutional cut: correct decision, wrong reason.** Opus said CAI is RLAIF. True. But OpenAI's Deliberative Alignment (Guan 2024) [orthogonal] is literally an inference-time policy spec — same shape as putting a `constitution.md` in the prompt. The technique is real and citable. v3's cut decision is right because RBAC already passes 10/10, not because the technique is fake. Frame it that way if asked in interview: "I cut it because the marginal lift was zero on hard governance metrics, not because the technique is unsound."
- **DSPy 30-50h: pessimistic.** Per hazard analysis above, 15-25h is realistic for single-node optimization. Opus inflated. v3's 30h budget is fine as a ceiling.
- **NIAH cut: 100% correct.** The agent is RAG. 1M context is marketing not engineering for this architecture. Keep cut.
- **PAIR demotion: correct.** Attacker model strength is the entire variable. Opus right.
- **Eval-loop compounding: 100% correct.** A5 quick-eval at 5 scenarios is right; consider 3 scenarios for "smoke" tier and 10 for "fast" tier — current single quick-eval is binary.

## E. Sprint 1 day-1 critique

v3 lists 3 verifications. Missing:

- Cohere rerank-v3 API key + free-tier quota. A2 needs this. Cohere free tier is 1000 calls/month; full eval × ablation × counterfactual will burn it.
- RAGAS langchain dep tree compatibility. RAGAS pins specific langchain versions that conflict with langgraph. This has eaten weekends in 2024-2025. Resolve before Sprint 2.
- OpenAI prompt-cache enabled + token budget alarms. DSPy compilation can burn $100 in an afternoon. Hard cap via OpenAI usage limits before Sprint 4.
- Anthropic prompt-caching beta header path. EU region accounts sometimes need explicit opt-in.
- Fly.io paid plan + region + memory tier. Free tier won't run BGE-M3 + Qdrant + Postgres + API. Verify before F7 deploys.
- v1 cost/latency baseline run. 2h. Without this, all MoE / cache / DSPy claims are uncalibrated.
- DSPy 2.5+ version + signature compatibility. Pin in pyproject before Sprint 4.
- GitHub Pages + custom domain DNS for F8 mkdocs (4h work that silently slips to 8h on DNS propagation).

The first three will silently fail in week 4-7. Pay 1-2 extra hours day-1, save 5+ hours later.

## F. The one missing item

**Trace replay regression harness.** Effort: 6-8h. Why it dominates:

A4 (failure case study) is a one-shot writeup. Trace replay is continuous: capture real traces from F7 deployment in Sprint 1, serialize them with their tool outputs and gold answers, replay against every new graph version in CI. This catches the case where DSPy improves overall `answer_correctness` by 0.05 but regresses one category (e.g., `conflict_resolution` dropped from 0.56 to 0.40, which is invisible in the headline metric). It's also what Anthropic / OpenAI / xAI all do internally and is the highest-signal "production AI eng" artifact. Paper anchor: PromptPex (Microsoft 2024) [orthogonal] or just "trace replay" as a generic pattern; no citation needed if framed as engineering practice.

Recommendation: swap A4 for trace replay. Or do both, since trace replay generates the raw material for A4 anyway. If forced to one: trace replay. It compounds across the 4 frontier integrations.

## G. 2025-2026 papers / techniques neither reviewer mentioned

- **TextGrad** (Yuksekgonul Sept 2024 Stanford) [orthogonal] — gradient-style prompt optimization, competes with DSPy on the same problem with simpler integration. Worth a one-paragraph compare-and-contrast in the DSPy ablation doc.
- **Deliberative Alignment** (Guan Dec 2024 OpenAI) [orthogonal] — inference-time policy specification. Cite this in the governance design doc to replace the Constitutional cut framing.
- **BFCL v3** (Berkeley 2025) — tool-call eval benchmark. Could replace HotpotQA as a more agent-relevant retrieval-component sanity check. F6 trajectory eval should at least cross-reference BFCL's metric definitions.

## H. Final calibration

Execute v3 with two non-negotiable modifications:

1. **Hold the agent's model class out of the DSPy training metric.** DSPy compilation in Sprint 4 must use a multi-judge median excluding DeepSeek (the agent's primary). State this explicitly in the v3 plan and in the DSPy ablation doc.
2. **Add a 2h v1 cost/latency baseline run to Sprint 1 day-1 deps verification.** Token counts per node, dollars per query at list price, p50/p95 latency. Without this, A3 (semantic cache leaderboard) and Frontier #4 (MoE Pareto) are unfalsifiable.

Optional but recommended: swap A4 for the trace replay regression harness (item F) and use replay data to write A4 organically. Optional: cite CRITIC (Gou 2024) instead of Self-Refine if the critique node will use tools; otherwise keep Madaan.

Everything else in v3 ships as-is. Opus's review was 90% right; the contamination point in B1 and the baseline absence in B2 are the two genuine misses.
