"""Google Docs search tool with cross-source ACL enforcement."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.governance.audit import audit_event
from src.governance.pii_redact import redact
from src.governance.rbac import check_resource
from src.tools.base import Tool, ToolContext, load_source, registry, validate_args


class GDocsArgs(BaseModel):
    keyword: str | None = Field(default=None, description="Substring match on title or content")
    owner: str | None = Field(default=None, description="Restrict to this gdocs_author_id")
    shared_with: str | None = Field(default=None, description="Docs shared with this gdocs_author_id")
    max_items: int = 10


@lru_cache(maxsize=1)
def _gd_data() -> dict[str, Any]:
    return load_source("gdocs")


def _run(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, GDocsArgs)
    role = ctx.get("role", "IC")
    user_gid = ctx.get("gdocs_author_id")
    docs = _gd_data()["docs"]

    visible = []
    denied: list[str] = []
    for d in docs:
        if parsed.keyword:
            hay = (d["title"] + "\n" + d["content"]).lower()
            if parsed.keyword.lower() not in hay:
                continue
        if parsed.owner and d["owner"] != parsed.owner:
            continue
        if parsed.shared_with and parsed.shared_with not in d.get("shared_with", []):
            continue
        acl = d.get("acl") or []
        rbac_ok = True
        for tag in acl:
            decision = check_resource("gdocs_acl", tag, role)
            if not decision.allow:
                rbac_ok = False
                denied.append(d["doc_id"])
                audit_event(
                    "rbac.deny",
                    {"source": "gdocs", "resource": d["doc_id"], "acl": acl, "role": role, "reason": decision.reason},
                )
                break
        if not rbac_ok:
            continue
        if acl and user_gid and d["owner"] != user_gid and user_gid not in d.get("shared_with", []):
            denied.append(d["doc_id"])
            continue
        visible.append(d)

    visible.sort(key=lambda d: d["doc_id"])
    total = len(visible)
    shown = visible[: parsed.max_items]
    lines = [
        f"gdocs_search(keyword={parsed.keyword}, owner={parsed.owner}): "
        f"{total} visible docs"
    ]
    if denied:
        lines.append(f"  RBAC denied: {sorted(set(denied))} (role={role})")
    for d in shown:
        acl_tag = f" acl={d['acl']}" if d.get("acl") else ""
        preview = d["content"][:140].replace("\n", " ")
        lines.append(f"  [{d['doc_id']}]{acl_tag} {d['title']} (owner={d['owner']}): {preview}")
    if total > len(shown):
        lines.append(f"  ... {total - len(shown)} more not shown")
    return redact("\n".join(lines))


TOOL = Tool(
    name="gdocs_search",
    description=(
        "Search the company Google Docs by keyword, owner, or sharing scope. Enforces ACL: "
        "docs marked acl=['hr'] or acl=['leadership'] are denied to roles without permission."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string"},
            "owner": {"type": "string"},
            "shared_with": {"type": "string"},
            "max_items": {"type": "integer"},
        },
    },
    run=_run,
)

registry().register(TOOL)
