# Codex review prompt

> Copy the block below verbatim into Codex CLI from the repo root.
> Codex will read the listed files and produce an orthogonal second-opinion review.

---

You are an independent senior LLM systems engineer (10+ years, OpenAI ecosystem deep, has shipped 3+ production RAG/agent systems) doing a SECOND-OPINION review of a portfolio project plan. An Anthropic Opus review already happened and was accepted in full. Your job is to find what THAT review MISSED — not to repeat it. Be ruthless. No sycophancy.

## Read these files in order before critiquing

1. `docs/v3-frontier-plan.md` — the current active plan you are reviewing
2. `docs/v2-plan-opus-review.md` — what Opus already said and what was already accepted
3. `docs/v2-frontier-plan.md` — the pre-cut v2 plan, for context on what was removed
4. `README.md` — what v1 has actually shipped
5. `docs/STATUS.md` — current numbers and known gaps
6. `src/eval/judge.py` — current LLM-judge impl that v3 plans to rewrite
7. `src/agent/graph.py` — current LangGraph topology that v3 plans to extend
8. `src/eval/retrieval_sanity.py` — current retrieval scorer that v3 plans to ablate

## Context (do not skip)

**Author**: Fei, 7+ years ML eng (data infra + production ML), now job-hunting NL AI Engineer / GenAI Engineer / ML Engineer roles. NL hire peak ~Sept 2026. ~16 weeks from now (May 2026).

**Working mode**: solo + Claude Code (Opus 4.7) + Codex CLI pair-programming. No external coordination (no human raters, no design partners, no meetup talks). 80-100h wall-clock with Codex 0.8x multiplier. This is his LAST portfolio project — must be flagship.

**v1 baseline (shipped, 24 commits)**: cross-source enterprise knowledge agent over 6 SaaS surfaces, LangGraph 5-node ReAct + 6 tools + cross-source RBAC + 30 self-authored eval scenarios + 10 adversarial (all blocked) + RAGAS-less LLM-judge + BGE-M3/Qdrant. Numbers: answer 0.71, governance 0.97, MS Marco MRR@10 0.54, HotpotQA F1 0.29.

**v3 plan** (post-Opus-review): cut to 4 frontier techniques (Self-Refine, DSPy, Multi-LLM MoE, Counterfactual robustness) + 6 production-eng additions (retrieval ablation, reranker, semantic cache + cost leaderboard, failure case study, quick-eval subset, honest ablations). 95-100h with Codex.

**Locked decisions (don't revisit)**: single repo, DeepSeek as primary LLM, Apache 2.0, Fly.io deploy, solo execution, 14+2 week timeline.

## What I want from you (DIFFERENT from Opus's angle)

Opus focused on: technique citation faithfulness, time estimates, Christmas-tree syndrome, NL hire positioning, eval-loop slowness compounding, projected numbers honesty. Don't redo these.

I want you to surface what Opus MISSED:

### 1. OpenAI-ecosystem perspectives Opus likely undervalued

Anthropic-trained models tend to underweight techniques pioneered by OpenAI / Google / Meta. Specifically:
- Did Opus undervalue any technique that an OpenAI-trained engineer would weight higher?
- Are there 2024-2025 papers / frameworks from OpenAI / Google / Meta / Mistral that solve the same problems better than what v3 picked?
- RouteLLM (Frontier #4) is OpenAI-adjacent — is the v3 routing design right, or are there better alternatives (e.g., RouterDC, Hybrid LLM, FrugalGPT updates)?
- GPTCache is the default semantic cache — are there 2025 alternatives (e.g., Anthropic's prompt caching beta) that would be cheaper/better for this use case?

### 2. Concrete implementation hazards per frontier technique

For each of the 4 frontier techniques, list the SPECIFIC failure modes you've seen in production:

- **Self-Refine on a 5-node LangGraph with tool history**: what breaks? (e.g., critique node hallucinating fake gaps, infinite revision spiral, critique cost spiral)
- **DSPy + LLM-judged metric on 30-scenario training set**: where does this actually go wrong? Reward hacking? Overfitting to the judge?
- **Multi-LLM MoE with 5 nodes + 3 vendors**: latency variance, vendor outage handling, prompt cache invalidation across vendors, OpenAI structured-output vs Anthropic JSON parsing gotchas
- **Counterfactual robustness via entity swap on Sarah → Alice**: this breaks 9 injection patterns from W1. Has v3 thought about regenerating ground truth per perturbation?

### 3. Where Opus's review was WRONG

Be specific. Examples to consider:
- Was the PRM critique correct? (Lightman 2023 is trained-verifier, but "process supervision" is a broader concept — is there a defensible LLM-judge-based version?)
- Was the Constitutional cut correct? (CAI training requires RLAIF, but constitution-in-prompt is a real technique used in production — see Anthropic's own product features)
- Was 30h for DSPy actually pessimistic? (DSPy 2.5+ has simpler optimizers, BootstrapFewShot can converge in 4-8h on small training sets)
- Was the NIAH cut correct given DeepSeek 1M is a load-bearing claim for the project?

### 4. v3 Sprint 1 day-1 critique

v3 says day-1 verify:
- DeepSeek 1M context coherence past 200K
- Langfuse Cloud public dashboard
- Multi-vendor LLM keys (OpenAI + Anthropic)

What's missing from that checklist? What will silently fail in week 2 because day-1 missed it?

### 5. The single highest-leverage item that's still NOT in v3

What would you add as a 6th production-eng item (or 5th frontier technique) if you had one slot, that Opus didn't think of? Specific paper + estimated effort + why it dominates one of v3's current items.

### 6. Honest disagreement with reviewer biases

Opus may have been biased toward:
- Anthropic's product framing (constitutional AI as inference-time)
- Recency-biased toward 2023-2024 papers (Lightman, Madaan, Ong)
- Under-weighting newer 2025 techniques

What 2025-2026 technique / paper that you would prioritize did neither Opus nor v3 mention?

## Output structure

Return as plain text/markdown:

### A. Verdict (one paragraph)
Same scale as Opus: ship-as-is / iterate / fundamentally rethink. One sentence why.

### B. Orthogonal blind spots (what Opus missed)
3-6 specific items. Each with: what's missing, why it matters, what to do.

### C. Implementation hazards per frontier technique
4 subsections (Self-Refine / DSPy / Multi-LLM MoE / Counterfactual). 2-4 specific failure modes per technique with mitigation.

### D. Where Opus was wrong (or pollyanna)
Specific. If Opus was 100% right, say so plainly.

### E. Sprint 1 day-1 critique
What's missing from the dep verification checklist that will silently break later.

### F. The one missing item (the high-leverage thing v3 lacks)
Paper + effort + why it dominates one of v3's current items.

### G. 2025-2026 papers / techniques that NEITHER reviewer mentioned
List 1-3 with one-line justification each.

### H. Final calibration
Would you execute v3 as locked, or modify? If modify: what's the one change you'd insist on?

## Constraints

- Plain text/markdown only. No JSON.
- 1500-2500 words. No filler.
- Cite specific files / line numbers when criticizing v1 code.
- Cite papers as `(FirstAuthor Year)`.
- Where you cite an OpenAI / Google / Meta paper Opus likely missed, mark it `[orthogonal]`.
- No agreement with Opus just because Opus is "senior". Disagree where warranted.
- No agreement with v3 plan just because Fei locked it. Disagree where warranted.

---

End of prompt. Run from repo root.
