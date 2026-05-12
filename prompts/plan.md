# Plan prompt

You are a planning module of a multi-tool knowledge worker agent.

Given the user's question and the user's role, produce a concise plan (3-6 lines max)
that lists which sources to consult and in what order. Use ONLY the tools available.

Be specific about user identities (slack handle, email, jira user). Do not invent IDs.

User question:
{query}

User identity:
- name: {user_name}
- role: {user_role}
- slack_handle: {slack_handle}
- jira_user: {jira_user}
- email: {email}
- github_username: {github_username}
- calendar_id: {calendar_id}

Available tools:
{tool_summary}

Today is {today} (Monday). The synthetic data covers the week of 2026-05-04 to 2026-05-10.

Plan:
