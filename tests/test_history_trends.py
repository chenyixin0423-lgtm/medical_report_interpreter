import sqlite3

import pytest

from interpreter.demo import demo_reports
from interpreter.models import Evidence, ExtractedReport, GeneratedAnalysis, ReportRecord
from interpreter.pipeline import finish, prepare
from interpreter.storage import HistoryStore
from interpreter.trends import trend_groups
from interpreter.validation import check_report


class EmptyKnowledge:
    def retrieve(self, code):
        return None


def make_record(value="14", unit="g/dL", day="2026-01-01", **extra):
    facts = ExtractedReport.model_validate({"report_date": day, "indicators": [{"name": "HGB", "raw_value": value,
        "unit": unit, "reference": {"text": None, "unit": unit}}]})
    return ReportRecord(mode="live", extracted=facts, checked=check_report(facts), facts_reviewed=True, **extra)


def test_history_roundtrip_delete_and_corruption(tmp_path):
    path = tmp_path / "history.sqlite3"
    store = HistoryStore(path)
    a, b = make_record(), make_record()
    assert a.id != b.id
    store.save(a)
    store.save(b)
    store.save(a)
    assert len(store.load()[0]) == 2
    assert store.load()[0][0].extracted == a.extracted
    store.delete("' OR 1=1 --")
    assert len(store.load()[0]) == 2
    store.delete(a.id)
    assert [r.id for r in store.load()[0]] == [b.id]
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO reports VALUES (?, ?, ?)", ("broken", "today", "not json"))
    assert store.load()[1] == 1
    with pytest.raises(ValueError):
        store.save(demo_reports(EmptyKnowledge())[0])


def test_trend_conversion_isolation_and_unknown():
    a, b = make_record(), make_record("130", "g/L", "2026-02-01")
    unrelated = make_record("999", series="Another person")
    unknown = make_record("14", "unknown", "2026-03-01")
    groups, excluded = trend_groups([a, b, unrelated, unknown], "HGB", "My reports", "live")
    assert [p["Value"] for p in groups["g/L"]] == [140, 130]
    assert len(excluded) == 1


def test_trends_separate_incompatible_units():
    groups, _ = trend_groups([make_record(), make_record("2", "mmol/L")], "HGB", "My reports", "live")
    assert set(groups) == {"g/L", "mmol/L"}


def test_trends_exclude_duplicate_uncertain_dates_and_flags():
    a = make_record(day=None)
    b = make_record()
    b.extracted.indicators[0].uncertain = True
    b.checked = check_report(b.extracted)
    c = make_record()
    c.extracted.indicators.append(c.extracted.indicators[0].model_copy(deep=True))
    c.checked = check_report(c.extracted)
    groups, excluded = trend_groups([a, b, c], "HGB", "My reports", "live")
    assert not groups
    assert len(excluded) == 4


def test_pipeline_validates_mock_analysis_and_preserves_facts():
    from unittest.mock import Mock
    facts = make_record().extracted
    rows = prepare(facts, EmptyKnowledge())
    gateway = Mock()
    gateway.analyze.return_value = GeneratedAnalysis.model_validate({"explanations": [
        {"row_id": "row-1", "text": "Insufficient coverage", "source_ids": []}], "limitations": []})
    result = finish(facts, rows, gateway)
    assert result.analysis is not None
    assert result.extracted == facts
    assert result.checked[0].original == facts.indicators[0]
    gateway.analyze.return_value.explanations[0].source_ids = ["invented"]
    failed = finish(facts, rows, gateway)
    assert failed.analysis is None and failed.analysis_issue
    assert failed.extracted == facts


def test_demo_always_synthetic():
    reports = demo_reports(EmptyKnowledge())
    assert len(reports) == 3
    assert all(r.mode == "synthetic" for r in reports)
    groups, _ = trend_groups(reports, "HGB", "Synthetic series A", "synthetic")
    assert [p["Value"] for p in groups["g/L"]] == [134, 128, 131]


def test_persisted_status_cannot_override_facts():
    from pydantic import ValidationError
    payload = make_record().model_dump()
    payload["checked"][0]["status"] = "within_range"
    with pytest.raises(ValidationError, match="Derived data"):
        ReportRecord.model_validate(payload)


def test_missing_indicator_does_not_become_zero_or_normal():
    a = make_record()
    other_facts = ExtractedReport.model_validate({"report_date": "2026-02-01", "indicators": [{
        "name": "Unrecognized", "raw_value": "5", "unit": "g/L", "reference": {"text": None, "unit": None}}]})
    b = ReportRecord(mode="live", facts_reviewed=True, extracted=other_facts, checked=check_report(other_facts))
    groups, _ = trend_groups([a, b], "HGB", "My reports", "live")
    assert len(groups["g/L"]) == 1
