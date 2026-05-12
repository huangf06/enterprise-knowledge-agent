# v1 status — what's done, what's only-you

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
- LLM-as-judge harness (`src/eval/judge.py`)
- Retrieval sanity scorers (HotpotQA + MS Marco) with both naive and llm-answer modes

### Infra
- `docker-compose.yml` (Qdrant + Postgres + API container)
- `infra/Dockerfile` (API) + `infra/Dockerfile.gradio` (UI)
- `infra/fly.toml` for Fly.io
- `infra/huggingface-space.yml` for HF Space
- `.github/workflows/`: test.yml, eval-gate.yml, eval-nightly.yml

### Docs
- `README.md` with leaderboard, architecture diagram, repo map, differentiation bullets
- `docs/architecture.md` (per-layer diagram + module reuse table)
- `docs/governance-design.md` (cross-source policy pattern framing)
- `docs/failure-modes.md` (10 failure modes documented)
- `docs/eval-methodology.md` (closed-loop honest chapter, blog draft)
- `docs/case-study-hr-helpdesk.md` (Demo 2)
- `docs/deploy.md` (Fly.io + HF Space + AWS deferred)
- `docs/demo-script.md` (5-min video storyboard)
- `docs/w1_report.md`, `docs/w2_report.md`, `docs/w4_report.md`, `docs/w5_report.md` (per-gate audits)

### Tests
- 66 pytests, all green

## Only-you (cannot automate)

| Item | Why | Where to start |
|---|---|---|
| Record the 5-min demo video | screen + voice capture | follow `docs/demo-script.md` storyboard scene by scene |
| `fly deploy` to public URL | needs your Fly.io account + paid CC | `infra/fly.toml`, `docs/deploy.md` |
| Push to HF Space | needs your HF account | `infra/huggingface-space.yml`, `docs/deploy.md` |
| W9 launch posts | manual social / outreach | NL AI Slack groups, LinkedIn, HN, r/MachineLearning |
| External reviewer spot-check | needs reaching out to 1-2 NL tech contacts | W7 hard gate per design |
| Multi-LLM ablation columns (Sonnet 4.6 / GPT-4o / Haiku 4.5) | needs additional API keys | once a second key is set in `.env`, the eval harness picks up the model from `LLM_MODEL` |
| Add `ANTHROPIC_API_KEY` for real Claude calls | needs the key | swap `DEEPSEEK_API_KEY` in `.env` and unset `ANTHROPIC_BASE_URL` |
| Production federation (Okta / SAML) | architecture pivot | v1.5 backlog explicit; design Section 3.3 |
| Demo GIF capture | screen recording | once UI is recorded for the video, extract a 5-10s clip |

## Final auto-run numbers

| Item | Result |
|---|---|
| Full 30-scenario eval | answer=0.71, complete=0.75, tools=0.96, gov=0.97, action=0.46 (eval-20260512-161340-rejudged.json) |
| HotpotQA llm-answer | EM=0.28, F1=0.29 (lift from F1=0.077 naive baseline) |
| MS Marco MRR@10 | 0.54 (PASS, beats published baseline) |
| Adversarial | 10 / 10 blocked (100%) |
