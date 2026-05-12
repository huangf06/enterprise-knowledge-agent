def test_graph_compiles():
    from src.agent import app

    compiled = app()
    assert compiled is not None


def test_state_typed_dict_keys():
    from src.agent.state import AgentState

    assert "query" in AgentState.__annotations__
    assert "tool_history" in AgentState.__annotations__
    assert "pending_tool" in AgentState.__annotations__
    assert "final_answer" in AgentState.__annotations__


def test_tool_registry_accessible_via_agent():
    from src.tools import registry

    schemas = registry().schemas()
    assert len(schemas) == 6
    assert {s["name"] for s in schemas} == {
        "slack_query",
        "jira_query",
        "calendar_query",
        "github_pr_review",
        "gdocs_search",
        "email_query",
    }
