"""Cross-source RBAC policy engine.

This is a *policy decision* layer on synthetic identity. It is not Okta / Azure
AD federation (deliberately scoped to v1.5 per design Section 3.3).

Public surface:
    - effective_role(user) -> role string (resolves exec from manager_id == null)
    - check_resource(resource_type, identifier, role) -> Decision(allow, reason)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.data.entity_consistency import User

POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "rbac_policies.yaml"


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str


@lru_cache(maxsize=1)
def _policies() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text())


def effective_role(user: User) -> str:
    """Promote heads (manager_id null) to the 'exec' tier."""
    if user.manager_id is None and user.department != "HR":
        return "exec"
    if user.department == "HR":
        return "HR"
    if "Manager" in user.role or "Lead" in user.role:
        return "manager"
    return "IC"


def check_resource(resource_type: str, identifier: str, role: str) -> Decision:
    """Return Decision(allow=True/False, reason=string)."""
    roles = _policies().get("roles", {})
    if role not in roles:
        return Decision(False, f"unknown role: {role}")
    grants = roles[role].get("grants", {})
    rule = grants.get(resource_type)
    if rule is None:
        return Decision(True, "no rule defined for resource type")
    deny_list = rule.get("deny") or []
    if identifier in deny_list:
        return Decision(False, f"role={role} denies {resource_type}={identifier}")
    return Decision(True, f"role={role} permits {resource_type}={identifier}")


def filter_allowed(resource_type: str, identifiers: list[str], role: str) -> tuple[list[str], list[str]]:
    """Split identifiers into (allowed, denied)."""
    allowed, denied = [], []
    for ident in identifiers:
        if check_resource(resource_type, ident, role).allow:
            allowed.append(ident)
        else:
            denied.append(ident)
    return allowed, denied
