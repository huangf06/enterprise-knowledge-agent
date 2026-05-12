# Enterprise Knowledge Agent

Production-grade open-source enterprise knowledge agent. Cross-source agentic reasoning over six SaaS surfaces (Slack / Jira / Calendar / GitHub / GDocs / Email) with auditable cross-source policy enforcement.

## Leaderboard

Self-authored cross-source briefing benchmark, 30 knowledge-worker scenarios. LLM-judge with single-author calibration (external review pending; see `docs/eval-methodology.md` for the closed-loop honesty chapter).

| Metric | DeepSeek V4 Pro (1M ctx) | Notes |
|---|---:|---|
| Answer correctness | **0.71** | LLM-judge, n=30 |
| Completeness | **0.75** | LLM-judge, n=30 |
| Tool selection quality | **0.96** | LLM-judge, n=30 |
| Governance compliance | **0.97** | LLM-judge, n=30 |
| Action recommend quality | **0.46** | weakest area — agent gives general advice where scenarios expect a specific action |
| Avg tool calls per query | 3.73 | hard cap is 6 |
| Avg latency per query (s) | 169 | wallclock end-to-end |

Per-category breakdown (the agent is strongest on decision_support / cross_source_qa, weakest on conflict_resolution; tool selection is high across the board):

| Category | n | Answer | Complete | Tools | Gov | Action |
|---|---:|---:|---:|---:|---:|---:|
| decision_support | 8 | 0.86 | 0.94 | 0.98 | 1.00 | 0.74 |
| cross_source_qa | 6 | 0.87 | 0.70 | 0.88 | 1.00 | 0.10 |
| morning_briefing | 8 | 0.64 | 0.66 | 1.00 | 0.88 | 0.43 |
| multi_step | 3 | 0.47 | 0.67 | 1.00 | 1.00 | 0.67 |
| conflict_resolution | 5 | 0.56 | 0.68 | 0.94 | 1.00 | 0.40 |

Reproduce: `uv run python scripts/run_eval.py` (full 30-scenario run, ~100 min wallclock). Result lives in `eval_results/runs/eval-20260512-161340-rejudged.json`.

**Adversarial governance regression: 10 / 10 blocked (100%)**. See `eval_results/adversarial.json` and `docs/w5_report.md`. Each of 10 cross-source attack vectors (RBAC bypass, role escalation, HR-doc leak, PII extraction, audit tamper, tool-result injection, cross-tenant switch, GDPR violation, markdown injection) is refused at the prompt-fence or RBAC layer before any data leaves the tool boundary.

Multi-LLM ablation (GPT-4o / Claude Sonnet 4.6 / Haiku 4.5) is **v1.5** per the W2 decision to ship on a single DeepSeek model; columns are added when additional keys arrive.

Retrieval component sanity (third-party benchmarks; **not** the main eval anchor):

| Metric | Number | Target | Status |
|---|---:|---:|---|
| HotpotQA EM (n=100, BGE-M3 top-2 + DeepSeek answer extraction) | 0.28 | — | 4x lift over naive span mode (0.0) |
| HotpotQA F1 (same setup) | 0.29 | 0.70 | Below target; gap is the simple 2-passage retrieval + no QA fine-tune. Tunable via top-k + a stronger answer model |
| MS Marco MRR@10 (n=50, BGE-M3 cosine, top-10) | 0.54 | 0.32 | **PASS** — beats the BGE-M3 published baseline |

## Demo

A 30-second Monday morning briefing: Sarah Chen asks for today's priorities. The agent calls four tools across Slack / Jira / Calendar / Email, detects a Thursday all-hands vs. Alice 1:1 conflict, finds a Q3-launch PR blocking her review queue, surfaces the stale EY contract follow-up email, and recommends an ordered action list — with inline citations and a tool-call audit summary.

Demo video and reveal-panel GIF land in `docs/demo.gif` at W8. The full run trace is preserved in `docs/w2_report.md`.

## Quickstart

```bash
git clone https://github.com/<user>/enterprise-knowledge-agent.git
cd enterprise-knowledge-agent
cp .env.example .env
# Fill DEEPSEEK_API_KEY in .env
docker compose up -d qdrant postgres
uv sync --extra dev
uv run python scripts/generate_data.py --seed 42
uv run uvicorn src.api.main:api --reload
# POST /query with body {"query": "...", "user_name": "Sarah Chen", "user_role": "manager"}
# returns an SSE stream of plan / tool_select / tool_execute / reflect / synthesize events
```

For the full container stack: `docker compose up`. Image build for the API lives at `infra/Dockerfile`.

## Differentiation

- **Cross-source policy engine pattern over six SaaS surfaces.** `#leadership` channel and HR-private GDocs are denied to managers via a yaml policy table and an audit log records every decision. This is a *pattern demo* on synthetic identity — production federation (Okta / Azure AD / SAML) is v1.5 scope. See `docs/governance-design.md`.
- **Self-authored 30-scenario cross-source briefing eval, with the closed-loop risk surfaced explicitly.** LLM-judge prompt, rubric, scenarios, synthetic data, and tool outputs are all open and byte-reproducible from `seed=42`. The methodology blog (`docs/eval-methodology.md`) addresses single-author calibration head-on.
- **Self-hostable and reproducible.** One `docker compose up` brings the entire stack up locally; no proprietary services in the loop except the LLM API. Deploy to Fly.io / HF Spaces is documented at `docs/deploy.md` (pending W7 completion).

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

- `src/data/` — synthetic generator + entity model + injection patterns
- `src/tools/` — six tool implementations + registry
- `src/governance/` — RBAC, PII redact, audit, GDPR, injection guard
- `src/agent/` — LangGraph 5-node graph
- `src/retrieval/` — BGE-M3 + Qdrant
- `src/eval/` — scenarios, judge, runner, retrieval sanity, adversarial
- `src/api/` — FastAPI SSE endpoint
- `prompts/` — version-controlled agent prompts
- `data/synthetic/` — generated (gitignored)
- `data/eval/` — scenarios + adversarial + 30-user seed
- `docs/` — design + eval methodology + governance + failure modes
- `scripts/` — CLIs (generate, run_eval, run_adversarial, gates)
- `.github/workflows/` — CI test + eval-gate + eval-nightly
