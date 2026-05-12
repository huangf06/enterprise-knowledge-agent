"""Three tools for the Demo 2 HR Helpdesk single-source case study.

Demonstrates module reuse: governance (RBAC + audit + PII redact) and the tool
base class are 100% reused; only the data and the per-tool logic are new.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.governance.audit import audit_event
from src.governance.pii_redact import redact
from src.tools.base import Tool, ToolContext, validate_args

CORPUS_PATH = Path(__file__).resolve().parents[3] / "data" / "hr_corpus" / "handbook.json"


@lru_cache(maxsize=1)
def _corpus() -> dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text())


class HRPolicyArgs(BaseModel):
    keyword: str = Field(min_length=1, description="Substring to match policy titles or content")
    max_items: int = 5


class EmployeeDataArgs(BaseModel):
    employee_id: str


class EscalationArgs(BaseModel):
    employee_id: str
    case_summary: str


def _hr_policy_search(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, HRPolicyArgs)
    policies = _corpus()["policies"]
    matched = [
        p
        for p in policies
        if parsed.keyword.lower() in p["title"].lower() or parsed.keyword.lower() in p["content"].lower()
    ]
    matched = matched[: parsed.max_items]
    lines = [f"hr_policy_search(keyword={parsed.keyword}): {len(matched)} policies"]
    for p in matched:
        lines.append(f"  [{p['id']}] {p['title']}: {p['content']}")
    return redact("\n".join(lines))


def _employee_self_data_query(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, EmployeeDataArgs)
    # Critical RBAC: a user may only query their OWN employee data.
    caller_user_id = ctx.get("user_id") or ctx.get("user_name", "")
    role = ctx.get("role", "IC")
    if parsed.employee_id != caller_user_id and role not in ("HR", "exec"):
        audit_event(
            "rbac.deny",
            {"source": "hr_helpdesk", "resource": parsed.employee_id, "role": role, "reason": "employee_self_only"},
        )
        return f"RBAC denied: employee_self_data_query(employee_id={parsed.employee_id}) — role={role} cannot query other employees."
    employees = _corpus()["employees"]
    match = next((e for e in employees if e["employee_id"] == parsed.employee_id), None)
    if match is None:
        return f"employee_self_data_query: no employee {parsed.employee_id} in corpus"
    return redact(f"employee_self_data_query({parsed.employee_id}):\n{json.dumps(match, indent=2)}")


def _escalation_routing(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, EscalationArgs)
    employees = _corpus()["employees"]
    match = next((e for e in employees if e["employee_id"] == parsed.employee_id), None)
    if match is None:
        return f"escalation_routing: no employee {parsed.employee_id}"
    audit_event(
        "hr.escalation",
        {"employee_id": parsed.employee_id, "summary": parsed.case_summary[:200]},
    )
    return (
        f"escalation_routing: case for {match['name']} escalated. "
        f"Path: direct manager ({match['manager']}, {match['manager_email']}) -> HRBP -> Head of HR. "
        "An anonymous-track copy may also be filed at hr-anonymous@acme.nl."
    )


HR_POLICY_TOOL = Tool(
    name="hr_policy_search",
    description="Search the company HR handbook for policies (paternity, vacation, expense, etc.).",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string"},
            "max_items": {"type": "integer"},
        },
        "required": ["keyword"],
    },
    run=_hr_policy_search,
)

EMPLOYEE_DATA_TOOL = Tool(
    name="employee_self_data_query",
    description="Query an employee's own data (vacation balance, paternity status). RBAC enforces self-only access for non-HR roles.",
    input_schema={
        "type": "object",
        "properties": {"employee_id": {"type": "string"}},
        "required": ["employee_id"],
    },
    run=_employee_self_data_query,
)

ESCALATION_TOOL = Tool(
    name="escalation_routing",
    description="Route an unresolved 1-1 / HR concern through the escalation path. Logs to the audit trail.",
    input_schema={
        "type": "object",
        "properties": {
            "employee_id": {"type": "string"},
            "case_summary": {"type": "string"},
        },
        "required": ["employee_id", "case_summary"],
    },
    run=_escalation_routing,
)


def hr_helpdesk_tools() -> list[Tool]:
    """Return the 3 Demo 2 tools. Caller registers them in a separate ToolRegistry."""
    return [HR_POLICY_TOOL, EMPLOYEE_DATA_TOOL, ESCALATION_TOOL]
