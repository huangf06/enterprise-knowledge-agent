"""Deterministic cross-source synthetic data generator.

Decision (design Section 13 Q2): Faker + numpy templates, not LLM-generated.
Reasons: byte-equal reproducibility from a single seed, zero cost, fast iteration,
sufficient realism for eval scenarios that test agent behavior rather than data prose.

Output layout, one JSON file per source under output_dir/{source}/{source}.json.
Determinism contract: same seed + same days always produces byte-equal files.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from faker import Faker

from src.data.entity_consistency import User, load_users

# Anchor week, Monday at 00:00 UTC, deliberately frozen so calendar events are
# reproducible across machines regardless of "today".
WEEK_START = datetime(2026, 5, 4, 0, 0, 0)

JIRA_PROJECTS = ["PLAT", "MOBILE", "BACKEND", "FRONT", "INFRA"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
PRIORITY_WEIGHTS = [0.1, 0.25, 0.45, 0.2]
STATUSES = ["Open", "In Progress", "Blocked", "In Review", "Done"]
STATUS_WEIGHTS = [0.25, 0.3, 0.1, 0.15, 0.2]


def _seeded_faker(seed: int) -> Faker:
    f = Faker()
    f.seed_instance(int(seed))
    return f


def _spawn(parent: np.random.SeedSequence, n: int) -> list[np.random.Generator]:
    return [np.random.default_rng(s) for s in parent.spawn(n)]


def _faker_seeds(parent: np.random.SeedSequence, n: int) -> list[int]:
    return [int(s.generate_state(1, dtype=np.uint32)[0]) for s in parent.spawn(n)]


def _by_dept(users: list[User]) -> dict[str, list[User]]:
    out: dict[str, list[User]] = {}
    for u in users:
        out.setdefault(u.department, []).append(u)
    return out


def _eng_users(users: list[User]) -> list[User]:
    return [u for u in users if u.department == "Engineering"]


def _heads(users: list[User]) -> list[User]:
    return [u for u in users if u.manager_id is None]


def _dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False, default=str)
    path.write_text(serialized + "\n")


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------


def _build_channel_list(users: list[User], rng: np.random.Generator) -> list[dict[str, Any]]:
    by_dept = _by_dept(users)
    heads = _heads(users)
    eng_managers = [u for u in _eng_users(users) if u.role == "Engineering Manager"]

    channels: list[dict[str, Any]] = [
        {
            "name": "#general",
            "members": sorted(u.slack_handle for u in users),
            "is_private": False,
            "description": "Company-wide announcements",
        },
        {
            "name": "#engineering",
            "members": sorted(u.slack_handle for u in _eng_users(users)),
            "is_private": False,
            "description": "Engineering organization",
        },
        {
            "name": "#product",
            "members": sorted(u.slack_handle for u in by_dept["Product"] + heads),
            "is_private": False,
            "description": "Product roadmap and launches",
        },
        {
            "name": "#design-review",
            "members": sorted(
                {u.slack_handle for u in by_dept["Design"] + by_dept["Product"] + eng_managers}
            ),
            "is_private": False,
            "description": "Design reviews and critique",
        },
        {
            "name": "#leadership",
            "members": sorted(u.slack_handle for u in heads),
            "is_private": True,
            "description": "Executive leadership only",
        },
    ]

    for dept, dept_users in sorted(by_dept.items()):
        channels.append(
            {
                "name": f"#team-{dept.lower()}",
                "members": sorted(u.slack_handle for u in dept_users),
                "is_private": False,
                "description": f"{dept} team room",
            }
        )

    project_names = [
        "q3-launch",
        "onboarding-revamp",
        "mobile-redesign",
        "infra-migration",
        "data-platform",
        "security-audit",
        "compliance",
        "growth-funnel",
        "billing-v2",
        "i18n",
    ]
    for name in project_names:
        member_pool = _eng_users(users) + by_dept["Product"] + by_dept["Design"]
        size = int(rng.integers(5, 12))
        picked = rng.choice(len(member_pool), size=size, replace=False)
        members = sorted({member_pool[int(i)].slack_handle for i in picked})
        channels.append(
            {
                "name": f"#proj-{name}",
                "members": members,
                "is_private": False,
                "description": f"Project {name}",
            }
        )

    topic_pool = [
        "random",
        "coffee-chat",
        "amsterdam",
        "berlin",
        "remote-workers",
        "books",
        "pets",
        "travel",
        "music",
        "games",
        "wellness",
        "food",
        "fitness",
        "movies",
        "ai-news",
        "career-talk",
        "side-projects",
        "fun",
        "learning",
        "kudos",
        "hiring",
        "ops",
        "incidents",
        "support",
        "feedback",
        "celebrations",
        "questions",
        "ideas",
        "memes",
        "recap",
    ]
    for topic in topic_pool[: 50 - len(channels)]:
        size = int(rng.integers(4, 18))
        picked = rng.choice(len(users), size=size, replace=False)
        members = sorted({users[int(i)].slack_handle for i in picked})
        channels.append(
            {
                "name": f"#{topic}",
                "members": members,
                "is_private": False,
                "description": f"Topic: {topic}",
            }
        )

    assert len(channels) == 50, f"channel count {len(channels)} != 50"
    return channels


def _gen_slack(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    channels = _build_channel_list(users, rng)
    messages: list[dict[str, Any]] = []
    msg_idx = 0
    for channel in channels:
        members = channel["members"]
        if not members:
            continue
        count = int(rng.integers(20, 51))
        thread_anchors: list[str] = []
        for _ in range(count):
            author = members[int(rng.integers(0, len(members)))]
            mention_count = int(rng.integers(0, 3))
            mentions = sorted(
                {
                    members[int(rng.integers(0, len(members)))]
                    for _ in range(mention_count)
                }
                - {author}
            )
            ts = WEEK_START + timedelta(
                seconds=int(rng.integers(0, days * 24 * 3600))
            )
            in_thread = bool(rng.random() < 0.2 and thread_anchors)
            thread_id = thread_anchors[int(rng.integers(0, len(thread_anchors)))] if in_thread else None
            mid = f"msg-{msg_idx:05d}"
            msg_idx += 1
            messages.append(
                {
                    "message_id": mid,
                    "channel": channel["name"],
                    "thread_id": thread_id,
                    "author": author,
                    "text": faker.sentence(nb_words=12),
                    "timestamp": ts.isoformat(),
                    "mentions": mentions,
                }
            )
            if thread_id is None and rng.random() < 0.15:
                thread_anchors.append(mid)

    dm_count = 60
    dms: list[dict[str, Any]] = []
    for i in range(dm_count):
        pair = rng.choice(len(users), size=2, replace=False)
        sender = users[int(pair[0])].slack_handle
        recipient = users[int(pair[1])].slack_handle
        ts = WEEK_START + timedelta(seconds=int(rng.integers(0, days * 24 * 3600)))
        dms.append(
            {
                "dm_id": f"dm-{i:04d}",
                "sender": sender,
                "recipient": recipient,
                "text": faker.sentence(nb_words=10),
                "timestamp": ts.isoformat(),
            }
        )

    messages.sort(key=lambda m: m["message_id"])
    dms.sort(key=lambda d: d["dm_id"])
    return {"channels": channels, "messages": messages, "dms": dms}


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------


def _gen_jira(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    eng = _eng_users(users)
    everyone = users
    tickets: list[dict[str, Any]] = []
    per_project = 40
    for project in JIRA_PROJECTS:
        for i in range(per_project):
            key = f"{project}-{i + 1:03d}"
            assignee = eng[int(rng.integers(0, len(eng)))].jira_user
            reporter = everyone[int(rng.integers(0, len(everyone)))].jira_user
            priority = PRIORITIES[int(rng.choice(len(PRIORITIES), p=PRIORITY_WEIGHTS))]
            status = STATUSES[int(rng.choice(len(STATUSES), p=STATUS_WEIGHTS))]
            created = WEEK_START - timedelta(days=int(rng.integers(1, 60)))
            updated = created + timedelta(hours=int(rng.integers(1, 24 * 30)))
            tickets.append(
                {
                    "issue_key": key,
                    "project": project,
                    "title": faker.sentence(nb_words=6).rstrip("."),
                    "description": faker.paragraph(nb_sentences=3),
                    "assignee": assignee,
                    "reporter": reporter,
                    "priority": priority,
                    "status": status,
                    "blockers": [],
                    "created_at": created.isoformat(),
                    "updated_at": updated.isoformat(),
                    "labels": [],
                }
            )

    for ticket in tickets:
        if rng.random() < 0.1:
            same_project = [t for t in tickets if t["project"] == ticket["project"] and t["issue_key"] != ticket["issue_key"]]
            if same_project:
                blocker = same_project[int(rng.integers(0, len(same_project)))]
                ticket["blockers"] = [blocker["issue_key"]]

    tickets.sort(key=lambda t: t["issue_key"])
    return {"tickets": tickets}


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


def _gen_calendar(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    event_idx = 0
    recurring_templates = [
        ("Engineering standup", _eng_users(users), 30, [0, 1, 2, 3, 4], time(9, 30)),
        ("Product weekly", [u for u in users if u.department == "Product"] + _heads(users), 60, [1], time(10, 0)),
        ("All hands", users, 45, [3], time(14, 0)),  # Thursday 14:00 — used by Task 4 injection
        ("Design critique", [u for u in users if u.department in {"Design", "Product"}], 45, [2], time(11, 0)),
        ("Sales pipeline", [u for u in users if u.department == "Sales"], 30, [0], time(15, 0)),
        ("HR office hours", [u for u in users if u.department == "HR"], 30, [4], time(13, 0)),
    ]
    for title, attendees_pool, duration, weekdays, start_time in recurring_templates:
        for offset in range(days):
            day = WEEK_START + timedelta(days=offset)
            if day.weekday() not in weekdays:
                continue
            start = datetime.combine(day.date(), start_time)
            end = start + timedelta(minutes=duration)
            event_idx += 1
            events.append(
                {
                    "event_id": f"evt-{event_idx:05d}",
                    "title": title,
                    "description": f"Recurring: {title}",
                    "organizer": attendees_pool[0].calendar_id,
                    "attendees": sorted(u.calendar_id for u in attendees_pool),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "is_recurring": True,
                    "mandatory": title == "All hands",
                    "location": "Conf room A",
                }
            )

    for user in users:
        per_user = int(rng.integers(3, 9))
        for _ in range(per_user):
            day_offset = int(rng.integers(0, days))
            hour = int(rng.integers(8, 18))
            minute = int(rng.choice([0, 15, 30, 45]))
            day = WEEK_START + timedelta(days=day_offset)
            start = datetime.combine(day.date(), time(hour, minute))
            duration = int(rng.choice([15, 30, 45, 60]))
            end = start + timedelta(minutes=duration)
            peer_count = int(rng.integers(1, 4))
            peers = rng.choice(len(users), size=peer_count, replace=False)
            attendees = sorted({user.calendar_id, *(users[int(p)].calendar_id for p in peers)})
            event_idx += 1
            events.append(
                {
                    "event_id": f"evt-{event_idx:05d}",
                    "title": faker.bs().title(),
                    "description": faker.sentence(nb_words=8),
                    "organizer": user.calendar_id,
                    "attendees": attendees,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "is_recurring": False,
                    "mandatory": False,
                    "location": rng.choice(["Conf room B", "Conf room C", "Zoom", "Meet"]).item(),
                }
            )

    events.sort(key=lambda e: e["event_id"])
    return {"events": events}


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


def _gen_github(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    eng = _eng_users(users)
    repo_prefixes = ["backend", "mobile", "frontend", "infra", "docs", "data"]
    repos: list[dict[str, Any]] = []
    repo_idx = 0
    for prefix in repo_prefixes:
        for i in range(5):
            repo_idx += 1
            repos.append(
                {
                    "name": f"acme/{prefix}-{i + 1}",
                    "description": f"{prefix.capitalize()} service {i + 1}",
                    "prs": [],
                }
            )
    repos = repos[:30]

    pr_idx = 0
    target_prs = 99  # injection_patterns adds 1 q3-launch PR to reach exactly 100
    while pr_idx < target_prs:
        repo = repos[int(rng.integers(0, len(repos)))]
        pr_idx += 1
        author = eng[int(rng.integers(0, len(eng)))].github_username
        reviewer_count = int(rng.integers(1, 4))
        reviewer_pool = [u.github_username for u in eng if u.github_username != author]
        reviewer_ids = rng.choice(len(reviewer_pool), size=reviewer_count, replace=False)
        reviewers = sorted({reviewer_pool[int(i)] for i in reviewer_ids})
        state = rng.choice(["open", "merged", "closed"], p=[0.45, 0.45, 0.1]).item()
        created = WEEK_START - timedelta(days=int(rng.integers(0, 14)))
        repo["prs"].append(
            {
                "pr_id": f"PR-{pr_idx:04d}",
                "repo": repo["name"],
                "title": faker.sentence(nb_words=8).rstrip("."),
                "body": faker.paragraph(nb_sentences=2),
                "author": author,
                "reviewers": reviewers,
                "state": state,
                "created_at": created.isoformat(),
                "labels": [],
            }
        )

    for repo in repos:
        repo["prs"].sort(key=lambda pr: pr["pr_id"])
    repos.sort(key=lambda r: r["name"])
    return {"repos": repos}


# ---------------------------------------------------------------------------
# GDocs
# ---------------------------------------------------------------------------


def _gen_gdocs(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    titles_seed = [
        "Q3 Roadmap Plan",
        "Architecture Proposal",
        "OKR Tracking",
        "Hiring Plan",
        "Onboarding Guide",
        "Incident Postmortem",
        "Vendor Contract Notes",
        "Security Review",
        "Quarterly Business Review",
        "Brand Guidelines",
        "Compensation Bands",
        "Performance Review Template",
        "Mobile Redesign Spec",
        "Compliance Checklist",
        "Customer Success Playbook",
        "GTM Strategy",
        "Engineering Career Ladder",
        "Design System Inventory",
        "Sales Enablement Deck",
        "Internal FAQ",
    ]
    docs: list[dict[str, Any]] = []
    for i in range(50):
        title = (
            titles_seed[i]
            if i < len(titles_seed)
            else f"{faker.catch_phrase()} ({i + 1})"
        )
        owner_user = users[int(rng.integers(0, len(users)))]
        share_size = int(rng.integers(2, 9))
        share_ids = rng.choice(len(users), size=share_size, replace=False)
        shared_with = sorted({users[int(j)].gdocs_author_id for j in share_ids})

        acl: list[str] = []
        title_lower = title.lower()
        if any(k in title_lower for k in ("compensation", "performance review", "hiring", "vendor contract")):
            acl = ["hr"]
        elif any(k in title_lower for k in ("quarterly business review", "okr tracking")):
            acl = ["leadership"]

        created = WEEK_START - timedelta(days=int(rng.integers(7, 120)))
        updated = created + timedelta(days=int(rng.integers(0, 14)))
        docs.append(
            {
                "doc_id": f"gdoc-{i + 1:03d}",
                "title": title,
                "content": faker.paragraph(nb_sentences=8),
                "owner": owner_user.gdocs_author_id,
                "shared_with": shared_with,
                "acl": acl,
                "created_at": created.isoformat(),
                "updated_at": updated.isoformat(),
            }
        )

    docs.sort(key=lambda d: d["doc_id"])
    return {"docs": docs}


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def _gen_email(users: list[User], rng: np.random.Generator, faker: Faker, days: int) -> dict[str, Any]:
    emails: list[dict[str, Any]] = []
    email_idx = 0
    threads: dict[str, str] = {}
    for user in users:
        for _ in range(50):
            email_idx += 1
            email_id = f"email-{email_idx:05d}"
            recipient_count = int(rng.integers(1, 4))
            recipient_ids = rng.choice(len(users), size=recipient_count, replace=False)
            recipients = sorted({users[int(i)].email for i in recipient_ids if users[int(i)].email != user.email})
            if not recipients:
                recipients = [users[(int(rng.integers(0, len(users))))].email]
            in_thread = bool(rng.random() < 0.25 and threads)
            if in_thread:
                thread_keys = sorted(threads.keys())
                thread_id = thread_keys[int(rng.integers(0, len(thread_keys)))]
            else:
                thread_id = f"thr-{email_idx:05d}"
                threads[thread_id] = email_id
            sent = WEEK_START - timedelta(days=int(rng.integers(0, 21))) + timedelta(
                seconds=int(rng.integers(0, 24 * 3600))
            )
            importance = rng.choice(["high", "normal", "low"], p=[0.15, 0.75, 0.1]).item()
            emails.append(
                {
                    "email_id": email_id,
                    "thread_id": thread_id,
                    "sender": user.email,
                    "recipients": recipients,
                    "subject": faker.sentence(nb_words=6).rstrip("."),
                    "body": faker.paragraph(nb_sentences=3),
                    "sent_at": sent.isoformat(),
                    "importance": importance,
                    "unread": bool(rng.random() < 0.4),
                }
            )

    emails.sort(key=lambda e: e["email_id"])
    return {"emails": emails}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def generate_all(seed: int, output_dir: Path | str, days: int = 7) -> dict[str, int]:
    output_dir = Path(output_dir)
    users = load_users()
    users = sorted(users, key=lambda u: u.user_id)

    parent = np.random.SeedSequence(seed)
    rngs = _spawn(parent, 6)
    faker_seeds = _faker_seeds(parent, 6)
    fakers = [_seeded_faker(s) for s in faker_seeds]

    payloads = {
        "slack": _gen_slack(users, rngs[0], fakers[0], days),
        "jira": _gen_jira(users, rngs[1], fakers[1], days),
        "calendar": _gen_calendar(users, rngs[2], fakers[2], days),
        "github": _gen_github(users, rngs[3], fakers[3], days),
        "gdocs": _gen_gdocs(users, rngs[4], fakers[4], days),
        "email": _gen_email(users, rngs[5], fakers[5], days),
    }

    try:
        from src.data.injection_patterns import apply_injections

        payloads = apply_injections(payloads, users, np.random.default_rng(seed + 1))
    except ImportError:
        pass

    stats: dict[str, int] = {}
    for source, payload in payloads.items():
        _dump(output_dir / source / f"{source}.json", payload)
        if source == "slack":
            stats["slack_channels"] = len(payload["channels"])
            stats["slack_messages"] = len(payload["messages"])
            stats["slack_dms"] = len(payload["dms"])
        elif source == "jira":
            stats["jira_tickets"] = len(payload["tickets"])
        elif source == "calendar":
            stats["calendar_events"] = len(payload["events"])
        elif source == "github":
            stats["github_repos"] = len(payload["repos"])
            stats["github_prs"] = sum(len(r["prs"]) for r in payload["repos"])
        elif source == "gdocs":
            stats["gdocs_docs"] = len(payload["docs"])
        elif source == "email":
            stats["email_emails"] = len(payload["emails"])
    return stats


def iter_sources() -> Iterable[str]:
    return ("slack", "jira", "calendar", "github", "gdocs", "email")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    result = generate_all(seed=args.seed, output_dir=args.output, days=args.days)
    print(json.dumps(result, indent=2, sort_keys=True))
