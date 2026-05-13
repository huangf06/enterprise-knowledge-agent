# Sprint 6 Frontier #7 Counterfactual robustness (scaffold ready)

Three perturbations per v4.1 plan, applied at tool-result level so `seed=42` synthetic data on disk is untouched.

## What's ready

`src/eval/counterfactual.py`:

| Function | Per spec | What it does |
|---|---|---|
| `apply_entity_swap(text)` | R3 | Rewrites non-protagonist entities only. `EY` -> `PwC`, `Q3 launch` -> `Q4 launch`, `Acme Corp` -> `Globex Inc`, `Alpha Pilot` -> `Beta Pilot`. Protagonist names (Sarah Chen) are NOT touched - retesting the injection guard on those is out of scope per Codex B5/B6. |
| `apply_noise_injection(text, n_lines=2)` | P10 | Appends 2 background-noise lines (newsletter / building / wellness chatter) to tool results. |
| `apply_doc_deletion(text, drop_pattern=None)` | P11 | Drops the paragraph with the most `[source:id]` citations (heuristic) or a caller-supplied pattern match. Tests graceful degradation. |
| `perturb_tool_history(history, mode)` | - | Apply any of the above to every tool result in a tool_history list, returning a copy. |

## Smoke

```
-- entity_swap --
  "The EY contract" -> "The PwC contract" ✓
  "Q3 launch" -> "Q4 launch" ✓
  "Acme Corp" -> "Globex Inc" ✓
  protagonist names untouched ✓

-- noise_injection --
  original text + 2-line [Background notes] block ✓

-- doc_deletion --
  most-cited paragraph removed; secondary paragraph retained ✓
```

## Sprint 6 day-of execution (not auto-run)

The full ablation requires re-running the agent over perturbed tool results. Two ways:

1. **Offline reuse**: take the N2 baseline rows (which carry `tool_history`), perturb the history with `perturb_tool_history`, re-invoke synthesize with the perturbed history, and re-judge. Costs only one synthesize call per scenario per variant.
2. **Live re-run**: route the agent's tool_execute through a perturbation wrapper. More authentic but costs the full agent cycle per scenario per variant.

Option 1 is the v4.1 default; it costs roughly $0.0005 / scenario / variant. Three variants x 30 scenarios x ~$0.001 (including judge) = $0.10 per full ablation pass.

```bash
# (Sprint 6 day-of):
uv run python scripts/run_counterfactual.py --variant entity_swap
uv run python scripts/run_counterfactual.py --variant noise_injection
uv run python scripts/run_counterfactual.py --variant doc_deletion
```

`scripts/run_counterfactual.py` is the remaining day-of work.

## Why we don't auto-run

Counterfactual robustness is the v4 frontier technique that takes longest to set up the harness (perturbation logic, offline-replay synthesize, per-variant judging). Tonight the *perturbation primitives* land. The runner + ablation table are a Sprint 6 day-of integration.
