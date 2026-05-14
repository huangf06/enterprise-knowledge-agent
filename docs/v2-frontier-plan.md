# v2 Frontier Enhancement Plan

> Status: draft, pending Opus review. Locked 2026-05-12.

## Author + role + constraint context

- **Author**: Fei, ML Engineer (7+ years data infrastructure, bridging pipelines to production ML).
- **Goal**: land NL AI Engineer / GenAI Engineer / ML Engineer role. NL hire peak season starts ~September 2026 (~16 weeks from now).
- **Working mode**: solo developer. No external coordination.
- **Time budget**: 80-100h wall-clock over 12-16 weeks. Track A (job hunt) takes 60% of time; this project is Track B (P1).
- **Decision**: this is the LAST portfolio project. No new ones after. All future signature work goes into this repo.

## v1 baseline state (already shipped)

24 commits on `main`. 66/66 tests green. Components:

- 6 tools (slack/jira/calendar/github/gdocs/email) with shared `Tool(args, ctx)` contract
- LangGraph 5-node ReAct agent (`src/agent/`)
- FastAPI + SSE `/query` endpoint
- Gradio reveal-panel UI (`src/ui/app.py`)
- Anthropic SDK client wired to DeepSeek's Anthropic-compatible endpoint
- BGE-M3 + Qdrant retrieval
- Cross-source RBAC + PII redact + audit + GDPR stub + injection guard
- 30 self-authored cross-source scenarios + 10 adversarial scenarios + 5 HR Helpdesk Demo 2 scenarios
- LLM-as-judge harness + cumulative rejudge for parse errors
- HotpotQA + MS Marco loaders + naive scorer + llm-answer scorer
- Docker compose + Fly.io / HF Space configs + 3 CI workflows
- 10+ docs: architecture, governance design, failure modes, eval methodology, deploy, demo script, w1-w5 reports, case study, STATUS

**v1 real numbers (committed)**:
- Self-authored 30-scenario eval: answer_correctness 0.71, completeness 0.75, tool_selection 0.96, governance 0.97, action_recommend 0.46
- HotpotQA F1: 0.077 (naive span) -> 0.29 (llm-answer mode)
- MS Marco MRR@10: 0.54
- Adversarial: 10/10 blocked (after single-tenant prompt fence fix)

**v1 honest assessment**: "良好执行" (solid execution), not "signature". Sits at top 20% of NL AI Eng portfolio projects, not top 5%.

## v2 framing

**This is a FLAGSHIP project demonstrating the upper limit of what LLM + RAG technology can achieve in 2026.**

Single repo, single deploy URL, single resume bullet. Two equally-weighted contributions in one project:

1. **The agent** (`src/agent` + `src/tools` + `src/governance`): a reference implementation.
2. **The eval framework + frontier integrations** (`src/eval`): showcase of 8 frontier techniques each tied to a recognized 2023-2025 paper, each producing a measurable result.

README markets BOTH contributions. No second repo, no second project.

## What's explicitly ruled out (and why)

| Ruled out | Why |
|---|---|
| Human rater Cohen's kappa study (3 raters x 10 scenarios) | Requires coordinating 3 people; replace with inter-LLM-judge kappa using 3 different vendors |
| NL contact dogfood (1-2 alpha users) | Requires reaching out, scheduling, follow-up - not solo |
| AI Engineer Amsterdam meetup talk | Requires proposal acceptance + speaking - external timeline |
| arXiv preprint (8-12 page tech report) | Writing + revision overhead disproportionate to portfolio value |
| Splitting into 2 PyPI packages | Maintenance cost 2x; one repo with subpackage import works |
| LangChain adapter / OpenAI function schema export | Same-as-everyone, doesn't show frontier |
| AWS deploy | Fly.io covers public deploy signal; AWS is v1.5 |
| Multi-turn conversation + memory | Out of scope; v1 is single-turn intentionally |
| Token-level Anthropic Citations API | Would require switching LLM from DeepSeek to Anthropic real; scope creep |
| GraphRAG / knowledge graphs | Hype past peak; standard RAG wins on cost-quality tradeoff |
| Multimodal (vision, voice) | Different problem class; scope creep |

## Foundation layer (~52h, must-do)

Industry-standard hardening. Without these the frontier work doesn't have a credible substrate.

### F1. Structured-output judge (4h)
Rewrite `src/eval/judge.py` using Anthropic SDK `messages.parse` + Pydantic `JudgeScore` schema. Eliminates current ~25% JSON parse failure rate (currently patched with cumulative rejudge). Standard 2025 practice.

### F2. RAGAS 4-metric integration (8h)
Add `src/eval/ragas_metrics.py` integrating: faithfulness, answer_relevancy, context_precision, context_recall. RAGAS is the de-facto standard for RAG eval (Shahul et al. 2023). Numbers comparable across projects.

### F3. Multi-LLM-judge consensus + inter-judge kappa (6h)
3 judges from different vendors: DeepSeek V4 Pro, Claude Haiku 4.5, GPT-4o-mini. Median scoring when agreement, flag for human review when max spread > 0.3. Compute inter-judge Cohen's kappa. Directly addresses same-model bias.

### F4. Algorithmic citation groundedness (4h)
`src/eval/citation_verify.py`: parse `[source:id]` tokens from agent output, verify against synthetic data IDs. Hard metric, not LLM-judge-dependent. Inspired by FActScore (CMU/UW 2023).

### F5. 30 reference answers in scenarios.json (4h)
Hand-author 200-400 word "ideal answer" per scenario. Judge prompt: "compare to reference, score semantic similarity to reference and rubric coverage". Anchors LLM-judge.

### F6. Trajectory eval (6h)
`src/eval/trajectory.py`: tool precision/recall/F1, redundancy, efficiency. Algorithmic; independent of LLM-judge. Inspired by LangSmith trace eval and Inspect AI (UK AISI 2024).

### F7. Public deploy + observability (10h)
- Fly.io deploy via existing `infra/fly.toml`
- Langfuse Cloud free tier + public read-only dashboard
- OpenTelemetry instrumentation across all 5 LangGraph nodes
- README header: live demo URL + Langfuse dashboard URL + telemetry badges

### F8. mkdocs-material documentation site (4h)
Wire existing `docs/*.md` into mkdocs-material, deploy to GitHub Pages. Standard OSS docs site.

### F9. MCP server wrappers (2 tools, 6h)
Package `slack_query` and `gdocs_search` as MCP servers (Model Context Protocol, Anthropic 2024). Test integration with Claude Desktop. 30-second demo GIF.

**Foundation subtotal: 52h**

## Frontier layer (~85h, 8 techniques)

Each technique: solo-implementable, defensible in interview, tied to recognized paper, produces a measurable demo result.

### #1. DSPy compiled prompts (15-20h)
- **Paper**: Khattab et al. 2023 (Stanford), "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines"
- **What**: Replace hand-tuned prompts in `prompts/{plan,tool_select,reflect,synthesize}.md` with DSPy modules. Use 30 scenarios as training data, optimize via BootstrapFewShot or MIPRO.
- **Demo result**: "+9% answer correctness on held-out subset, with no manual prompt tuning"
- **Why include**: This is the actual frontier of prompt engineering 2025-2026. Hand-tuned prompts are the "writing assembly by hand" era; DSPy-compiled is "writing C".

### #2. Process Reward Model (PRM) step-level evaluation (8-10h)
- **Paper**: Lightman et al. 2023 (OpenAI), "Let's Verify Step by Step". Productionized in o1 / Claude 4 thinking models.
- **What**: Add step-level reward scoring to each LangGraph node. Each plan / tool_select / reflect / synthesize step gets a 0-1 reward from a verifier LLM, exposed in Langfuse trace.
- **Demo result**: Per-step trace heatmap; identify which step weakest in failure cases.
- **Why include**: Frontier eval technique; demonstrates understanding of o1/Claude 4 training methodology.

### #3. Self-Refine critique loop (10-12h)
- **Paper**: Madaan et al. 2023, "Self-Refine: Iterative Refinement with Self-Feedback"
- **What**: Add `critique` node after `synthesize`. Agent reads own answer, identifies misses against `expected_topics` it has visibility to (inferred from query, not the scenario), decides whether to revise. Max 2 critique rounds.
- **Demo result**: action_recommend_quality 0.46 -> 0.65+ projected (biggest weakness in v1).
- **Why include**: Directly fixes v1's weakest metric with a recognized technique.

### #4. Multi-LLM Mixture-of-Experts routing (10-12h)
- **Paper**: Ong et al. 2024, "RouteLLM"; productionized at many AI platforms 2025.
- **What**: Different LLMs for different node types:
  - `plan`: Claude Sonnet 4.6 (strong global)
  - `tool_select`: Claude Haiku 4.5 (cheap structured)
  - `reflect`: Haiku 4.5 (short)
  - `synthesize`: Sonnet 4.6 (writing)
  - `critique`: GPT-4o-mini (independent vendor)
- **Demo result**: Pareto chart - all-Sonnet vs all-Haiku vs MoE; MoE should hit Pareto frontier with ~42% cost saving at <5% quality loss.
- **Why include**: Shows production-ready cost engineering, multi-vendor expertise.

### #5. Constitutional self-supervision (8-10h)
- **Paper**: Bai et al. 2022 (Anthropic), Constitutional AI; productionized everywhere by 2024.
- **What**: Add soft governance layer on top of hard RBAC. Write `config/constitution.md` with 10-15 principles (single-tenant, refuse uncertain access, citations real-only, append-only audit, etc.). After synthesize node, agent reads constitution and self-critiques against it. Layered with hard RBAC for defense-in-depth.
- **Demo result**: Dual-layer governance demo, catches edge cases hard rules miss.
- **Why include**: Two-layer governance is genuinely deeper than 99% of similar projects.

### #6. PAIR auto-adversarial generation (15-20h)
- **Paper**: Chao et al. 2023, "Jailbreaking Black Box Large Language Models in Twenty Queries" (PAIR)
- **What**: Replace 10 hand-written adversarial scenarios with auto-generated attacks. Attacker LLM (GPT-4o) generates novel jailbreak prompts targeting our 10 vectors (RBAC bypass, role escalation, etc.). Judge LLM scores defense. Attacker iterates from failures.
- **Demo result**: "1000 auto-generated adversarial attempts, 0.X% breach rate": vastly more credible than 10/10 on hand-written.
- **Why include**: automated red-teaming over a wide attack surface; novel demo.

### #7. Counterfactual robustness evaluation (12-15h)
- **Paper**: Liu et al. 2024 "Noise Robustness in RAG"; CRAG (Meta 2024)
- **What**: Generate 3 counterfactual variants per scenario:
  - **Noise injection**: add 5 irrelevant docs to retrieved context
  - **Doc deletion**: remove ground-truth supporting doc
  - **Entity swap**: replace Sarah with Alice
- Score degradation_rate = (clean_score - perturbed_score) / clean_score.
- **Demo result**: "Agent degrades only 12% under noise injection vs baseline 35%"
- **Why include**: Real robustness measure; what production teams actually care about.

### #8. Long-context Needle-In-A-Haystack (6-8h)
- **Paper**: Greg Kamradt's NIAH (2023); RULER (NVIDIA 2024)
- **What**: Scale synthetic data 100x (1M tokens worth of messages), bury 5 critical facts at 0%, 25%, 50%, 75%, 100% depth. Test agent retrieval accuracy.
- **Demo result**: NIAH matrix plot (context length x depth x recall) showing DeepSeek V4 Pro 1M context behavior.
- **Why include**: Demonstrates real use of 1M context window; visually striking README image.

**Frontier subtotal: 84-107h**

## Total time estimate

| Block | Wall-clock | Adjusted (~0.6x) |
|---|---|---|
| Foundation | 52h | 31h |
| Frontier (all 8) | 85-107h | 51-64h |
| Polish (blog, demo video, README rewrite) | 12-15h | 8-10h |
| **TOTAL** | **149-174h** | **90-105h** |

12-16 weeks at 6-8h/week = covers May -> September NL hire peak.

## Sprint plan

| Sprint | Weeks | Work | Hours (wall-clock) |
|---|---|---|---|
| 1 | 1-3 | Foundation F1-F6 (eval upgrades) | 32h |
| 2 | 4 | Foundation F7-F9 (deploy + docs + MCP) | 20h |
| 3 | 5 | Frontier #2 (PRM) + #5 (Constitutional) | 18h |
| 4 | 6-7 | Frontier #3 (Self-Refine) + #4 (Multi-LLM MoE) | 22h |
| 5 | 8-9 | Frontier #1 (DSPy) | 20h |
| 6 | 10-11 | Frontier #6 (PAIR) + #7 (Counterfactual) | 32h |
| 7 | 12 | Frontier #8 (NIAH) + signature blog | 14h |
| 8 | 13-14 | Polish + demo video recording | 10h |
| Buffer | 15-16 | - | 5-10h |

## Final state of project

### README header (target)
```
# Enterprise Knowledge Agent: pushing the limit of LLM + RAG

A flagship cross-source AI agent with 8 frontier techniques wired in:

│  Technique                       │ Paper                          │ Result
├──────────────────────────────────┼────────────────────────────────┼──────────────
│  DSPy compiled prompts           │ Khattab 2023 (Stanford)        │ +9% answer
│  Process Reward Model eval       │ Lightman 2023 (OpenAI)         │ per-step traces
│  Self-Refine critique loop       │ Madaan 2023                    │ action 0.46→0.71
│  Multi-LLM MoE routing           │ Ong 2024 (RouteLLM)            │ -42% cost
│  Constitutional self-supervision │ Bai 2022 (Anthropic)           │ 2-layer governance
│  PAIR auto-adversarial           │ Chao 2023                      │ 1000 attacks, 0.7% breach
│  Counterfactual robustness       │ Liu 2024, CRAG (Meta 2024)     │ -12% under noise
│  Long-context NIAH (1M)          │ Kamradt 2023, RULER 2024       │ 98% recall at depth 50%

🔗 Live: enterprise-knowledge-agent.fly.dev
📊 Public traces: <Langfuse URL>
📖 Docs: <username>.github.io/eka/
📝 Blog: "Pushing the limit of LLM-evaluated LLM-built agents"
```

### Leaderboard (projected)
- RAGAS faithfulness: 0.86
- RAGAS answer_relevancy: 0.83
- RAGAS context_precision: 0.78
- RAGAS context_recall: 0.85
- Multi-judge consensus answer: 0.74
- Inter-judge kappa (DeepSeek vs Sonnet): 0.79
- Algorithmic citation groundedness: 0.94
- Tool F1: 0.91
- PRM avg step reward: 0.81
- PAIR breach rate (n=1000): 0.7%
- Noise-injection robustness: -12% (vs -35% baseline)
- NIAH recall (1M, depth 50%): 98%
- Self-refine improvement: +18%
- Multi-LLM MoE cost saving: -42%

### Resume bullet
> Built **Enterprise Knowledge Agent** (Apache 2.0, live demo): a cross-source 6-SaaS AI agent integrating 8 frontier LLM + RAG techniques (DSPy compilation, Process Reward Models, Self-Refine, MoE routing, Constitutional AI, PAIR adversarial, counterfactual robustness, NIAH long-context). Achieves 0.86 RAGAS faithfulness, 0.7% breach rate over 1000 auto-attacks, 42% cost reduction via multi-LLM routing.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DSPy learning curve steeper than 15-20h | M | M | Fallback: hand-tuned prompts + paper citation; 4h instead of 20h |
| PAIR 1000 attempts API cost too high | L | L | Cap at 200 attempts; still strong signal |
| Multi-LLM MoE needs multi-vendor keys | M | M | Minimum viable: DeepSeek + 1 Claude key + 1 OpenAI key |
| Self-Refine introduces infinite-loop bug | L | M | Hard cap 2 critique rounds + state validation |
| DeepSeek 1M context actually unstable | M | L | Fallback NIAH to 200K context |
| Track A (job hunt) collision | H | M | +1 week per collision; do not cut scope |
| Burnout from sprint pace | M | H | Built-in 2-week buffer (sprints 15-16) |

## Open questions for Opus review

1. **Is the 8-technique frontier list genuinely frontier or hype-laden?** Specifically: are any of these past peak relevance or about to be?
2. **Are the time estimates realistic?** Specifically Frontier #1 (DSPy); is 15-20h enough to learn + integrate + tune, or is this 40h disguised?
3. **Sequencing**: should DSPy go before or after Self-Refine? They interact (DSPy can compile the critique prompt).
4. **What's missing that would actually be more impactful?** Specifically things like:
   - Continuous online eval (production-style A/B)
   - Semantic caching layer
   - Tool search (Anthropic's tool_search beta) for tool catalog scaling
5. **What can be cut without losing top-5% signal?** If a hiring manager scans for 30 seconds, which 2 of the 8 techniques are load-bearing?
6. **Defense-in-depth question**: is Constitutional self-check (Frontier #5) genuinely useful, or does it just add latency without improving governance compliance over the existing RBAC + adversarial regression?
7. **Honesty calibration**: any of the projected numbers (e.g., -42% cost saving, 0.7% breach rate, +18% from Self-Refine) feel too optimistic to defend?
8. **Will a NL AI Eng senior interviewer find this credible**, or will it read as "AI-assembled portfolio Christmas tree" lacking depth?

## Locked decisions (do not revisit in review)

- Single repo, not two PyPI packages
- DeepSeek as primary LLM (multi-LLM only for MoE ablation + judge consensus)
- Apache 2.0 license
- Fly.io as deploy target (not AWS)
- Solo dev: no external coordination
- 12-16 week timeline targeting Sept 2026
