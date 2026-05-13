"""A7 trace replay unit tests."""

import json
from pathlib import Path

from src.eval.trace_replay import REGRESSION_THRESHOLDS, compare, is_pass


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps({"summary": {}, "rows": rows}))


def _row(sid: str, tool_f1: float, gov: float = 1.0, well: float = 1.0, src: float = 1.0, ids: float = 1.0) -> dict:
    return {
        "scenario_id": sid,
        "ok": True,
        "scores": {"governance_compliance": gov},
        "citations": {"well_formedness": well, "source_coverage": src, "id_grounded": ids},
        "trajectory": {"tool_f1": tool_f1},
    }


def test_gold_equals_candidate_passes(tmp_path: Path):
    gold = tmp_path / "g.json"
    cand = tmp_path / "c.json"
    rows = [_row("a", 1.0), _row("b", 0.8)]
    _write(gold, rows)
    _write(cand, rows)
    report = compare(gold, cand)
    assert is_pass(report)


def test_tool_f1_regression_flagged(tmp_path: Path):
    gold = tmp_path / "g.json"
    cand = tmp_path / "c.json"
    _write(gold, [_row("a", 1.0)])
    _write(cand, [_row("a", 0.5)])  # 0.5 drop > 0.10 threshold
    report = compare(gold, cand)
    assert not is_pass(report)
    assert report["n_regressions"] == 1
    assert "tool_f1" in report["regressions"][0]["regressed_on"]


def test_within_threshold_not_flagged(tmp_path: Path):
    gold = tmp_path / "g.json"
    cand = tmp_path / "c.json"
    _write(gold, [_row("a", 1.0)])
    _write(cand, [_row("a", 0.95)])  # 0.05 drop < 0.10 threshold
    report = compare(gold, cand)
    assert is_pass(report)


def test_missing_in_candidate_fails(tmp_path: Path):
    gold = tmp_path / "g.json"
    cand = tmp_path / "c.json"
    _write(gold, [_row("a", 1.0), _row("b", 1.0)])
    _write(cand, [_row("a", 1.0)])
    report = compare(gold, cand)
    assert not is_pass(report)
    assert report["n_missing_in_candidate"] == 1


def test_governance_drop_flagged_at_lower_threshold(tmp_path: Path):
    gold = tmp_path / "g.json"
    cand = tmp_path / "c.json"
    _write(gold, [_row("a", 1.0, gov=1.0)])
    _write(cand, [_row("a", 1.0, gov=0.9)])  # 0.10 drop > 0.05 governance threshold
    report = compare(gold, cand)
    assert not is_pass(report)
    assert "governance_compliance" in report["regressions"][0]["regressed_on"]
