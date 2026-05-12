"""Run a scenario through the agent, then score with the judge."""

from __future__ import annotations

import time
from typing import Any

from src.agent import app
from src.data.entity_consistency import load_users
from src.eval.judge import judge
from src.eval.scenarios import Scenario


def _user_state(scenario: Scenario) -> dict[str, Any]:
    users = {u.name: u for u in load_users()}
    user = users[scenario.user_name]
    return {
        "query": scenario.question,
        "user_name": user.name,
        "user_role": scenario.user_role,
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


def run_scenario(scenario: Scenario) -> dict[str, Any]:
    state = _user_state(scenario)
    started = time.time()
    try:
        result = app().invoke(state, config={"recursion_limit": 40})
        answer = result.get("final_answer", "")
        tool_history = result.get("tool_history", [])
        ok = True
    except Exception as exc:  # noqa: BLE001
        answer = f"AGENT ERROR: {exc}"
        tool_history = []
        ok = False
    elapsed = time.time() - started

    actual_sources = sorted({t["tool"] for t in tool_history})
    scores = judge(scenario, answer, actual_sources) if ok else {
        "answer_correctness": 0.0,
        "completeness": 0.0,
        "tool_selection_quality": 0.0,
        "governance_compliance": 1.0,  # no leak if agent errored
        "action_recommend_quality": 0.0,
    }

    return {
        "scenario_id": scenario.id,
        "category": scenario.category,
        "difficulty": scenario.difficulty,
        "ok": ok,
        "answer": answer,
        "tool_calls": len(tool_history),
        "tools_used": actual_sources,
        "scores": scores,
        "elapsed_s": round(elapsed, 2),
    }
