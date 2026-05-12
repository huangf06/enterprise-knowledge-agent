# Enterprise Knowledge Agent

Production-grade open-source enterprise knowledge agent. Cross-source RAG + agentic reasoning + auditable cross-source policy enforcement.

> Status: in development (W1 scaffold). Public leaderboard and demo land at W8.

## Leaderboard

Self-authored cross-source briefing benchmark (n=50 knowledge worker scenarios, LLM-judge + author spot check + external reviewer calibration).

| Metric | DeepSeek V4 Pro (1M) |
|---|---:|
| Answer correctness (n=5 partial) | 0.60 |
| Completeness (n=5 partial) | 0.60 |
| Tool selection quality (n=5 partial) | 0.60 |
| Governance compliance (n=5 partial) | 0.60 |
| Action recommend quality (n=5 partial) | 0.58 |
| Avg tool calls per query | 4.0 |
| Avg latency per query (s) | 181 |

n=5 partial run; full 30 scenarios takes ~100 min wallclock. Note: 2/5 scenarios in this run hit a judge JSON parse error (fixed in the same commit); the 3 that scored properly were perfect across all metrics. Re-run via `scripts/run_eval.py`.

Multi-LLM ablation (GPT-4o / Haiku 4.5 / Sonnet 4.6) is **v1.5** per Fei's W2 decision to use a single DeepSeek model; columns will be added if a second key arrives.

Retrieval component sanity checks (third-party benchmarks, retrieval pipeline health only — NOT the project's main eval anchor):

| Metric | Number | Target | Status |
|---|---:|---:|---|
| HotpotQA F1 (n=100, BGE-M3 + naive span) | 0.077 | 0.70 | Below target — answer extraction naive in v1; W6 swaps to agent loop |
| MS Marco MRR@10 (n=50, BGE-M3 + cosine) | 0.5381 | 0.32 | PASS (beats published baseline) |

## Demo

![Demo GIF placeholder](docs/demo.gif)

30-second Monday morning briefing across 6 sources (Slack / Jira / Calendar / GitHub / GDocs / Email) with cross-source policy enforcement visible in the reveal panel. Recording lands at W8.

## Quickstart

```bash
git clone https://github.com/<user>/enterprise-knowledge-agent.git
cd enterprise-knowledge-agent
docker compose up -d
```

Full quickstart with API key configuration lands at W7 alongside public deploy.

## Differentiation

- Cross-source policy engine pattern over six SaaS surfaces, demonstrated on a synthetic identity provider. Production federation (Okta / Azure AD / SAML) is v1.5 scope.
- Self-authored 50-scenario cross-source briefing eval with LLM-judge methodology blog and external reviewer calibration. Data, prompts, and judge prompts are fully open and reproducible from seed.
- Self-hostable and reproducible. One `docker compose up` brings the entire stack up locally.

## Architecture

Architecture diagram and module reuse table land at W8 alongside the eval methodology blog and governance design doc.
