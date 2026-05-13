"""Frontier #7 Counterfactual robustness scaffold (Sprint 6).

Three perturbation variants per v4.1 plan, applied at tool-result level so the
synthetic data on disk is not modified (seed=42 reproducibility preserved):

  - entity_swap (R3): non-protagonist entity rename, e.g. 'EY contract' ->
    'PwC contract'. Protagonist names (Sarah Chen et al.) are NOT swapped to
    avoid retesting the injection guard on a name it was not tuned for.
  - noise_injection (P10): wrap each tool result with a small amount of
    plausible but irrelevant chatter. Tests whether the agent gets distracted.
  - doc_deletion (P11): drop the most-cited document from the tool result set.
    Tests graceful degradation when the canonical source disappears.

The runner reuses the existing src/eval/runner.py path; we just intercept the
tool execution to apply perturbations before the agent sees results. NOT wired
into the live agent flow here - it's a separate eval mode.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

# R3-compliant non-protagonist entity swaps.
# Keep the LHS specific so we don't accidentally rename protagonist references
# ("Sarah" not in keys, only third-party org names).
ENTITY_SWAPS = {
    r"\bEY\b": "PwC",
    r"\bEY contract\b": "PwC contract",
    r"\bAcme Corp\b": "Globex Inc",
    r"\bAlpha Pilot\b": "Beta Pilot",
    r"\bQ3 launch\b": "Q4 launch",
}

NOISE_LINES = [
    "Internal newsletter reminder: optional all-hands at 5pm Friday for engagement survey results.",
    "Reminder: building access badge audit next Tuesday; new badges available at security desk.",
    "Office wellness program: 15-minute walks recommended; sign-up sheet on intranet.",
    "Compliance refresher: quarterly conflict-of-interest disclosure due end of month.",
]


def apply_entity_swap(text: str) -> str:
    out = text
    for pattern, repl in ENTITY_SWAPS.items():
        out = re.sub(pattern, repl, out)
    return out


def apply_noise_injection(text: str, n_lines: int = 2) -> str:
    chosen = NOISE_LINES[:n_lines]
    return text + "\n\n[Background notes]\n" + "\n".join(chosen)


def apply_doc_deletion(text: str, drop_pattern: str | None = None) -> str:
    """Drop the canonical-doc paragraph. Heuristic: remove the line with the most
    [source:id] citations or the first paragraph if no citation marker found.
    """
    paragraphs = re.split(r"\n\n+", text)
    if not paragraphs:
        return text
    if drop_pattern:
        kept = [p for p in paragraphs if drop_pattern.lower() not in p.lower()]
        return "\n\n".join(kept) if kept else "(canonical doc deleted)"
    # Heuristic: most-cited paragraph
    best_idx, best_count = 0, -1
    for i, p in enumerate(paragraphs):
        c = len(re.findall(r"\[[a-z]+:[A-Za-z0-9_./-]+\]", p))
        if c > best_count:
            best_count, best_idx = c, i
    kept = [p for i, p in enumerate(paragraphs) if i != best_idx]
    return "\n\n".join(kept) if kept else "(canonical doc deleted)"


def perturb_tool_history(
    tool_history: list[dict[str, Any]],
    mode: str = "entity_swap",
) -> list[dict[str, Any]]:
    """Apply the named perturbation to every tool result. Returns a copy."""
    out = []
    for entry in tool_history:
        new_entry = deepcopy(entry)
        result = new_entry.get("result", "")
        if not isinstance(result, str):
            new_entry["result"] = result
            out.append(new_entry)
            continue
        if mode == "entity_swap":
            new_entry["result"] = apply_entity_swap(result)
        elif mode == "noise_injection":
            new_entry["result"] = apply_noise_injection(result)
        elif mode == "doc_deletion":
            new_entry["result"] = apply_doc_deletion(result)
        else:
            raise ValueError(f"unknown perturbation mode: {mode}")
        out.append(new_entry)
    return out


__all__ = [
    "apply_entity_swap",
    "apply_noise_injection",
    "apply_doc_deletion",
    "perturb_tool_history",
    "ENTITY_SWAPS",
]
