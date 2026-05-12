"""Gradio reveal-panel UI: chat on the left, agent trace on the right.

W7 deliverable. The right-side reveal panel shows the agent's plan, every tool
call, every RBAC decision, and the audit summary - the design's wow moment for
governance transparency.
"""

from __future__ import annotations

import json
from typing import Iterator

import gradio as gr

from src.agent import app as agent_app
from src.data.entity_consistency import load_users


def _users_by_name() -> dict[str, object]:
    return {u.name: u for u in load_users()}


def _initial_state(query: str, user_name: str, user_role: str) -> dict:
    user = _users_by_name()[user_name]
    return {
        "query": query,
        "user_name": user.name,
        "user_role": user_role,
        "user_identity": {
            "slack_handle": user.slack_handle,
            "jira_user": user.jira_user,
            "email": user.email,
            "github_username": user.github_username,
            "calendar_id": user.calendar_id,
            "gdocs_author_id": user.gdocs_author_id,
        },
        "max_iterations": 5,
        "tool_history": [],
        "streaming_events": [],
        "pending_tool": None,
    }


def _render_event(ev: dict) -> str:
    t = ev.get("type", "event")
    if t == "plan":
        return f"### plan\n```\n{ev.get('text', '')[:600]}\n```"
    if t == "tool_select":
        picked = ev.get("picked")
        if picked:
            return f"**tool_select** → {picked}"
        thought = ev.get("thought", "")[:200]
        return f"**tool_select** → no tool ({thought})"
    if t == "tool_execute":
        ok = "OK" if ev.get("ok") else "ERROR"
        return f"**tool_execute** [{ok}] {ev.get('tool')}({list((ev.get('args') or {}).keys())})"
    if t == "reflect":
        return f"**reflect** verdict: {str(ev.get('verdict', ''))[:120]}"
    if t == "synthesize":
        return "**synthesize** (final answer written)"
    return f"**{t}** {json.dumps(ev, default=str)[:200]}"


def run_query(query: str, user_name: str, user_role: str) -> Iterator[tuple[str, str]]:
    """Yields (chat_message, reveal_panel_html) incrementally as the graph streams."""
    if not query.strip():
        yield ("Please enter a query.", "")
        return
    state = _initial_state(query, user_name, user_role)
    events_md: list[str] = []
    answer = ""
    try:
        for step in agent_app().stream(state, config={"recursion_limit": 40}):
            for _node_name, node_state in step.items():
                if not isinstance(node_state, dict):
                    continue
                evs = node_state.get("streaming_events") or []
                # Show only new events relative to what we've already rendered
                new_evs = evs[len(events_md) :]
                for ev in new_evs:
                    events_md.append(_render_event(ev))
                if node_state.get("final_answer"):
                    answer = node_state["final_answer"]
                yield (answer or "_thinking..._", "\n\n".join(events_md))
    except Exception as exc:  # noqa: BLE001
        events_md.append(f"**error** {exc}")
        yield (answer or f"Agent error: {exc}", "\n\n".join(events_md))


def build() -> gr.Blocks:
    users = _users_by_name()
    user_names = sorted(users.keys())
    with gr.Blocks(title="Enterprise Knowledge Agent") as demo:
        gr.Markdown(
            """# Enterprise Knowledge Agent
Cross-source enterprise knowledge agent over six SaaS surfaces with policy enforcement.
"""
        )
        with gr.Row():
            with gr.Column(scale=3):
                user_dd = gr.Dropdown(user_names, value="Sarah Chen", label="Acting as")
                role_dd = gr.Dropdown(
                    ["IC", "manager", "HR", "exec"], value="manager", label="Role"
                )
                query = gr.Textbox(
                    label="Query",
                    lines=3,
                    value="Give me my Monday morning briefing across Slack, Jira, calendar, and email. What should I focus on first?",
                )
                go = gr.Button("Ask agent", variant="primary")
                answer_md = gr.Markdown("_Answer will appear here once the agent completes._", label="Answer")
            with gr.Column(scale=2):
                gr.Markdown("### Reveal panel — agent trace")
                reveal_md = gr.Markdown("_Trace will stream here._")
        go.click(run_query, [query, user_dd, role_dd], [answer_md, reveal_md])
        gr.Markdown(
            """---
**Repo**: https://github.com/<you>/enterprise-knowledge-agent
"""
        )
    return demo


def main() -> None:
    build().launch(server_name="0.0.0.0", server_port=7860, show_error=True, theme="soft")


if __name__ == "__main__":
    main()
