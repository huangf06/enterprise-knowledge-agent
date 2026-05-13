"""Langfuse v4 tracing wrapper.

Langfuse v4 is OTel-based: observations form a tree, the root is the trace.
We expose two operations:

  - `record_generation(...)`: emits a generation observation under whatever
    parent context is currently active. If no parent (batch eval), it becomes
    a standalone trace.
  - `flush()`: blocks until buffered events are uploaded.

The API handler opens a parent trace by wrapping with `@observe` from langfuse
directly; we do not add our own trace wrapper to keep the integration thin.

Conditional activation: if LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY are absent,
all calls are silent no-ops. Tests + local dev work without Langfuse credentials.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_client():
    """Return a Langfuse client or None if keys are missing."""
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_BASE_URL") or os.environ.get(
        "LANGFUSE_HOST", "https://cloud.langfuse.com"
    )
    if not (public and secret):
        return None
    try:
        from langfuse import Langfuse  # type: ignore
    except ImportError:
        return None
    try:
        return Langfuse(public_key=public, secret_key=secret, host=host)
    except Exception:
        return None


def record_generation(
    node: str,
    model: str,
    input_messages: list[dict[str, Any]],
    output_text: str,
    usage: dict[str, int] | None = None,
) -> None:
    """Emit a generation observation under the current trace context (if any)."""
    client = get_client()
    if client is None:
        return
    try:
        with client.start_as_current_observation(name=node, as_type="generation") as gen:
            gen.update(
                input=input_messages,
                output=output_text,
                model=model,
                usage_details=usage or {},
            )
    except Exception:
        # Observability MUST NOT break the agent run.
        pass


def flush() -> None:
    """Block-flush pending Langfuse events. Call at API request boundary."""
    client = get_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass


# Backward-compat stubs (legacy callers in api/main.py) - now no-ops since the
# parent trace is created by langfuse.observe on the API handler.
def start_query_trace(query: str, user_name: str, user_role: str) -> Any:
    return None


def end_query_trace(final_answer: str | None = None) -> None:
    pass
