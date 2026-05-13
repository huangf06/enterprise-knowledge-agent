"""HotpotQA full-agent adapter.

Wires EKA's existing 5-node LangGraph loop (plan / tool_select / tool_execute /
reflect / synthesize) to a single-tool registry for the HotpotQA distractor
benchmark. The one tool, `retrieve_passage`, ranks the question's 10
candidate paragraphs via BGE-M3 cosine similarity and returns the top-k.

Design notes:
- The agent's six default enterprise tools are swapped out for the run via a
  context manager on the global registry, then restored. This keeps the rest
  of the agent code (prompts, nodes, graph) untouched.
- Self-Refine critique is disabled for this benchmark because its checks are
  enterprise-specific (citations_ok, cross_source, governance_ok). HotpotQA
  is a short-answer extraction task, not a multi-source briefing.
- The synthesize node returns a long-form citation answer by default; we
  post-process with a short-answer extractor that calls the LLM once more to
  collapse the answer to the canonical HotpotQA short form.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.agent.state import AgentState
from src.eval.hotpotqa_loader import HotpotQAExample
from src.llm.anthropic_client import messages_create
from src.retrieval.embeddings import embed
from src.tools import registry
from src.tools.base import Tool


@dataclass
class RetrieveContext:
    """Per-question state shared between the tool and the runner."""

    example: HotpotQAExample
    paragraph_embeddings: np.ndarray | None = None
    top_k: int = 3


# Module-level handle the registered tool closes over. The runner sets this
# before invoking the agent for each example, so the same tool definition
# works for every question without re-registering on every call.
_ACTIVE: RetrieveContext | None = None


def _set_active(ctx: RetrieveContext | None) -> None:
    global _ACTIVE
    _ACTIVE = ctx


def _format_retrieved(top_indices: list[int], example: HotpotQAExample, scores: list[float]) -> str:
    out_lines: list[str] = []
    for rank, idx in enumerate(top_indices, start=1):
        title, sentences = example.paragraphs[idx]
        body = " ".join(sentences).strip()
        score = scores[idx]
        out_lines.append(
            f"[passage {rank}] title={title!r} (idx={idx}, cosine={score:.3f})\n{body}"
        )
    return "\n\n".join(out_lines)


def _retrieve_run(args: dict[str, Any], ctx: dict[str, Any]) -> str:
    del ctx  # unused; HotpotQA has no RBAC
    active = _ACTIVE
    if active is None:
        return "ERROR: retrieve_passage called without an active HotpotQA context"

    query = str(args.get("query", "")).strip()
    if not query:
        return "ERROR: retrieve_passage requires a non-empty `query` argument"
    requested_k = int(args.get("top_k", active.top_k) or active.top_k)
    top_k = max(1, min(requested_k, len(active.example.paragraphs)))

    if active.paragraph_embeddings is None:
        para_texts = active.example.paragraph_texts()
        active.paragraph_embeddings = np.asarray(embed(para_texts))

    q_vec = np.asarray(embed([query])[0])
    sims = active.paragraph_embeddings @ q_vec  # normalized -> cosine
    ranked = list(np.argsort(sims)[::-1][:top_k])
    return _format_retrieved([int(i) for i in ranked], active.example, sims.tolist())


_RETRIEVE_TOOL = Tool(
    name="retrieve_passage",
    description=(
        "Retrieve up to top_k passages from the question's candidate paragraph pool "
        "via BGE-M3 cosine similarity. Use this tool one or more times with different "
        "queries to gather evidence for a multi-hop question. Each call returns the "
        "top_k passages ranked by similarity to the query."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query. Reformulate the question or focus on the next hop.",
            },
            "top_k": {
                "type": "integer",
                "description": "How many passages to return (default 3, max 10).",
            },
        },
        "required": ["query"],
    },
    run=_retrieve_run,
)


@contextmanager
def _single_tool_registry():
    """Swap the global tool registry to only the retrieve_passage tool, then restore."""
    reg = registry()
    saved = dict(reg._tools)  # type: ignore[attr-defined]
    reg._tools.clear()  # type: ignore[attr-defined]
    try:
        reg.register(_RETRIEVE_TOOL)
        yield reg
    finally:
        reg._tools.clear()  # type: ignore[attr-defined]
        reg._tools.update(saved)  # type: ignore[attr-defined]


_SHORT_ANSWER_PROMPT = """You are extracting the short answer for a HotpotQA-style multi-hop question.

Read the long-form draft answer below and return ONLY the canonical short answer
string (typically 1-5 words; a proper noun, a number, a date, or `yes` / `no`).

Rules:
- Do not explain.
- Do not restate the question.
- Do not include citations or brackets.
- Output exactly the answer string, nothing else.

Question: {question}

Long-form draft:
{draft}

Short answer:"""


def _extract_short_answer(question: str, draft: str) -> str:
    """Collapse the synthesize-node long-form answer to a HotpotQA short answer."""
    prompt = _SHORT_ANSWER_PROMPT.format(question=question, draft=draft.strip() or "(no draft)")
    # max_tokens=1024 because DeepSeek's Anthropic-compatible endpoint emits
    # ThinkingBlock content before the final text; a tight cap (e.g. 64) hits
    # max_tokens inside the thinking trace and returns no text. The text
    # portion is still typically <= 10 tokens.
    resp = messages_create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        node="hotpotqa_short_answer",
    )
    text = " ".join(b.text for b in resp.content if b.type == "text").strip()
    # Strip surrounding quotes / trailing period / "Answer:" prefix if the model added them.
    text = re.sub(r"^answer\s*:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip('"').strip("'").rstrip(".")
    # Keep first line only.
    return text.splitlines()[0].strip() if text else ""


def _initial_state(example: HotpotQAExample, max_iterations: int) -> dict[str, Any]:
    return {
        "query": example.question,
        "user_name": "hotpotqa_eval",
        "user_role": "IC",
        "user_identity": {
            "slack_handle": "",
            "jira_user": "",
            "email": "",
            "github_username": "",
            "calendar_id": "",
            "gdocs_author_id": "",
        },
        "max_iterations": max_iterations,
        "tool_history": [],
        "streaming_events": [],
        "pending_tool": None,
    }


@dataclass
class AgentRunResult:
    qid: str
    question: str
    gold: str
    raw_answer: str
    short_answer: str
    tool_calls: int
    tool_history: list[dict[str, Any]]
    streaming_events: list[dict[str, Any]]
    ok: bool
    error: str | None


def run_agent(
    example: HotpotQAExample,
    max_iterations: int = 5,
    top_k: int = 3,
    recursion_limit: int = 40,
) -> AgentRunResult:
    """Run the EKA agent loop on one HotpotQA example with the single-tool registry."""
    # Ensure the enterprise-specific Self-Refine critique is off for this benchmark.
    os.environ.setdefault("SELF_REFINE_ENABLED", "0")
    # Also keep DSPy compiled prompt off (it is tuned for the enterprise scenarios).
    os.environ.setdefault("USE_COMPILED_PROMPTS", "0")

    from src.agent import app  # local import so env flags above land first

    rctx = RetrieveContext(example=example, top_k=top_k)
    _set_active(rctx)
    state = _initial_state(example, max_iterations)

    try:
        with _single_tool_registry():
            result: AgentState = app().invoke(state, config={"recursion_limit": recursion_limit})
        raw_answer = result.get("final_answer", "") or ""
        tool_history = list(result.get("tool_history", []))
        events = list(result.get("streaming_events", []))
        short = _extract_short_answer(example.question, raw_answer)
        return AgentRunResult(
            qid=example.qid,
            question=example.question,
            gold=example.answer,
            raw_answer=raw_answer,
            short_answer=short,
            tool_calls=len(tool_history),
            tool_history=tool_history,
            streaming_events=events,
            ok=True,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — surface failure to the runner
        return AgentRunResult(
            qid=example.qid,
            question=example.question,
            gold=example.answer,
            raw_answer="",
            short_answer="",
            tool_calls=0,
            tool_history=[],
            streaming_events=[],
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        _set_active(None)


__all__ = ["AgentRunResult", "RetrieveContext", "run_agent"]
