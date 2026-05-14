# v1 status: what's done, what's only-you

> Auto-generated snapshot of the v1 power-through. For per-week details see `docs/w{1..5}_report.md`.

## Done (committed on `main`)

### Code
- 6 cross-source tools (slack / jira / calendar / github / gdocs / email) with shared `Tool(args, ctx)` contract
- LangGraph 5-node ReAct agent (`src/agent/`)
- FastAPI + SSE `/query` endpoint
- Gradio reveal-panel UI (`src/ui/app.py`)
- Anthropic SDK client wired to DeepSeek's Anthropic-compatible endpoint (`src/llm/anthropic_client.py`)
- Cost ledger with DeepSeek pricing (`src/llm/cost_ledger.py`)
- BGE-M3 + Qdrant retrieval (`src/retrieval/`)
- Demo 2 HR Helpdesk modularity case study (`src/case_studies/hr_helpdesk/`)

### Governance
- `config/rbac_policies.yaml` with IC / manager / exec / HR roles
- `src/governance/rbac.py`, `pii_redact.py`, `audit.py`, `gdpr.py`, `injection_guard.py`
- Single-tenant + audit-immutability hard rules in prompts
- 10/10 adversarial scenarios blocked (`docs/w5_report.md`)

### Eval
- 30 self-authored cross-source scenarios (`data/eval/scenarios.json`)
- 10 adversarial governance scenarios (`data/eval/adversarial.json`)
- 5 HR helpdesk Demo 2 scenarios (`src/case_studies/hr_helpdesk/scenarios.json`)
- LLM-as-judge harness (`src/eval/judge.py`) with 3-vendor multi-judge consensus (Anthropic + OpenAI + DeepSeek)
- Retrieval sanity scorers (HotpotQA + MS Marco) with both naive and llm-answer modes
- HotpotQA full-agent benchmark, n=100 dev distractor: F1=0.816, EM=0.690 (`src/eval/hotpotqa_*.py`, `docs/hotpotqa_agent_result.md`)
- 4 frontier-technique ablations published with-vs-without (Self-Refine, DSPy compilation, multi-LLM MoE, counterfactual robustness)

### Infra
- `docker-compose.yml` (Qdrant + Postgres + API container)
- `infra/Dockerfile` (API) + `infra/Dockerfile.gradio` (UI)
- `infra/fly.toml` for Fly.io (live)
- `infra/azure/deploy.sh` for Azure Container Apps (live, dual-cloud sibling of Fly.io)
- `infra/huggingface-space.yml` for HF Space
- `.github/workflows/`: test.yml, eval-gate.yml, eval-nightly.yml

### Docs
- `README.md` with leaderboard, architecture diagram, repo map, differentiation bullets
- `docs/architecture.md` (per-layer diagram + module reuse table)
- `docs/governance-design.md` (cross-source policy pattern framing)
- `docs/failure-modes.md` (10 failure modes documented)
- `docs/eval-methodology.md` (single-author calibration write-up)
- `docs/case-study-hr-helpdesk.md` (Demo 2)
- `docs/deploy.md` (Fly.io + HF Space + AWS deferred)
- `docs/deploy-azure.md` (Azure Container Apps all-sidecar architecture, dual-cloud reproduction)
- `docs/hotpotqa_agent_result.md` (full-agent benchmark setup, result table, ReAct comparison, failure analysis)
- `docs/demo-script.md` (5-min video storyboard)
- `docs/w1_report.md`, `docs/w2_report.md`, `docs/w4_report.md`, `docs/w5_report.md` (per-gate audits)

### Tests
- 117 pytests, all green (66 v1 base + 4 frontier ablation suites + 13 HotpotQA benchmark)

## Only-you (cannot automate)

| Item | Why | Where to start |
|---|---|---|
| Record the 5-min demo video | screen + voice capture | follow `docs/demo-script.md` storyboard scene by scene |
| Push to HF Space | needs your HF account | `infra/huggingface-space.yml`, `docs/deploy.md` |
| W9 launch posts | manual social / outreach | NL AI Slack groups, LinkedIn, HN, r/MachineLearning |
| External reviewer spot-check | needs reaching out to 1-2 NL tech contacts | W7 hard gate per design |
| Production federation (Okta / SAML) | architecture pivot | v1.5 backlog explicit; design Section 3.3 |
| Demo GIF capture | screen recording | once UI is recorded for the video, extract a 5-10s clip |

## Final auto-run numbers

| Item | Result |
|---|---|
| Full 30-scenario eval | answer=0.69, complete=0.75, tools=0.94, gov=1.00, action=0.53 (eval-20260513-105857.json) |
| HotpotQA full-agent (n=100, dev distractor) | F1=0.816, EM=0.690 (1.7x ReAct paper best-prompted 0.473) |
| HotpotQA retrieval-only (n=100) | EM=0.28, F1=0.29 (lower-bound component sanity) |
| MS Marco MRR@10 | 0.54 (PASS, beats BGE-M3 published baseline 0.32 by 69%) |
| Adversarial | 10 / 10 blocked (100%) |
| Live deploy | dual-cloud: Fly.io + Azure Container Apps (westeurope) |
