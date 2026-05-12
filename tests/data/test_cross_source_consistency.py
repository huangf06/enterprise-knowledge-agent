import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.data.entity_consistency import load_users
from src.data.generator import generate_all


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    out = tmp_path_factory.mktemp("synth")
    generate_all(seed=42, output_dir=out, days=7)
    payload = {}
    for source in ("slack", "jira", "calendar", "github", "gdocs", "email"):
        payload[source] = json.loads((out / source / f"{source}.json").read_text())
    return payload


def _overlaps(events):
    pairs = []
    for i, a in enumerate(events):
        a_start = datetime.fromisoformat(a["start"])
        a_end = datetime.fromisoformat(a["end"])
        for b in events[i + 1 :]:
            b_start = datetime.fromisoformat(b["start"])
            b_end = datetime.fromisoformat(b["end"])
            if a_start < b_end and b_start < a_end:
                pairs.append((a["event_id"], b["event_id"]))
    return pairs


def test_sarah_thursday_calendar_conflict(synth):
    sarah = next(u for u in load_users() if u.name == "Sarah Chen")
    events = [
        e for e in synth["calendar"]["events"]
        if sarah.email in e["attendees"] and datetime.fromisoformat(e["start"]).weekday() == 3
    ]
    conflicts = _overlaps(events)
    assert len(conflicts) >= 1, f"no Thursday conflict for Sarah; events={events}"


def test_jira_ticket_links_to_gdoc(synth):
    gdoc_ids = {d["doc_id"] for d in synth["gdocs"]["docs"]}
    linked = [t for t in synth["jira"]["tickets"] if any(g in t["description"] for g in gdoc_ids)]
    assert len(linked) >= 5


def test_slack_thread_mentions_calendar_event(synth):
    event_ids = {e["event_id"] for e in synth["calendar"]["events"]}
    linked = [m for m in synth["slack"]["messages"] if any(eid in m["text"] for eid in event_ids)]
    assert len(linked) >= 3


def test_q3_launch_pr_blocking_sarah(synth):
    sarah = next(u for u in load_users() if u.name == "Sarah Chen")
    blocking = [
        pr
        for repo in synth["github"]["repos"]
        for pr in repo["prs"]
        if sarah.github_username in pr["reviewers"] and "q3-launch" in pr.get("labels", [])
    ]
    assert len(blocking) >= 1


def test_leadership_channel_excludes_sarah(synth):
    sarah = next(u for u in load_users() if u.name == "Sarah Chen")
    leadership = next(c for c in synth["slack"]["channels"] if c["name"] == "#leadership")
    assert sarah.slack_handle not in leadership["members"]
    assert 3 <= len(leadership["members"]) <= 5


def test_hr_private_gdocs(synth):
    hr_docs = [d for d in synth["gdocs"]["docs"] if d.get("acl") == ["hr"]]
    assert len(hr_docs) >= 3


def test_cto_dms_to_sarah(synth):
    sarah = next(u for u in load_users() if u.name == "Sarah Chen")
    vp_eng = next(u for u in load_users() if u.role == "VP Engineering")
    dms = [
        d
        for d in synth["slack"]["dms"]
        if d["sender"] == vp_eng.slack_handle and d["recipient"] == sarah.slack_handle
    ]
    assert len(dms) >= 3


def test_monday_production_incident_thread(synth):
    monday_morning = synth["slack"]["messages"]
    incidents = [
        m
        for m in monday_morning
        if "production incident" in m["text"].lower()
        and m["channel"] == "#engineering"
        and datetime.fromisoformat(m["timestamp"]).weekday() == 0
    ]
    assert len(incidents) >= 1
    parent = incidents[0]
    replies = [m for m in synth["slack"]["messages"] if m.get("thread_id") == parent["message_id"]]
    assert len(replies) >= 2


def test_ey_contract_email_stale_for_sarah(synth):
    sarah = next(u for u in load_users() if u.name == "Sarah Chen")
    candidates = [
        e
        for e in synth["email"]["emails"]
        if "ey contract" in e["subject"].lower() and sarah.email in e["recipients"]
    ]
    assert len(candidates) >= 1
    e = candidates[0]
    sent = datetime.fromisoformat(e["sent_at"])
    age = datetime(2026, 5, 11) - sent  # Monday of demo week
    assert age >= timedelta(days=4)
    assert e["importance"] == "high"
    assert e["unread"] is True


def test_injections_preserve_determinism(tmp_path):
    generate_all(seed=42, output_dir=tmp_path / "a", days=7)
    generate_all(seed=42, output_dir=tmp_path / "b", days=7)
    for source in ("slack", "jira", "calendar", "github", "gdocs", "email"):
        a = (tmp_path / "a" / source / f"{source}.json").read_text()
        b = (tmp_path / "b" / source / f"{source}.json").read_text()
        assert a == b
