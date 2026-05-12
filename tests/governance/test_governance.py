from src.governance.audit import audit_event, clear, recent
from src.governance.pii_redact import redact
from src.governance.rbac import check_resource, effective_role


def test_pii_redact_phone():
    text = "Call me at +31 6 1234 5678 tomorrow"
    assert "+31 6 1234 5678" not in redact(text)
    assert "REDACTED:phone" in redact(text)


def test_pii_redact_salary():
    text = "Salary band is €85,000 per year"
    assert "85,000" not in redact(text)
    assert "REDACTED:salary" in redact(text)


def test_pii_redact_iban():
    text = "Bank: NL91ABNA0417164300"
    assert "NL91ABNA0417164300" not in redact(text)


def test_rbac_leadership_channel_denied_to_manager():
    decision = check_resource("slack_channel", "#leadership", "manager")
    assert decision.allow is False


def test_rbac_leadership_channel_allowed_to_exec():
    decision = check_resource("slack_channel", "#leadership", "exec")
    assert decision.allow is True


def test_rbac_hr_doc_denied_to_manager():
    decision = check_resource("gdocs_acl", "hr", "manager")
    assert decision.allow is False


def test_rbac_hr_doc_allowed_to_hr():
    decision = check_resource("gdocs_acl", "hr", "HR")
    assert decision.allow is True


def test_audit_event_records():
    clear()
    audit_event("test.event", {"k": "v"})
    items = recent()
    assert items[-1]["kind"] == "test.event"
    assert items[-1]["payload"] == {"k": "v"}


def test_effective_role_resolves_vp_to_exec():
    from src.data.entity_consistency import load_users

    users = {u.name: u for u in load_users()}
    assert effective_role(users["Marco van der Berg"]) == "exec"
    assert effective_role(users["Sarah Chen"]) == "manager"
    assert effective_role(users["Sofia Almeida"]) == "HR"
    assert effective_role(users["Alice Rodriguez"]) == "IC"
