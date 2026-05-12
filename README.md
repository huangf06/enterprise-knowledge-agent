# Enterprise Knowledge Agent

Production-grade open-source enterprise knowledge agent. Cross-source RAG + agentic reasoning + auditable cross-source policy enforcement.

> Status: in development (W1 scaffold). Public leaderboard and demo land at W8.

## Leaderboard

Self-authored cross-source briefing benchmark (n=50 knowledge worker scenarios, LLM-judge + author spot check + external reviewer calibration).

| Metric | Sonnet 4.6 | GPT-4o | Haiku 4.5 |
|---|---:|---:|---:|
| Answer correctness | TBD (W4 fills) | TBD (W4 fills) | TBD (W4 fills) |
| Citation groundedness | TBD (W4 fills) | TBD (W4 fills) | TBD (W4 fills) |
| Governance compliance (n=10 adversarial) | TBD (W5 fills) | TBD (W5 fills) | TBD (W5 fills) |
| Cost / query (USD) | TBD (W6 fills) | TBD (W6 fills) | TBD (W6 fills) |
| Latency p95 (s) | TBD (W6 fills) | TBD (W6 fills) | TBD (W6 fills) |

Retrieval component sanity checks (third-party benchmarks, retrieval pipeline health only):

| Metric | Number |
|---|---:|
| HotpotQA F1 (n=100) | TBD (W4 fills) |
| MS Marco MRR@10 (n=50) | TBD (W4 fills) |

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
