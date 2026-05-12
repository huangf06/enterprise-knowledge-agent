from src.case_studies.hr_helpdesk import (
    EMPLOYEE_DATA_TOOL,
    ESCALATION_TOOL,
    HR_POLICY_TOOL,
    hr_helpdesk_tools,
)


def test_hr_helpdesk_exposes_three_tools():
    tools = hr_helpdesk_tools()
    assert {t.name for t in tools} == {
        "hr_policy_search",
        "employee_self_data_query",
        "escalation_routing",
    }


def test_hr_policy_search_paternity():
    out = HR_POLICY_TOOL.run({"keyword": "paternity"}, {"role": "IC"})
    assert "pol-paternity" in out
    assert "4 weeks" in out


def test_employee_self_data_lisa_can_read_lisa():
    out = EMPLOYEE_DATA_TOOL.run({"employee_id": "u023"}, {"user_id": "u023", "role": "IC"})
    assert "Lisa Park" in out
    assert "vacation_balance_days" in out


def test_employee_self_data_other_user_denied():
    out = EMPLOYEE_DATA_TOOL.run({"employee_id": "u023"}, {"user_id": "u005", "role": "IC"})
    assert "RBAC denied" in out


def test_employee_self_data_hr_can_read_anyone():
    out = EMPLOYEE_DATA_TOOL.run({"employee_id": "u023"}, {"user_id": "u027", "role": "HR"})
    assert "Lisa Park" in out


def test_escalation_routing():
    out = ESCALATION_TOOL.run(
        {"employee_id": "u023", "case_summary": "manager not addressing concern"},
        {"role": "IC"},
    )
    assert "Daniel Weber" in out
    assert "HRBP" in out
