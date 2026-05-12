#!/usr/bin/env python3
"""Verify W1 hard gate invariants on a generated synthetic dataset.

Prints:
- Entity overlap matrix (30 users by 6 sources, presence counts)
- Nine cross-source injection patterns checklist

Exit code 0 if all invariants pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.data.entity_consistency import load_users

SOURCES = ("slack", "jira", "calendar", "github", "gdocs", "email")


def _load(data_dir: Path) -> dict[str, dict]:
    return {s: json.loads((data_dir / s / f"{s}.json").read_text()) for s in SOURCES}


def overlap_matrix(payloads: dict[str, dict], users) -> list[tuple[str, dict[str, int]]]:
    """Return per-user count of mentions per source. Counts are recall signals, not strict."""
    rows = []
    for u in users:
        counts = {
            "slack": sum(
                1
                for m in payloads["slack"]["messages"]
                if m["author"] == u.slack_handle or u.slack_handle in m.get("mentions", [])
            )
            + sum(
                1
                for d in payloads["slack"]["dms"]
                if u.slack_handle in (d["sender"], d["recipient"])
            )
            + sum(1 for c in payloads["slack"]["channels"] if u.slack_handle in c["members"]),
            "jira": sum(
                1
                for t in payloads["jira"]["tickets"]
                if u.jira_user in (t["assignee"], t["reporter"])
            ),
            "calendar": sum(
                1
                for e in payloads["calendar"]["events"]
                if u.calendar_id == e["organizer"] or u.calendar_id in e["attendees"]
            ),
            "github": sum(
                1
                for r in payloads["github"]["repos"]
                for pr in r["prs"]
                if u.github_username == pr["author"] or u.github_username in pr["reviewers"]
            ),
            "gdocs": sum(
                1
                for d in payloads["gdocs"]["docs"]
                if u.gdocs_author_id == d["owner"] or u.gdocs_author_id in d["shared_with"]
            ),
            "email": sum(
                1
                for e in payloads["email"]["emails"]
                if u.email == e["sender"] or u.email in e["recipients"]
            ),
        }
        rows.append((u.name, counts))
    return rows


def check_injections(payloads: dict[str, dict], users) -> list[tuple[str, bool, str]]:
    sarah = next(u for u in users if u.name == "Sarah Chen")
    vp_eng = next(u for u in users if u.role == "VP Engineering")

    checks: list[tuple[str, bool, str]] = []

    # 1. Sarah Thursday conflict
    thursday_events = [
        e
        for e in payloads["calendar"]["events"]
        if sarah.email in e["attendees"] and datetime.fromisoformat(e["start"]).weekday() == 3
    ]
    conflict = False
    for i, a in enumerate(thursday_events):
        for b in thursday_events[i + 1 :]:
            if (
                datetime.fromisoformat(a["start"]) < datetime.fromisoformat(b["end"])
                and datetime.fromisoformat(b["start"]) < datetime.fromisoformat(a["end"])
            ):
                conflict = True
                break
        if conflict:
            break
    checks.append(("1. Sarah Thursday conflict (Alice 1:1 vs all-hands)", conflict, ""))

    # 2. Jira-GDoc links
    gdoc_ids = {d["doc_id"] for d in payloads["gdocs"]["docs"]}
    linked = sum(
        1 for t in payloads["jira"]["tickets"] if any(g in t["description"] for g in gdoc_ids)
    )
    checks.append(("2. >=5 Jira tickets cite a GDoc id", linked >= 5, f"count={linked}"))

    # 3. Slack-Calendar references
    event_ids = {e["event_id"] for e in payloads["calendar"]["events"]}
    sc = sum(1 for m in payloads["slack"]["messages"] if any(eid in m["text"] for eid in event_ids))
    checks.append(("3. >=3 Slack messages reference a calendar event_id", sc >= 3, f"count={sc}"))

    # 4. q3-launch PR blocking Sarah
    blocking = [
        pr
        for r in payloads["github"]["repos"]
        for pr in r["prs"]
        if sarah.github_username in pr["reviewers"] and "q3-launch" in pr.get("labels", [])
    ]
    checks.append(("4. >=1 q3-launch PR blocking Sarah's review", len(blocking) >= 1, ""))

    # 5. Leadership channel excludes Sarah, has 3-5 members
    leadership = next(c for c in payloads["slack"]["channels"] if c["name"] == "#leadership")
    ok5 = sarah.slack_handle not in leadership["members"] and 3 <= len(leadership["members"]) <= 5
    checks.append(("5. #leadership excludes Sarah, 3-5 members", ok5, f"members={leadership['members']}"))

    # 6. HR-private GDocs
    hr_docs = [d for d in payloads["gdocs"]["docs"] if d.get("acl") == ["hr"]]
    checks.append(("6. >=3 HR-private GDocs (acl=['hr'])", len(hr_docs) >= 3, f"count={len(hr_docs)}"))

    # 7. CTO/VP-Eng DMs to Sarah
    dms = [
        d
        for d in payloads["slack"]["dms"]
        if d["sender"] == vp_eng.slack_handle and d["recipient"] == sarah.slack_handle
    ]
    checks.append(("7. >=3 VP-Eng DMs to Sarah", len(dms) >= 3, f"count={len(dms)}"))

    # 8. Monday production incident thread
    incidents = [
        m
        for m in payloads["slack"]["messages"]
        if "production incident" in m["text"].lower()
        and m["channel"] == "#engineering"
        and datetime.fromisoformat(m["timestamp"]).weekday() == 0
    ]
    ok8 = False
    if incidents:
        parent = incidents[0]
        replies = [m for m in payloads["slack"]["messages"] if m.get("thread_id") == parent["message_id"]]
        ok8 = len(replies) >= 2
    checks.append(("8. Monday production incident thread w/ replies", ok8, ""))

    # 9. EY contract follow-up email
    candidates = [
        e
        for e in payloads["email"]["emails"]
        if "ey contract" in e["subject"].lower() and sarah.email in e["recipients"]
    ]
    ok9 = False
    if candidates:
        e = candidates[0]
        age = datetime(2026, 5, 11) - datetime.fromisoformat(e["sent_at"])
        ok9 = age >= timedelta(days=4) and e["importance"] == "high" and e["unread"] is True
    checks.append(("9. EY contract follow-up email stale + high priority", ok9, ""))

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: data dir {args.data} not found. Run scripts/generate_data.py first.")
        return 1

    payloads = _load(args.data)
    users = load_users()

    print("=" * 72)
    print("W1 hard gate verification")
    print(f"data dir: {args.data}")
    print("=" * 72)

    print()
    print("Entity overlap matrix (presence count per user per source)")
    print("-" * 72)
    header = f"{'User':<22}" + "".join(f"{s:>10}" for s in SOURCES)
    print(header)
    rows = overlap_matrix(payloads, users)
    full_overlap = True
    for name, counts in rows:
        line = f"{name:<22}" + "".join(f"{counts[s]:>10}" for s in SOURCES)
        print(line)
        if any(counts[s] == 0 for s in SOURCES):
            full_overlap = False
    print("-" * 72)
    print(f"Full 30/30 overlap across all 6 sources: {'PASS' if full_overlap else 'FAIL'}")

    print()
    print("Injection patterns checklist")
    print("-" * 72)
    checks = check_injections(payloads, users)
    all_pass = True
    for label, ok, detail in checks:
        tag = "PASS" if ok else "FAIL"
        suffix = f"  ({detail})" if detail else ""
        print(f"  [{tag}] {label}{suffix}")
        if not ok:
            all_pass = False

    print()
    print("=" * 72)
    overall = full_overlap and all_pass
    print(f"W1 gate: {'PASS' if overall else 'FAIL'}")
    print("=" * 72)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
