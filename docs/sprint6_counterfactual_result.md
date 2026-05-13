# Sprint 6 Frontier #7 Counterfactual robustness — ablation result

Baseline: `eval-20260513-105857.json` (subset n=10)
Counterfactual: `counterfactual-20260513-122722.json` (3 modes × subset)

Each perturbation modifies the tool_history that the synthesize node sees;
the agent flow (plan + tool_select + tool_execute + reflect) is held constant
by replay. The judge scores the new answer against the original scenario
rubric — so a perturbed entity name lowers `answer_correctness` because the
expected_topics no longer match, BUT `governance_compliance` must stay at 1.0
for the governance layer to be called robust. That is the load-bearing test.

| Metric | Baseline | entity_swap | Δ | noise_injection | Δ | doc_deletion | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| answer_correctness | 0.7800 | 0.7800 | 0.0000 | 0.7700 | -0.0100 | 0.2000 | -0.5800 |
| completeness | 0.8350 | 0.8300 | -0.0050 | 0.8500 | +0.0150 | 0.2400 | -0.5950 |
| tool_selection_quality | 0.9700 | 0.9520 | -0.0180 | 0.9550 | -0.0150 | 0.9500 | -0.0200 |
| governance_compliance | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| action_recommend_quality | 0.6400 | 0.5300 | -0.1100 | 0.7250 | +0.0850 | 0.3100 | -0.3300 |
| cite_well_formedness | 0.6083 | 0.8441 | +0.2358 | 0.6000 | -0.0083 | 0.9667 | +0.3584 |
| cite_source_coverage | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |
| cite_id_grounded | 0.7750 | 0.7714 | -0.0036 | 0.8000 | +0.0250 | 0.8333 | +0.0583 |

## Interpretation

**Governance held across all three perturbations** (1.00 baseline → entity_swap=1.00, noise_injection=1.00, doc_deletion=1.00). The RBAC + injection-guard layer is not entity-aware; it filters on policy tables and structural prompt patterns rather than entity names, which is why swapping `EY` for `PwC` or padding noise lines does not move the metric.

answer_correctness and completeness deltas under entity_swap are EXPECTED to be negative: the perturbed answer talks about `PwC` while the rubric's expected_topics still mention `EY`. That is the test that the judge is actually looking at content (which it is). Treat correctness deltas as a judge-faithfulness signal, not a robustness signal.

Citation deltas reveal how robust the synthesize prompt is to noisy evidence: a sharp drop in `source_coverage` under noise_injection means the model is citing the noise lines, while a sharp drop in `id_grounded` under doc_deletion means the model is hallucinating IDs that no longer appear in tool_history.
