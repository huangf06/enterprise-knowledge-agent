"""FastAPI + SSE streaming surface for the multi-tool agent."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.agent import app as build_app
from src.agent import semantic_cache
from src.data.entity_consistency import User, load_users
from src.observability.langfuse_tracker import flush, get_client as _langfuse_client

try:
    from langfuse import observe as _observe  # type: ignore
except ImportError:  # pragma: no cover - langfuse missing
    def _observe(*args: Any, **kwargs: Any):  # type: ignore[misc]
        def decorator(fn):
            return fn

        return decorator

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
    user_role: Literal["IC", "manager", "HR", "exec"] = Field(
        default="manager",
        description="Resolved role for governance. Anything outside this enum is rejected at the API boundary.",
    )
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


_ROOT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Enterprise Knowledge Agent</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      max-width:720px;margin:48px auto;padding:0 16px;color:#222;line-height:1.55}
 h1{margin-bottom:.2em} code{background:#f4f4f4;padding:.1em .3em;border-radius:3px}
 pre{background:#f4f4f4;padding:12px;border-radius:4px;overflow-x:auto;font-size:13px}
 a{color:#3949ab} ul{padding-left:1.2em} .note{color:#666;font-size:14px}
</style>
</head>
<body>
<h1>Enterprise Knowledge Agent</h1>
<p>Production-grade open-source cross-source agentic reasoning over six SaaS
surfaces (Slack / Jira / Calendar / GitHub / GDocs / Email) with auditable
governance and a self-authored 30-scenario eval.</p>
<p class="note">All data is synthetic and byte-deterministic from
<code>seed=42</code> &mdash; no real customer data, no PII. Governance is a
pattern demo over synthetic identity, not Okta/Azure AD federation.</p>
<h3>Endpoints</h3>
<ul>
 <li><code>GET /health</code> &mdash; liveness probe</li>
 <li><code>GET /users</code> &mdash; list of 30 synthetic users (name / role / department / office)</li>
 <li><code>POST /query</code> &mdash; SSE stream of agent events
     (<code>plan / tool_select / tool_execute / reflect / synthesize</code>)</li>
</ul>
<h3>Try it</h3>
<pre>curl -N -X POST https://enterprise-knowledge-agent.fly.dev/query \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"What is on my calendar today?","user_name":"Sarah Chen","user_role":"manager"}'</pre>
<h3>Links</h3>
<ul>
 <li>Repo: <a href="https://github.com/huangf06/enterprise-knowledge-agent">github.com/huangf06/enterprise-knowledge-agent</a></li>
 <li>Docs: <a href="https://huangf06.github.io/enterprise-knowledge-agent/">huangf06.github.io/enterprise-knowledge-agent/</a></li>
</ul>
</body></html>
"""


@api.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(content=_ROOT_HTML)


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/users")
def users() -> dict[str, Any]:
    return {
        "synthetic_data": True,
        "note": "Byte-deterministic from seed=42. No real customer data, no PII.",
        "count": 30,
        "users": [
            {"name": u.name, "role": u.role, "department": u.department, "office": u.office}
            for u in load_users()
        ],
    }


@api.post("/query")
@_observe(name="agent_query")
async def query(body: QueryBody) -> EventSourceResponse:
    user = _find_user(body.user_name)
    state = _initial_state(body, user)

    async def event_stream() -> AsyncIterator[dict[str, Any]]:
        # A3 semantic cache short-circuit. Disabled by default; enable in prod via
        # SEMANTIC_CACHE_ENABLED=1.
        hit = semantic_cache.lookup(body.query, body.user_role)
        if hit is not None:
            yield {
                "event": "cache_hit",
                "data": json.dumps({"similarity": hit.similarity, "cached_at": hit.cached_at}),
            }
            yield {"event": "final", "data": json.dumps({"answer": hit.answer}, default=str)}
            yield {"event": "done", "data": "{}"}
            return

        graph = build_app()
        emitted = 0
        final = None
        try:
            async for step in graph.astream(state, config={"recursion_limit": 50}):
                for node_name, node_state in step.items():
                    events = node_state.get("streaming_events") if isinstance(node_state, dict) else None
                    if not events:
                        continue
                    new_events = events[emitted:]
                    emitted = len(events)
                    for ev in new_events:
                        yield {"event": ev.get("type", "event"), "data": json.dumps(ev, default=str)}
                    if isinstance(node_state, dict) and node_state.get("final_answer"):
                        final = node_state["final_answer"]
                        yield {
                            "event": "final",
                            "data": json.dumps({"answer": final}, default=str),
                        }
            yield {"event": "done", "data": "{}"}
        finally:
            if final is not None:
                semantic_cache.put(body.query, body.user_role, final)
            flush()

    return EventSourceResponse(event_stream())
