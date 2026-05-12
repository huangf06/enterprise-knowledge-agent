#!/usr/bin/env python3
"""W2 hard gate: end-to-end agent run on Sarah's morning briefing. Writes docs/w2_report.md."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.agent import app  # noqa: E402
from src.data.entity_consistency import load_users  # noqa: E402

REPORT_PATH = REPO_ROOT / "docs" / "w2_report.md"
QUERY = (
    "Morning briefing for today across Slack, Jira, and Calendar. "
    "What should I focus on? Highlight conflicts and blockers."
)


def main() -> int:
    users = {u.name: u for u in load_users()}
    sarah = users["Sarah Chen"]
    state = {
        "query": QUERY,
        "user_name": sarah.name,
        "user_role": "manager",
        "user_identity": {
            "slack_handle": sarah.slack_handle,
            "jira_user": sarah.jira_user,
            "email": sarah.email,
            "github_username": sarah.github_username,
            "calendar_id": sarah.calendar_id,
        },
        "max_iterations": 5,
        "tool_history": [],
        "streaming_events": [],
        "pending_tool": None,
    }
    result = app().invoke(state, config={"recursion_limit": 40})

    buf = StringIO()
    print("# W2 hard gate report", file=buf)
    print("", file=buf)
    print(
        "Agent end-to-end smoke against the 3-tool catalog (slack_query / jira_query / "
        "calendar_query), streaming events through the LangGraph 5-node skeleton. Per "
        "design Section 8 W2 gate criteria.",
        file=buf,
    )
    print("", file=buf)
    print(f"**Query** ({sarah.name}, role=manager):", file=buf)
    print("> " + QUERY, file=buf)
    print("", file=buf)

    history = result.get("tool_history", [])
    print(f"**Tool calls**: {len(history)}", file=buf)
    print("", file=buf)
    print("| # | Tool | Args (keys) |", file=buf)
    print("|---:|---|---|", file=buf)
    for i, h in enumerate(history, 1):
        print(f"| {i} | `{h['tool']}` | `{sorted(h['args'].keys())}` |", file=buf)
    print("", file=buf)

    print("**Final answer**:", file=buf)
    print("", file=buf)
    print(result.get("final_answer", "<no answer>"), file=buf)
    print("", file=buf)

    ok = bool(history) and bool(result.get("final_answer"))
    print(f"### W2 hard gate: **{'PASS' if ok else 'FAIL'}**", file=buf)
    print("", file=buf)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
