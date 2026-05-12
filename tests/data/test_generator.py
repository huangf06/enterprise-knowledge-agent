import json
from datetime import datetime, timedelta

from src.data.generator import generate_all


def test_generator_deterministic(tmp_path):
    generate_all(seed=42, output_dir=tmp_path / "run1", days=7)
    generate_all(seed=42, output_dir=tmp_path / "run2", days=7)
    for source in ["slack", "jira", "calendar", "github", "gdocs", "email"]:
        f1 = (tmp_path / "run1" / source / f"{source}.json").read_text()
        f2 = (tmp_path / "run2" / source / f"{source}.json").read_text()
        assert f1 == f2, f"{source} not deterministic"


def test_generator_counts_match_design(tmp_path):
    generate_all(seed=42, output_dir=tmp_path, days=7)
    slack = json.loads((tmp_path / "slack" / "slack.json").read_text())
    jira = json.loads((tmp_path / "jira" / "jira.json").read_text())
    gdocs = json.loads((tmp_path / "gdocs" / "gdocs.json").read_text())
    github = json.loads((tmp_path / "github" / "github.json").read_text())
    assert len(slack["channels"]) == 50
    assert len(jira["tickets"]) == 200
    assert len(gdocs["docs"]) == 50
    assert len(github["repos"]) == 30
    assert sum(len(r["prs"]) for r in github["repos"]) == 100


def test_calendar_7_day_window(tmp_path):
    generate_all(seed=42, output_dir=tmp_path, days=7)
    cal = json.loads((tmp_path / "calendar" / "calendar.json").read_text())
    assert len(cal["events"]) > 0
    starts = [datetime.fromisoformat(e["start"]) for e in cal["events"]]
    span = max(starts) - min(starts)
    assert span <= timedelta(days=8), f"calendar span {span} exceeds 7-day window"


def test_email_per_user(tmp_path):
    generate_all(seed=42, output_dir=tmp_path, days=7)
    email = json.loads((tmp_path / "email" / "email.json").read_text())
    assert 1400 <= len(email["emails"]) <= 1600
