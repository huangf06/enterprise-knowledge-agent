# F4 algorithmic citation groundedness (Sprint 2)

LLM-free metric replacing the partial-credit citation portion of the LLM judge's `answer_correctness`. Runs deterministically off `(answer, tool_history)` pairs already captured in every eval row.

Implementation: `src/eval/citation.py`. Three scores per scenario:

| Field | Definition |
|---|---|
| `well_formedness` | fraction of bracketed tokens in the answer that match `[source:id]`. Penalizes naked URLs, `[source-only]`, malformed brackets. |
| `source_coverage` | of cited `(source, id)` pairs, fraction whose `source` maps to a tool the agent actually called. Catches hallucinated sources. |
| `id_grounded` | of cited `(source, id)` pairs, fraction where `id` appears as a substring in the relevant tool's result text. Catches invented IDs. |

Source-to-tool map (from `SOURCE_TO_TOOL`):
- `slack` → `slack_query`
- `jira` → `jira_query`
- `cal` / `calendar` → `calendar_query`
- `gh` / `github` → `github_pr_review`
- `gdoc` / `gdocs` → `gdocs_search`
- `email` → `email_query`

Unknown source tags fail both `source_coverage` and `id_grounded`.

## Why this matters for v4

The LLM judge's `answer_correctness` collapses three distinct failure modes (factual wrong, hallucinated citation, malformed format) into one fuzzy float. F4 decomposes the citation-quality slice so a frontier technique that improves citations can be measured separately from one that improves factual content. Critical for Self-Refine (Sprint 3) and CRITIC-style critique (v1.5) deltas.

## Status

- Module + per-row aggregation wired into `src/eval/runner.py`. Each eval row now carries a `citations` field alongside `scores`.
- Tool history is preserved in the eval row (`tool_history` field, gitignored under `eval_results/runs/`) so this metric can be re-run offline on any past run without re-invoking the agent.
- Backfill across existing pre-F4 runs: not possible (old rows lack `tool_history`); fresh eval runs from this commit onward have full citation scoring.
