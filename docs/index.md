# Enterprise Knowledge Agent

Production-grade open-source enterprise knowledge agent. Cross-source agentic reasoning over six SaaS surfaces (Slack / Jira / Calendar / GitHub / GDocs / Email) with auditable cross-source policy enforcement.

## Repo

[github.com/huangf06/enterprise-knowledge-agent](https://github.com/huangf06/enterprise-knowledge-agent)

## What this site contains

- **Plan**: the locked v4.1 frontier enhancement plan + the second-pass review notes.
- **Eval**: per-feature evaluation reports - N2 cost/latency baseline (the canonical reference all frontier deltas compare against), A1 retrieval ablation, F4 citation groundedness.
- **Reference**: prompts and review artifacts.

## Quick links

- v4 plan: [v4-frontier-plan.md](v4-frontier-plan.md)
- N2 baseline: [n2_baseline.md](n2_baseline.md)
- Retrieval ablation: [a1_retrieval_ablation.md](a1_retrieval_ablation.md)
- Citation groundedness metric: [f4_citation_groundedness.md](f4_citation_groundedness.md)

## Honesty calibration

Per v4.1 plan section *Honesty calibration policy*, every published leaderboard number ships with a "with vs without" ablation. The project is built solo with Claude Code + Codex CLI pair-programming; design decisions, architecture, and trade-offs are mine, code execution is paired.
