from src.tools import registry


def test_registry_lists_three_tools():
    names = registry().names()
    assert set(names) == {"slack_query", "jira_query", "calendar_query"}


def test_slack_query_for_sarah_finds_cto_dms():
    out = registry().get("slack_query").run(
        {
            "user_handle": "sarah.chen",
            "channels": ["#nonexistent"],
            "include_mentions": False,
            "max_items": 50,
        }
    )
    assert "marco.vandenberg" in out
    assert "DM" in out


def test_slack_query_finds_monday_incident_thread():
    out = registry().get("slack_query").run(
        {"user_handle": "sarah.chen", "keyword": "production incident", "include_dms": False}
    )
    assert "production incident" in out.lower()


def test_jira_query_open_high_priority():
    out = registry().get("jira_query").run(
        {"assignee": "sarah.chen", "statuses": ["Open", "In Progress"], "priority_min": "High"}
    )
    assert "sarah.chen" in out or "0 tickets" in out


def test_calendar_query_thursday_conflict():
    out = registry().get("calendar_query").run(
        {
            "user_calendar_id": "sarah.chen@acme.nl",
            "start": "2026-05-07T00:00:00",
            "end": "2026-05-08T00:00:00",
            "include_conflicts": True,
        }
    )
    assert "CONFLICT" in out


def test_tool_schemas_are_anthropic_compatible():
    for schema in registry().schemas():
        assert "name" in schema and "description" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]
