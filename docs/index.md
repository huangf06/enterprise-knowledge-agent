# Enterprise Knowledge Agent

Open-source enterprise knowledge agent. Reasons across six SaaS surfaces (Slack, Jira, Calendar, GitHub, GDocs, Email) with auditable cross-source policy enforcement.

- **Live demo**: <https://enterprise-knowledge-agent.fly.dev/>
- **Repo**: [github.com/huangf06/enterprise-knowledge-agent](https://github.com/huangf06/enterprise-knowledge-agent)
- **Observability**: every `/query` emits a Langfuse trace with per-node generations.

## What this site contains

- **Architecture**: system overview, governance design, failure modes, eval methodology.
- **Frontier ablations**: per-technique with-vs-without tables (Self-Refine, DSPy, MoE, counterfactual).
- **Benchmarks**: HotpotQA full-agent result, adversarial coverage.
- **Deploy**: Fly.io and Azure Container Apps reproduction guides.

## Frontier ablations

Every frontier technique ships with a with-vs-without table.

- Self-Refine: [frontier3_self_refine.md](frontier3_self_refine.md). Negative result on core metrics (-0.05 to -0.08).
- DSPy compile + wire: [sprint4_dspy_result.md](sprint4_dspy_result.md) and [sprint4_dspy_agent_ablation.md](sprint4_dspy_agent_ablation.md). Negative on production metrics.
- MoE synthesize Pareto: [sprint5_moe_pareto.md](sprint5_moe_pareto.md). Cost / quality trade-off across 4 vendors.
- Counterfactual robustness: [sprint6_counterfactual_result.md](sprint6_counterfactual_result.md). Governance held under perturbation.

## Calibration

Every published leaderboard number ships with a with-vs-without ablation.
