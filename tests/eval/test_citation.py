"""F4 citation groundedness unit tests."""

from src.eval.citation import (
    citation_groundedness,
    parse_bracket_tokens,
    parse_citations,
)


def _hist(*entries):
    return [{"tool": t, "args": {}, "result": r} for t, r in entries]


def test_parse_citations_returns_pairs():
    out = parse_citations("Hello [slack:msg-001] world [jira:PROJ-2]")
    assert out == [("slack", "msg-001"), ("jira", "PROJ-2")]


def test_parse_citations_ignores_malformed_brackets():
    out = parse_citations("[just text] and [slack:ok-1]")
    assert out == [("slack", "ok-1")]


def test_well_formedness_counts_malformed():
    out = citation_groundedness(
        "Good [slack:m1] and malformed [stray] also [jira:PROJ-1]",
        _hist(("slack_query", "m1"), ("jira_query", "PROJ-1")),
    )
    # 2 valid out of 3 brackets
    assert out["well_formedness"] == round(2 / 3, 4)


def test_source_coverage_fails_on_uncalled_tool():
    out = citation_groundedness(
        "Per slack [slack:m1]",
        _hist(("jira_query", "m1")),  # jira called, not slack
    )
    assert out["source_coverage"] == 0.0


def test_id_grounded_fails_on_invented_id():
    out = citation_groundedness(
        "Per slack [slack:invented-zzz]",
        _hist(("slack_query", "Real content with msg-1")),
    )
    assert out["id_grounded"] == 0.0


def test_id_grounded_passes_when_substring_present():
    out = citation_groundedness(
        "Per slack [slack:msg-1]",
        _hist(("slack_query", "Slack returned: msg-1 from Alice")),
    )
    assert out["id_grounded"] == 1.0


def test_no_citations_vacuous_pass():
    out = citation_groundedness("Plain prose, no brackets.", _hist())
    assert out["source_coverage"] == 1.0
    assert out["id_grounded"] == 1.0
    assert out["n_citations"] == 0


def test_parse_bracket_tokens_includes_everything():
    out = parse_bracket_tokens("[a:b] and [stray] and [c:d]")
    assert out == ["a:b", "stray", "c:d"]


def test_cal_alias_maps_to_calendar():
    out = citation_groundedness(
        "Today's meeting [cal:evt-12]",
        _hist(("calendar_query", "Event evt-12: standup at 10")),
    )
    assert out["source_coverage"] == 1.0
    assert out["id_grounded"] == 1.0
