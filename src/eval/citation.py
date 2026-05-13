"""F4 algorithmic citation groundedness.

Pure-Python metric for citation quality. Replaces the LLM-judged
"answer_correctness" partial-credit on citations with three deterministic
scores per (answer, tool_history) pair:

  - well_formedness: fraction of citations that match the canonical
    [source:id] pattern. Anything that doesn't match (e.g. naked URLs or
    [source-only] forms) is counted against well-formedness.
  - source_coverage: of cited sources, fraction actually called by the agent.
    Catches hallucinated sources (citing Slack when the agent never queried
    Slack).
  - id_grounded: of cited (source, id) pairs, fraction where the id
    substring appears in the corresponding tool's result text. Catches
    invented IDs.

These metrics never call an LLM. They run on the post-eval JSON rows that
include `answer` + `tool_history` (full tool history is added by runner in F4).
"""

from __future__ import annotations

import re
from typing import Any

# Match [source:id]; source is lowercase letters; id can have alnum/_/- (and dots)
_CITE_RE = re.compile(r"\[([a-z]+):([A-Za-z0-9_./-]+)\]")
# Broader pattern that catches malformed citations like [source] or [text without colon]
_ANY_BRACKET = re.compile(r"\[([^\[\]\n]{1,120})\]")

# Source-tag → tool-name mapping. Agents may cite "cal" or "calendar"; both map
# to calendar_query. Keep this list explicit so spurious tags fail source_coverage.
SOURCE_TO_TOOL = {
    "slack": "slack_query",
    "jira": "jira_query",
    "cal": "calendar_query",
    "calendar": "calendar_query",
    "gh": "github_pr_review",
    "github": "github_pr_review",
    "gdoc": "gdocs_search",
    "gdocs": "gdocs_search",
    "email": "email_query",
}


def parse_citations(answer: str) -> list[tuple[str, str]]:
    """Return all well-formed (source, id) citation pairs from the answer."""
    return [(m.group(1).lower(), m.group(2)) for m in _CITE_RE.finditer(answer)]


def parse_bracket_tokens(answer: str) -> list[str]:
    """Return all bracketed tokens regardless of format. Used for well_formedness denom."""
    return [m.group(1) for m in _ANY_BRACKET.finditer(answer)]


def _result_text(entry: dict[str, Any]) -> str:
    """Extract the result string from a tool_history entry."""
    r = entry.get("result", "")
    if isinstance(r, str):
        return r
    return str(r)


def citation_groundedness(answer: str, tool_history: list[dict[str, Any]]) -> dict[str, float | int]:
    """Compute the three citation scores plus raw counts."""
    pairs = parse_citations(answer)
    brackets = parse_bracket_tokens(answer)

    n_brackets = len(brackets)
    n_pairs = len(pairs)
    if n_brackets == 0:
        well_formed = 1.0  # vacuous: no brackets at all, nothing malformed
    else:
        well_formed = n_pairs / n_brackets

    tools_actually_called = {t.get("tool", "") for t in tool_history}
    text_by_tool: dict[str, str] = {}
    for entry in tool_history:
        tool = entry.get("tool", "")
        text_by_tool.setdefault(tool, "")
        text_by_tool[tool] += " " + _result_text(entry)

    if not pairs:
        return {
            "well_formedness": round(well_formed, 4),
            "source_coverage": 1.0,
            "id_grounded": 1.0,
            "n_citations": 0,
            "n_brackets": n_brackets,
        }

    src_hits = 0
    id_hits = 0
    for source, cite_id in pairs:
        expected_tool = SOURCE_TO_TOOL.get(source)
        if expected_tool is None:
            continue  # unknown source tag, fail both counts
        if expected_tool in tools_actually_called:
            src_hits += 1
        text = text_by_tool.get(expected_tool, "")
        if cite_id in text:
            id_hits += 1

    return {
        "well_formedness": round(well_formed, 4),
        "source_coverage": round(src_hits / n_pairs, 4),
        "id_grounded": round(id_hits / n_pairs, 4),
        "n_citations": n_pairs,
        "n_brackets": n_brackets,
    }


__all__ = ["citation_groundedness", "parse_citations", "SOURCE_TO_TOOL"]
