"""FastAPI + SSE streaming surface for the multi-tool agent."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.agent import app as build_app
from src.data.entity_consistency import User, load_users

api = FastAPI(title="Enterprise Knowledge Agent", version="0.1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryBody(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_name: str = Field(min_length=1, description="Display name, must match users_seed.yaml")
    user_role: str = Field(default="manager", description="IC | manager | HR")
    max_iterations: int = Field(default=6, ge=1, le=10)


def _find_user(name: str) -> User:
    for u in load_users():
        if u.name == name:
            return u
    raise HTTPException(status_code=404, detail=f"User not found: {name}")


def _initial_state(body: QueryBody, user: User) -> dict[str, Any]:
    return {
        "query": body.query,
        "user_name": user.name,
        "user_role": body.user_role,
        "user_identity": {
            "slack_handle": user.slack_handle,
            "jira_user": user.jira_user,
            "email": user.email,
            "github_username": user.github_username,
            "calendar_id": user.calendar_id,
        },
        "max_iterations": body.max_iterations,
        "tool_history": [],
        "streaming_events": [],
        "pending_tool": None,
    }


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/users")
def users() -> list[dict[str, str]]:
    return [
        {"name": u.name, "role": u.role, "department": u.department, "office": u.office}
        for u in load_users()
    ]


@api.post("/query")
async def query(body: QueryBody) -> EventSourceResponse:
    user = _find_user(body.user_name)
    state = _initial_state(body, user)

    async def event_stream() -> AsyncIterator[dict[str, Any]]:
        graph = build_app()
        emitted = 0
        async for step in graph.astream(state, config={"recursion_limit": 50}):
            for node_name, node_state in step.items():
                events = node_state.get("streaming_events") if isinstance(node_state, dict) else None
                if not events:
                    continue
                # Only emit the events new since last emission
                new_events = events[emitted:]
                emitted = len(events)
                for ev in new_events:
                    yield {"event": ev.get("type", "event"), "data": json.dumps(ev, default=str)}
                if isinstance(node_state, dict) and node_state.get("final_answer"):
                    yield {
                        "event": "final",
                        "data": json.dumps({"answer": node_state["final_answer"]}, default=str),
                    }
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_stream())
