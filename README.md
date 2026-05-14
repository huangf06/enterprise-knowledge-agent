# Enterprise Knowledge Agent

Production-grade open-source enterprise knowledge agent. Cross-source agentic reasoning over six SaaS surfaces (Slack / Jira / Calendar / GitHub / GDocs / Email) with auditable cross-source policy enforcement.

Ships four frontier-technique ablations with honest with-vs-without tables (three negatives, one positive), HotpotQA full-agent F1 of 0.816 (n=100 dev distractor) anchored against the ReAct paper baseline of 0.473, dual-cloud live deploy (Fly.io + Azure Container Apps), Langfuse tracing, and 117 / 117 tests.

> All data is synthetic and byte-deterministic from `seed=42`. No real customer data, no PII. Governance is a *pattern demo* on synthetic identity, not Okta / Azure AD federation (v1.5 scope).

**Live demo (dual-cloud)**:
- Fly.io: <https://enterprise-knowledge-agent.fly.dev/>
- Azure Container Apps: <https://eka-api.agreeabletree-5c626ab6.westeurope.azurecontainerapps.io/>

Both expose the same routes: `/health`, `GET /`, `POST /query` (SSE stream). See `docs/deploy.md` (Fly.io) and `docs/deploy-azure.md` (Azure all-sidecar architecture) for reproduction.

**Docs site**: <https://huangf06.github.io/enterprise-knowledge-agent/>
**Observability**: every `/query` emits a Langfuse trace with per-node generations + token counts.

```bash
curl -N -X POST https://enterprise-knowledge-agent.fly.dev/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is on my calendar today?","user_name":"Sarah Chen","user_role":"manager"}'
```

## Leaderboard

Self-authored cross-source briefing benchmark, 30 knowledge-worker scenarios. LLM-judge with single-author calibration; v4 adds multi-judge consensus (Anthropic Haiku 4.5 + OpenAI gpt-4o-mini + DeepSeek) on every published ablation per the v4.1 honesty calibration policy. See `docs/eval-methodology.md` for the closed-loop chapter.

| Metric | v1 DeepSeek baseline | Notes |
|---|---:|---|
| Answer correctness | **0.69** | LLM-judge, n=30, post-F1 structured judge |
| Completeness | **0.75** | LLM-judge, n=30 |
| Tool selection quality | **0.94** | LLM-judge, n=30 |
| Governance compliance | **1.00** | LLM-judge, n=30; perfect on the test set |
| Action recommend quality | **0.53** | weakest area; answers describe the situation more than they recommend a specific next step |
| Avg tool calls per query | 3.60 | hard cap is 6 |
| Avg latency per query (s) | 150 | wallclock end-to-end, p50 163s, p95 234s |
| Cost per query (USD) | $0.0036 | DeepSeek V4 Pro pricing, includes plan / tool_select / reflect / synthesize |

Per-category breakdown (the agent is strongest on multi_step and decision_support, weakest on conflict_resolution; tool selection is high across the board, governance compliance is perfect):

| Category | n | Answer | Complete | Tools | Gov | Action |
|---|---:|---:|---:|---:|---:|---:|
| decision_support | 8 | 0.85 | 0.89 | 0.90 | 1.00 | 0.62 |
| multi_step | 3 | 0.83 | 0.92 | 1.00 | 1.00 | 0.87 |
| cross_source_qa | 6 | 0.73 | 0.80 | 0.98 | 1.00 | 0.33 |
| morning_briefing | 8 | 0.62 | 0.61 | 0.99 | 1.00 | 0.51 |
| conflict_resolution | 5 | 0.41 | 0.55 | 0.82 | 1.00 | 0.42 |

Reproduce: `SELF_REFINE_ENABLED=0 uv run python scripts/run_eval.py --tier full` (full 30-scenario run, ~90 min wallclock at DeepSeek list price). Result lives in `eval_results/runs/eval-20260513-105857.json`.

**Adversarial governance regression: 10 / 10 blocked (100%)**. See `eval_results/adversarial.json` and `docs/w5_report.md`. Each of 10 cross-source attack vectors (RBAC bypass, role escalation, HR-doc leak, PII extraction, audit tamper, tool-result injection, cross-tenant switch, GDPR violation, markdown injection) is refused at the prompt-fence or RBAC layer before any data leaves the tool boundary.

**Scope of the governance 1.00**: perfect on this 30-scenario set + 10 adversarial vectors against the synthetic-identity policy table. The known blind spot: federation across a real Slack workspace / Jira project / GitHub org permission model is **not** in scope. This is a *pattern demo*; real federation (Okta / Azure AD / SAML) is v1.5 (see `docs/governance-design.md` first paragraph).

## Frontier ablations (v4)

Four frontier techniques shipped with explicit with-vs-without tables.

| Technique | Ablation | Verdict | Detail |
|---|---|---|---|
| Self-Refine (Madaan 2023) | OFF vs ON, n=30 | **OFF default**: -0.05 to -0.08 on correctness / completeness; +0.08 on source_coverage; +18% latency | [docs/frontier3_self_refine.md](docs/frontier3_self_refine.md) |
| DSPy compilation (synthesize node) | manual prompt vs compiled, n=10 | **OFF default**: 2-judge regime (the training metric) shows +0.05 on correctness; 3-judge regime (adds back the agent's model class) flips to -0.03, a Goodhart effect that v4.1 N1+P15 was designed to catch. Plus -1.0 on cite_source_coverage and -0.17 on action_recommend_quality. | [docs/sprint4_dspy_agent_ablation.md](docs/sprint4_dspy_agent_ablation.md) |
| Multi-LLM MoE (synthesize routing) | 4 vendors × n=10 fast-tier | **DeepSeek default**: Sonnet 4.6 lift is +0.07 (within n=10 noise floor) at 32× cost. All four vendors lie on the Pareto frontier; default to DeepSeek with Sonnet 4.6 as opt-in per-request | [docs/sprint5_moe_pareto.md](docs/sprint5_moe_pareto.md) |
| Counterfactual robustness | 3 perturbations × n=10 fast-tier | **Governance held at 1.00 across all perturbations**; doc_deletion drops answer_correctness to 0.0-0.3 (graceful degradation, no hallucination of removed sources) | [docs/sprint6_counterfactual_result.md](docs/sprint6_counterfactual_result.md) |

The two negatives (Self-Refine, DSPy) are kept as code paths behind env flags and shipped with the diagnosis docs above. Many production LLM systems ship those techniques claim-only with no ablation; v4 ships the table even when it does not favor the technique. That is the differentiation, not the optimization.

Public benchmarks (anchored against external baselines):

| Metric | Number | Baseline | Status |
|---|---:|---:|---|
| **HotpotQA F1 (full-agent mode, n=100, dev distractor)** | **0.816** | ReAct paper best-prompted 0.473, Yao 2022 | **PASS**, see `docs/hotpotqa_agent_result.md` |
| **HotpotQA EM (full-agent mode, same setup)** | **0.690** | ReAct paper ~0.30, Yao 2022 | **PASS**, same setup as F1 row |
| HotpotQA EM (retrieval-only, n=100, BGE-M3 top-2 + DeepSeek extraction) | 0.28 | naive span 0.0 | 4x lift over naive baseline |
| HotpotQA F1 (retrieval-only, same setup) | 0.29 | n/a | Lower bound: the gap to the full-agent row (2.8x) is the value of the agent loop |
| MS Marco MRR@10 (n=50, BGE-M3 cosine, top-10) | 0.54 | BGE-M3 published 0.32 | **PASS**, beats published baseline by 69% |

## Demo

A 30-second Monday morning briefing: Sarah Chen asks for today's priorities. The agent calls four tools across Slack / Jira / Calendar / Email, detects a Thursday all-hands vs. Alice 1:1 conflict, finds a Q3-launch PR blocking her review queue, surfaces the stale EY contract follow-up email, and recommends an ordered action list with inline citations and a tool-call audit summary.

Try it now on the live deploy:

```bash
curl -N -X POST https://enterprise-knowledge-agent.fly.dev/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is on my calendar today?","user_name":"Sarah Chen","user_role":"manager"}'
```

Recorded 30-second demo video is pending; `docs/demo-script.md` is the 6-scene shoot script.

## Quickstart

```bash
git clone https://github.com/huangf06/enterprise-knowledge-agent.git
cd enterprise-knowledge-agent
cp .env.example .env
# Fill DEEPSEEK_API_KEY in .env
docker compose up -d qdrant postgres
uv sync --extra dev
uv run python scripts/generate_data.py --seed 42     # required before docker / uvicorn; synthetic data is gitignored
uv run uvicorn src.api.main:api --reload
# POST /query with body {"query": "...", "user_name": "Sarah Chen", "user_role": "manager"}
# returns an SSE stream of plan / tool_select / tool_execute / reflect / synthesize events
```

For the full container stack: run `generate_data.py` first, then `docker compose up`. Image build for the API lives at `infra/Dockerfile` and bakes the generated synthetic dataset into the image.

## Differentiation

- **Cross-source policy engine pattern over six SaaS surfaces.** `#leadership` channel and HR-private GDocs are denied to managers via a yaml policy table and an audit log records every decision. This is a *pattern demo* on synthetic identity; production federation (Okta / Azure AD / SAML) is v1.5 scope. See `docs/governance-design.md`.
- **Self-authored 30-scenario cross-source briefing eval, with the closed-loop risk surfaced explicitly.** LLM-judge prompt, rubric, scenarios, synthetic data, and tool outputs are all open and byte-reproducible from `seed=42`. The methodology blog (`docs/eval-methodology.md`) addresses single-author calibration head-on.
- **Multi-judge consensus on every published ablation, with judge-pool isolation.** Anthropic Haiku 4.5 + OpenAI gpt-4o-mini + DeepSeek judge each ablation; DSPy training metric drops DeepSeek (the agent's primary) per v4.1 N1, and the comparison metric adds it back per v4.1 P15. The DSPy ablation surfaces a real Goodhart reversal under this dual regime (see `docs/sprint4_dspy_agent_ablation.md` "Critical finding"). Most LLM portfolios single-judge; this one publishes the cross-judge dispersion.
- **Self-hostable and reproducible.** One `docker compose up` brings the entire stack up locally; no proprietary services in the loop except the LLM API. Live on Fly.io since 2026-05-13; deploy guide at `docs/deploy.md`.

## Architecture

```
[Gradio UI / curl]
      ↓ POST /query
[FastAPI + SSE]
      ↓
[LangGraph 5-node ReAct agent]
  plan → tool_select → tool_execute → reflect → (loop or synthesize)
                          ↓
              [6-tool catalog: slack / jira / calendar / github / gdocs / email]
                          ↓
              [governance hooks: RBAC + PII redact + injection guard + audit]
                          ↓
              [synthetic 6-source dataset, 30 users, byte-deterministic from seed=42]

[retrieval: Qdrant + BGE-M3]   [audit: append-only JSONL → PostgreSQL in W5]
```

Full architecture diagram, module reuse table, and the Demo 2 modularity case study (HR Helpdesk single-source, optional) live in `docs/architecture.md` (lands W8).

## Repo map

- `src/data/`: synthetic generator, entity model, injection patterns
- `src/tools/`: six tool implementations and registry
- `src/governance/`: RBAC, PII redact, audit, GDPR, injection guard
- `src/agent/`: LangGraph 5-node graph
- `src/retrieval/`: BGE-M3 over Qdrant
- `src/eval/`: scenarios, judge, runner, retrieval sanity, adversarial
- `src/api/`: FastAPI SSE endpoint
- `prompts/`: version-controlled agent prompts
- `data/synthetic/`: generated (gitignored)
- `data/eval/`: scenarios, adversarial vectors, 30-user seed
- `docs/`: design, eval methodology, governance, failure modes
- `scripts/`: CLIs for generate, run_eval, run_adversarial, gates
- `.github/workflows/`: CI test, eval-gate, eval-nightly

## Honesty calibration

The "Three honest negatives" framing (Self-Refine, DSPy under 3-judge, and the Sonnet-MoE-lift-is-within-noise observation) came from running the experiments and publishing the tables as they fell, not from cherry-picking the runs that flattered the techniques. Multi-judge consensus + judge-pool isolation (v4.1 N1+P15) is what made the Goodhart reversal in the DSPy ablation visible at all.

## License

Apache-2.0. See [LICENSE](LICENSE).
