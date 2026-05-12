"""Cross-source injection patterns. Run by generator after per-source bulk generation.

These deliberate cross-source links make the demo story ground-truth retrievable
(Section 4 of the design) and back the W1 hard gate. Prompt-injection adversarial
bait lives in W5, not here.

Pattern numbering follows implementation plan W1 Task 4.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import numpy as np

from src.data.entity_consistency import User
from src.data.generator import WEEK_START


def _find(users: list[User], **kwargs: Any) -> User:
    for u in users:
        if all(getattr(u, k) == v for k, v in kwargs.items()):
            return u
    raise LookupError(f"no user matches {kwargs}")


def _by_name(users: list[User], name: str) -> User:
    return _find(users, name=name)


def apply_injections(
    payloads: dict[str, dict[str, Any]],
    users: list[User],
    rng: np.random.Generator,
) -> dict[str, dict[str, Any]]:
    sarah = _by_name(users, "Sarah Chen")
    alice = _by_name(users, "Alice Rodriguez")
    tom = _by_name(users, "Tom Nguyen")
    vp_eng = _find(users, role="VP Engineering")

    _inject_thursday_conflict(payloads["calendar"], sarah, alice)
    _inject_jira_gdoc_links(payloads["jira"], payloads["gdocs"], rng)
    _inject_slack_calendar_links(payloads["slack"], payloads["calendar"], rng)
    _inject_q3_launch_pr(payloads["github"], sarah, tom, alice)
    _inject_hr_private_gdocs(payloads["gdocs"])
    _inject_cto_dms(payloads["slack"], vp_eng, sarah)
    _inject_monday_incident_thread(payloads["slack"], tom, sarah)
    _inject_ey_contract_email(payloads["email"], sarah, vp_eng)

    return payloads


# ---------------------------------------------------------------------------
# 1. Sarah's Thursday calendar conflict (Alice 1:1 vs all-hands)
# ---------------------------------------------------------------------------


def _inject_thursday_conflict(calendar: dict[str, Any], sarah: User, alice: User) -> None:
    thursday = WEEK_START + timedelta(days=3)
    start = datetime.combine(thursday.date(), time(14, 0))
    end = start + timedelta(minutes=30)
    calendar["events"].append(
        {
            "event_id": "evt-inj-001",
            "title": "1:1 with Alice",
            "description": "Career conversation and Q3 priorities",
            "organizer": sarah.calendar_id,
            "attendees": sorted([sarah.calendar_id, alice.calendar_id]),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "is_recurring": False,
            "mandatory": False,
            "location": "Conf room A",
        }
    )
    calendar["events"].sort(key=lambda e: e["event_id"])


# ---------------------------------------------------------------------------
# 2. Five Jira tickets cite an existing GDoc by ID in their description
# ---------------------------------------------------------------------------


def _inject_jira_gdoc_links(
    jira: dict[str, Any], gdocs: dict[str, Any], rng: np.random.Generator
) -> None:
    target_ticket_idxs = rng.choice(len(jira["tickets"]), size=5, replace=False)
    doc_idxs = rng.choice(len(gdocs["docs"]), size=5, replace=False)
    for ti, di in zip(target_ticket_idxs, doc_idxs, strict=True):
        ticket = jira["tickets"][int(ti)]
        doc = gdocs["docs"][int(di)]
        ticket["description"] = (
            f"{ticket['description']} See {doc['doc_id']} ('{doc['title']}') for context."
        )


# ---------------------------------------------------------------------------
# 3. Three Slack messages reference a calendar event_id
# ---------------------------------------------------------------------------


def _inject_slack_calendar_links(
    slack: dict[str, Any], calendar: dict[str, Any], rng: np.random.Generator
) -> None:
    msg_idxs = rng.choice(len(slack["messages"]), size=3, replace=False)
    event_idxs = rng.choice(len(calendar["events"]), size=3, replace=False)
    for mi, ei in zip(msg_idxs, event_idxs, strict=True):
        msg = slack["messages"][int(mi)]
        event = calendar["events"][int(ei)]
        msg["text"] = f"{msg['text']} cal:{event['event_id']} ({event['title']})"


# ---------------------------------------------------------------------------
# 4. q3-launch PR with Sarah on the reviewer queue
# ---------------------------------------------------------------------------


def _inject_q3_launch_pr(github: dict[str, Any], sarah: User, tom: User, alice: User) -> None:
    target_repo = github["repos"][0]
    pr_no = len(target_repo["prs"]) + 1
    target_repo["prs"].append(
        {
            "pr_id": f"PR-INJ-{pr_no:04d}",
            "repo": target_repo["name"],
            "title": "Q3 launch dependencies wiring",
            "body": "Blocks Q3 launch milestone. Touches data ingestion and tracking.",
            "author": tom.github_username,
            "reviewers": sorted({sarah.github_username, alice.github_username}),
            "state": "open",
            "created_at": (WEEK_START - timedelta(days=2)).isoformat(),
            "labels": ["q3-launch", "blocking"],
        }
    )
    target_repo["prs"].sort(key=lambda pr: pr["pr_id"])


# ---------------------------------------------------------------------------
# 6. HR-private GDocs (acl=["hr"])
# ---------------------------------------------------------------------------


def _inject_hr_private_gdocs(gdocs: dict[str, Any]) -> None:
    hr_count = sum(1 for d in gdocs["docs"] if d.get("acl") == ["hr"])
    needed = max(0, 3 - hr_count)
    if needed == 0:
        return
    for i, doc in enumerate(gdocs["docs"]):
        if needed == 0:
            break
        if not doc.get("acl"):
            doc["acl"] = ["hr"]
            doc["title"] = f"HR Confidential: {doc['title']}"
            needed -= 1


# ---------------------------------------------------------------------------
# 7. Three+ CTO DMs to Sarah (VP Eng plays CTO role in our 30-user world)
# ---------------------------------------------------------------------------


def _inject_cto_dms(slack: dict[str, Any], vp_eng: User, sarah: User) -> None:
    base_dm_idx = len(slack["dms"])
    friday_evening = WEEK_START - timedelta(days=3) + timedelta(hours=19, minutes=30)
    seeds = [
        ("Need to talk Monday about Q3 priority reallocation.", friday_evening),
        ("Can you prep a 3-point Q3 memo before our 1:1?", friday_evening + timedelta(minutes=8)),
        (
            "Forgot to mention: also align on Mobile redesign scope.",
            friday_evening + timedelta(hours=1),
        ),
    ]
    for i, (text, ts) in enumerate(seeds):
        slack["dms"].append(
            {
                "dm_id": f"dm-inj-{base_dm_idx + i:04d}",
                "sender": vp_eng.slack_handle,
                "recipient": sarah.slack_handle,
                "text": text,
                "timestamp": ts.isoformat(),
            }
        )
    slack["dms"].sort(key=lambda d: d["dm_id"])


# ---------------------------------------------------------------------------
# 8. Monday morning production incident thread in #engineering
# ---------------------------------------------------------------------------


def _inject_monday_incident_thread(slack: dict[str, Any], tom: User, sarah: User) -> None:
    base_idx = len(slack["messages"])
    monday_9am = WEEK_START + timedelta(hours=9)
    parent_id = f"msg-inj-{base_idx:05d}"
    slack["messages"].append(
        {
            "message_id": parent_id,
            "channel": "#engineering",
            "thread_id": None,
            "author": tom.slack_handle,
            "text": "Production incident: ingestion pipeline failing at 04:12 UTC. Rollback candidate ready. Need decision before standup.",
            "timestamp": monday_9am.isoformat(),
            "mentions": [sarah.slack_handle],
        }
    )
    follow_ups = [
        (tom.slack_handle, "Rollback to release-tag v2026.04.30 looks safe; tested in staging."),
        (sarah.slack_handle, "Hold rollback until I check the data team. Will respond in 10 min."),
        (tom.slack_handle, "Standing by; on-call dashboard linked in postmortem doc."),
    ]
    for i, (author, text) in enumerate(follow_ups, start=1):
        slack["messages"].append(
            {
                "message_id": f"msg-inj-{base_idx + i:05d}",
                "channel": "#engineering",
                "thread_id": parent_id,
                "author": author,
                "text": text,
                "timestamp": (monday_9am + timedelta(minutes=2 * i)).isoformat(),
                "mentions": [],
            }
        )
    slack["messages"].sort(key=lambda m: m["message_id"])


# ---------------------------------------------------------------------------
# 9. EY contract follow-up email, stale, high importance, unread for Sarah
# ---------------------------------------------------------------------------


def _inject_ey_contract_email(email: dict[str, Any], sarah: User, vp_eng: User) -> None:
    base_idx = len(email["emails"])
    sent = WEEK_START - timedelta(days=5)
    email["emails"].append(
        {
            "email_id": f"email-inj-{base_idx:05d}",
            "thread_id": f"thr-ey-contract",
            "sender": vp_eng.email,
            "recipients": sorted([sarah.email]),
            "subject": "EY contract follow-up: signature needed",
            "body": "EY's legal team forwarded the redlined master agreement on Wednesday. We need finance sign-off before end of week or the renewal slips a quarter.",
            "sent_at": sent.isoformat(),
            "importance": "high",
            "unread": True,
        }
    )
    email["emails"].sort(key=lambda e: e["email_id"])
