# Case study: HR Helpdesk single-source modularity (Demo 2)

> Per design Section 4. This is an **optional modularity case study**, not a hard gate. The point is to show how much of the cross-source agent infrastructure reuses verbatim when the vertical changes.

## What is reused, what is re-authored

See the table in `docs/architecture.md`. Headline:

- **100% reused**: LangGraph 5-node skeleton, Tool base + registry, PII redaction, prompt-injection guard, audit log, LLM-judge harness, Gradio UI shell.
- **~90% reused, yaml swap**: RBAC policy engine (new roles/resources but same engine).
- **0% reused, re-authored**: Synthetic data (HR handbook corpus, ~6 policies), tool implementations (3 new), eval scenarios (5 new).

## Files

| File | Purpose |
|---|---|
| `data/hr_corpus/handbook.json` | HR handbook corpus + 1 employee profile (Lisa Park) |
| `src/case_studies/hr_helpdesk/tools.py` | 3 tools: `hr_policy_search`, `employee_self_data_query`, `escalation_routing` |
| `src/case_studies/hr_helpdesk/scenarios.json` | 5 scenarios: paternity, code-freeze vacation, GDPR erasure, expense, escalation |

The same `src/eval/runner.py` runs both Demo 1 and Demo 2 scenarios; just point the loader at the alternate scenarios file. Same `src/eval/judge.py` rubric.

## Demo story (30 seconds)

Lisa Park asks:

> I'm planning paternity leave for 4 weeks next month, and I want to add my July family vacation right after. Is that allowed?

Agent calls:

1. `hr_policy_search(keyword="paternity")` → `pol-paternity` (4 weeks paid, can stack but 8-week cap)
2. `hr_policy_search(keyword="vacation")` → `pol-vacation` (25 days/year, stacking requires HR pre-approval)
3. `employee_self_data_query(employee_id="u023")` → vacation_balance=17, paternity_taken=false

Answer:

> Yes, with one caveat. You have 17 vacation days banked. 4 weeks paternity + 2 weeks vacation = 6 weeks combined, which is under the 8-week combined absence cap [pol-paternity], so VP approval is not required. Notify HR at least 4 weeks ahead; stacking is permitted with HR pre-approval [pol-vacation]. Avoid the Q3 launch code-freeze window if your dates would land there [pol-code-freeze].

## RBAC demonstration

`employee_self_data_query` enforces self-only access: a different user calling it for Lisa's profile gets `RBAC denied: employee_self_only`. HR / exec roles can call it for any employee.

## Why this isn't run as a hard gate

The W7 design decision (Codex review v1.4) downgrades Demo 2 from "real second vertical" to "optional 2-day modularity case study." Its job is to make the module reuse table credible. Full Demo 2 eval runs are nice-to-have, not load-bearing.

## How to run

```python
# Manual smoke (no agent loop; just the tools):
from src.case_studies.hr_helpdesk import HR_POLICY_TOOL, EMPLOYEE_DATA_TOOL
print(HR_POLICY_TOOL.run({"keyword": "paternity"}, {"role": "IC"}))
print(EMPLOYEE_DATA_TOOL.run({"employee_id": "u023"}, {"user_id": "u023", "role": "IC"}))
```

Wiring Demo 2 into the LangGraph agent + a separate ToolRegistry takes ~30 minutes and lands in v1.5.
