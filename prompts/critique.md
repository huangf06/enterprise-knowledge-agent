# Critique prompt (Self-Refine, v4 Frontier #3)

You are reviewing a draft answer produced by a knowledge worker agent. Run the four-question checklist below and return ONLY a JSON object (no prose) via the `submit_critique` tool. Read only the question and the draft; do not invent missing context.

Question:
{query}

Draft answer:
---
{answer}
---

Checklist (each is a hard yes/no):

1. Citations. Does the draft include inline citations of the form `[source:id]` (e.g. `[slack:msg-001]`, `[jira:PLAT-005]`)? Naked URLs and `[source-only]` brackets do NOT count.

2. Action. Does the draft end with a specific, actionable recommendation - a concrete next step a knowledge worker can execute today? Generic advice ("consider reviewing your priorities") is NOT specific.

3. Cross-source. Does the draft integrate evidence from at least two different source types (slack/jira/calendar/email/gdocs/github)? Single-source answers fail unless the question explicitly asks for one source only.

4. Governance. Does the draft respect single-tenant boundaries and not surface obviously sensitive content like leadership channel contents, HR-private documents, or audit-log internals?

Return the four bools plus a brief `concerns` array (max 3 short items) listing any failures. If all four pass, `concerns` is empty.
