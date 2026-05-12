"""Regex-based PII redaction. Last line of defense before tool results reach the LLM.

W3 redacts the obvious shapes (phone, IBAN, SSN-like 9-digit, payroll figures with currency symbols).
W5 hardens this with NER + a configurable policy.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("[REDACTED:phone]", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
    ("[REDACTED:iban]", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b")),
    ("[REDACTED:ssn]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("[REDACTED:salary]", re.compile(r"[€£$]\s?\d{1,3}(?:[,.]\d{3})+(?:\.\d{2})?")),
]


def redact(text: str) -> str:
    out = text
    for placeholder, pattern in _PATTERNS:
        out = pattern.sub(placeholder, out)
    return out
