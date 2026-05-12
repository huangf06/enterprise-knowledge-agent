from src.tools import registry

CTX_MANAGER = {"role": "manager"}
CTX_HR = {"role": "HR"}
CTX_EXEC = {"role": "exec"}


def test_registry_lists_six_tools():
    names = registry().names()
    assert set(names) == {
        "slack_query",
        "jira_query",
        "calendar_query",
        "github_pr_review",
        "gdocs_search",
        "email_query",
    }


def test_slack_query_for_sarah_finds_cto_dms():
    out = registry().get("slack_query").run(
        {
            "user_handle": "sarah.chen",
            "channels": ["#nonexistent"],
            "include_mentions": False,
            "max_items": 50,
        },
        CTX_MANAGER,
    )
    assert "marco.vandenberg" in out
    assert "DM" in out


def test_slack_query_finds_monday_incident_thread():
    out = registry().get("slack_query").run(
        {"user_handle": "sarah.chen", "keyword": "production incident", "include_dms": False},
        CTX_MANAGER,
    )
    assert "production incident" in out.lower()


def test_jira_query_open_high_priority():
    out = registry().get("jira_query").run(
        {"assignee": "sarah.chen", "statuses": ["Open", "In Progress"], "priority_min": "High"},
        CTX_MANAGER,
    )
    assert "sarah.chen" in out or "0 tickets" in out


def test_calendar_query_thursday_conflict():
    out = registry().get("calendar_query").run(
        {
            "user_calendar_id": "sarah.chen@acme.nl",
            "start": "2026-05-07T00:00:00",
            "end": "2026-05-08T00:00:00",
            "include_conflicts": True,
        },
        CTX_MANAGER,
    )
    assert "CONFLICT" in out


def test_github_pr_review_for_sarah_finds_q3_launch():
    out = registry().get("github_pr_review").run(
        {"reviewer": "sarah.chen", "label": "q3-launch"}, CTX_MANAGER
    )
    assert "q3-launch" in out


def test_gdocs_search_hr_doc_denied_to_manager():
    out = registry().get("gdocs_search").run({"keyword": "Compensation"}, CTX_MANAGER)
    assert "RBAC denied" in out or "0 visible" in out


def test_gdocs_search_hr_doc_allowed_to_hr():
    out = registry().get("gdocs_search").run(
        {"keyword": "Compensation"}, {"role": "HR", "gdocs_author_id": "u-u027"}
    )
    assert "RBAC denied" not in out
    assert "gdoc-" in out


def test_email_query_ey_contract_for_sarah():
    out = registry().get("email_query").run(
        {"user_email": "sarah.chen@acme.nl", "importance": "high"}, CTX_MANAGER
    )
    assert "EY contract" in out


def test_slack_query_leadership_denied_to_manager():
    out = registry().get("slack_query").run(
        {"user_handle": "marco.vandenberg", "channels": ["#leadership"], "max_items": 5},
        CTX_MANAGER,
    )
    assert "RBAC denied" in out


def test_slack_query_leadership_allowed_to_exec():
    out = registry().get("slack_query").run(
        {"user_handle": "marco.vandenberg", "channels": ["#leadership"], "max_items": 5},
        CTX_EXEC,
    )
    assert "RBAC denied" not in out


def test_tool_schemas_are_anthropic_compatible():
    for schema in registry().schemas():
        assert "name" in schema and "description" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]
