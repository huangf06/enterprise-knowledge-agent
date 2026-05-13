# Self-Refine ablation table

Source OFF: `eval_results/runs/eval-20260513-105857.json`
Source ON:  `eval_results/runs/eval-20260513-111407.json`

| Metric | OFF | ON | Delta |
|---|---:|---:|---:|
| answer_correctness | 0.6917 | 0.6150 | -0.0767 |
| completeness | 0.7450 | 0.6933 | -0.0517 |
| tool_selection_quality | 0.9367 | 0.9417 | +0.0050 |
| governance_compliance | 1.0000 | 1.0000 | 0.0000 |
| action_recommend_quality | 0.5250 | 0.4867 | -0.0383 |
| cite_well_formedness | 0.7076 | 0.6824 | -0.0252 |
| cite_source_coverage | 0.9155 | 1.0000 | +0.0845 |
| cite_id_grounded | 0.7521 | 0.6723 | -0.0798 |
| traj_tool_f1 | 0.7298 | 0.7389 | +0.0091 |
|  |  |  |  |
| avg_elapsed_s | 150.40 | 177.91 | +27.51s |
| p50_elapsed_s | 163.34 | 177.21 | +13.87s |
| agent_cost_usd_per_query | 0.003612 | 0.003884 | +0.000272 |
