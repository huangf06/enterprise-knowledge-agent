from src.data.entity_consistency import load_users


def test_30_users_loaded():
    users = load_users()
    assert len(users) == 30


def test_user_has_all_source_identities():
    users = load_users()
    for u in users:
        assert u.slack_handle and u.jira_user and u.email and u.github_username and u.gdocs_author_id and u.calendar_id


def test_email_unique_across_users():
    users = load_users()
    emails = [u.email for u in users]
    assert len(set(emails)) == len(emails)


def test_5_departments_3_offices():
    users = load_users()
    depts = {u.department for u in users}
    offices = {u.office for u in users}
    assert len(depts) == 5
    assert len(offices) == 3


def test_slack_handle_matches_email_local_part():
    users = load_users()
    for u in users:
        local = u.email.split("@")[0]
        assert u.slack_handle == local, f"User {u.name} slack/email drift"


def test_sarah_chen_present_as_eng_manager_amsterdam():
    users = load_users()
    sarah = next((u for u in users if u.name == "Sarah Chen"), None)
    assert sarah is not None
    assert sarah.department == "Engineering"
    assert sarah.office == "Amsterdam"
    assert "Manager" in sarah.role
