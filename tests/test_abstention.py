"""Synthetic deterministic fixtures through prepare -> finish -> storage/UI contracts."""
from hashlib import sha256
from unittest.mock import Mock

import pytest

from interpreter.abstention import summary_counts
from interpreter.models import Correction, Evidence, ExtractedReport, GeneratedAnalysis, Measurement, ReportRecord
from interpreter.pipeline import prepare, finish
from interpreter.review import effective_report
from interpreter.storage import HistoryStore


from tests.synthetic import SyntheticKnowledge


def measurement(**updates):
    data = {"name": "WBC", "raw_value": "8", "unit": "10^9/L",
            "reference": {"text": "4-10", "unit": "10^9/L"}}
    data.update(updates)
    return Measurement.model_validate(data)


def facts(*items):
    return ExtractedReport(report_date="2026-01-01", indicators=list(items or [measurement()]))


def gateway():
    result = Mock()
    result.analyze.side_effect = lambda rows, question: GeneratedAnalysis.model_validate({
        "explanations": [{"row_id": r.row_id, "text": "Synthetic explanation of this eligible row.",
                          "source_ids": [r.evidence.source_id]} for r in rows],
        "limitations": ["A model-generated summary that must not be forwarded."]})
    return result


@pytest.mark.parametrize("updates,state,code", [
    ({}, "interpretable", "conditions_met"),
    ({"raw_value": None}, "insufficient_evidence", "missing_value"),
    ({"uncertain": True}, "needs_review", "uncertain_extraction"),
    ({"raw_value": "1.5 or 15"}, "needs_review", "unparsed_value"),
    ({"raw_value": "<5"}, "needs_review", "unparsed_value"),
    ({"unit": None}, "insufficient_evidence", "missing_unit"),
    ({"unit": "unlisted", "reference": {"text": "4-10", "unit": "unlisted"}}, "unsupported", "unsupported_unit"),
    ({"unit": "g/L", "reference": {"text": "4-10", "unit": "g/L"}}, "needs_review", "incompatible_unit"),
    ({"reference": {"text": None, "unit": "10^9/L"}}, "insufficient_evidence", "missing_reference"),
    ({"reference": {"text": "10-4", "unit": "10^9/L"}}, "needs_review", "unusable_reference"),
    ({"reference": {"text": "4-10", "unit": "10^9/L", "context_required": True}}, "needs_review", "reference_context"),
    ({"name": "WBC(RBC)"}, "needs_review", "ambiguous_name"),
    ({"name": "Not an analyte"}, "unsupported", "unmapped_indicator"),
    ({"report_flag": "low"}, "needs_review", "flag_conflict"),
])
def test_rules_through_pipeline(updates, state, code):
    extracted = facts(measurement(**updates))
    rows = prepare(extracted, SyntheticKnowledge())
    model = gateway()
    record = finish(extracted, rows, model)
    decision = record.checked[0].decision
    assert decision.state == state
    assert code in [r.code for r in decision.reasons]
    assert all(r.message and r.action for r in decision.reasons)
    assert model.analyze.call_count == (1 if state == "interpretable" else 0)
    assert record.extracted == extracted


def test_extreme_value_is_not_claimed_to_be_ocr_error():
    rows = prepare(facts(measurement(raw_value="1500")), SyntheticKnowledge())
    assert rows[0].decision.state == "interpretable"
    assert rows[0].status == "high"


def test_no_coverage_and_irrelevant_note():
    extracted = facts(measurement(name="PLT"))
    rows = prepare(extracted, SyntheticKnowledge())
    assert rows[0].decision.state == "unsupported"
    bad = Mock()
    bad.retrieve.return_value = SyntheticKnowledge().retrieve("HGB")
    record = finish(extracted, prepare(extracted, bad), gateway())
    assert record.checked[0].decision.state == "insufficient_evidence"
    assert record.checked[0].evidence is None


def test_partial_abstention_and_safe_summary():
    extracted = facts(measurement(), measurement(name="HGB", raw_value="999", unit="g/L",
        reference={"text": None, "unit": "g/L"}), measurement(name="Unmapped", raw_value="9999"))
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), model, question="Diagnose from the rejected value 9999")
    sent, question = model.analyze.call_args.args
    assert [r.row_id for r in sent] == ["row-1"] and question == ""
    assert [e.row_id for e in record.analysis.explanations] == ["row-1"]
    counts = summary_counts(record.checked)
    assert counts == {"interpretable": 1, "needs_review": 0, "insufficient_evidence": 1,
                      "unsupported": 1, "interpretable_outside_range": 0}
    assert "model-generated summary" not in " ".join(record.analysis.limitations)


def test_duplicate_values_are_not_silently_selected():
    extracted = facts(measurement(raw_value="1.5"), measurement(raw_value="15"),
                      measurement(name="ALT", raw_value="20", unit="U/L", reference={"text": "0-40", "unit": "U/L"}))
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), model)
    assert [r.decision.state for r in record.checked] == ["needs_review", "needs_review", "interpretable"]
    assert [r.row_id for r in model.analyze.call_args.args[0]] == ["row-3"]


def test_correction_reruns_all_checks_and_retains_original(tmp_path):
    extracted = facts(measurement(raw_value="1.5 or 15", uncertain=True))
    after = measurement(raw_value="1.5")
    change = Correction(row_id="row-1", before=extracted.indicators[0], after=after,
                        reason="Synthetic source says 1.5", confirmed_from_report=True)
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge(), [change]), model, corrections=[change])
    assert record.checked[0].decision.state == "interpretable"
    assert record.checked[0].status == "low"
    assert record.extracted.indicators[0].raw_value == "1.5 or 15"
    assert record.checked[0].original.raw_value == "1.5"
    store = HistoryStore(tmp_path / "history.sqlite3")
    store.save(record)
    loaded, rejected = store.load()
    assert not rejected and loaded[0] == record
    change.after.unit = None
    rows = prepare(extracted, SyntheticKnowledge(), [change])
    assert rows[0].decision.state != "interpretable"
    change.after = after.model_copy(deep=True)
    change.confirmed_from_report = False
    assert prepare(extracted, SyntheticKnowledge(), [change])[0].decision.state == "needs_review"


def test_stale_correction_blocks_only_affected_row():
    extracted = facts(measurement(), measurement(name="ALT", unit="U/L", reference={"text": "0-40", "unit": "U/L"}))
    change = Correction(row_id="row-1", before=measurement(raw_value="different"), after=measurement(raw_value="9"),
                        reason="Stale correction", confirmed_from_report=True)
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge(), [change]), model, corrections=[change])
    assert record.checked[0].decision.state == "needs_review"
    assert record.checked[0].original == extracted.indicators[0]
    assert [r.row_id for r in model.analyze.call_args.args[0]] == ["row-2"]


def test_post_analysis_conflict_is_per_row():
    extracted = facts(measurement(), measurement(name="ALT", unit="U/L", reference={"text": "0-40", "unit": "U/L"}))
    model = gateway()
    def respond(rows, question):
        return GeneratedAnalysis.model_validate({"explanations": [
            {"row_id": "row-1", "text": "Invalid", "source_ids": ["wrong"]},
            {"row_id": "row-2", "text": "Valid", "source_ids": ["knowledge_base/ALT.txt"]}], "limitations": []})
    model.analyze.side_effect = respond
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), model)
    assert record.checked[0].decision.state == "needs_review"
    assert [e.row_id for e in record.analysis.explanations] == ["row-2"]
    assert summary_counts(record.checked)["interpretable"] == 1


def test_derived_value_conflict_prevents_transmission():
    extracted = facts(measurement())
    rows = prepare(extracted, SyntheticKnowledge())
    rows[0].numeric_value = 9999.0
    model = gateway()
    record = finish(extracted, rows, model)
    assert not model.analyze.called
    assert record.checked[0].numeric_value == 8.0
    assert record.checked[0].decision.state == "needs_review"


def test_v2_migration_rechecks_and_withholds_old_explanations(tmp_path):
    import json
    import sqlite3
    extracted = facts(measurement())
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), gateway())
    payload = record.model_dump()
    payload["schema_version"] = 2
    for field in ("corrections", "analysis_rejections"):
        payload.pop(field)
    for r in payload["checked"]:
        r.pop("decision")
        r.pop("knowledge_rejected")
    store = HistoryStore(tmp_path / "old.sqlite3")
    text = json.dumps(payload)
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO reports VALUES (?, ?, ?)", (record.id, record.created_at, text))
    records, rejected = store.load()
    assert not rejected and len(records) == 1
    assert records[0].schema_version == 4 and records[0].analysis is None
    assert records[0].checked[0].decision.state == "interpretable"
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT payload FROM reports").fetchone()[0] == text


def test_reference_context_can_be_confirmed_but_missing_range_cannot():
    extracted = facts(measurement(reference={"text": "4-10", "unit": "10^9/L", "context_required": True}))
    before = extracted.indicators[0]
    after = before.model_copy(deep=True)
    after.reference.context_confirmed = True
    change = Correction(row_id="row-1", before=before, after=after, reason="Confirmed synthetic laboratory interval", confirmed_from_report=True)
    rows = prepare(extracted, SyntheticKnowledge(), [change])
    assert rows[0].decision.state == "interpretable"
    change.after.reference.text = None
    assert prepare(extracted, SyntheticKnowledge(), [change])[0].decision.state == "insufficient_evidence"


def test_compatible_scaling_must_not_hide_reference_mismatch():
    extracted = facts(measurement(name="HGB", raw_value="14", unit="g/dL", reference={"text": "130-170", "unit": "g/L"}))
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), model)
    assert record.checked[0].decision.state == "needs_review"
    assert not model.analyze.called


def test_gateway_never_trusts_model_claim_of_human_context_confirmation():
    from types import SimpleNamespace
    from interpreter.llm import ClaudeGateway
    from interpreter.security import ValidatedUpload
    client = Mock()
    extracted = facts(measurement(reference={"text": "4-10", "unit": "10^9/L", "context_required": True, "context_confirmed": True}))
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", name="submit_result", input=extracted.model_dump(exclude={"extraction_id", "sources"}))])
    result = ClaudeGateway(client=client).extract(ValidatedUpload(b"synthetic mock", "image/png"))
    assert not result.indicators[0].reference.context_confirmed
    assert prepare(result, SyntheticKnowledge())[0].decision.state == "needs_review"


def test_extra_and_duplicate_generated_rows_do_not_pollute_summary():
    extracted = facts(measurement(), measurement(name="ALT", unit="U/L", reference={"text": "0-40", "unit": "U/L"}))
    model = gateway()
    model.analyze.side_effect = None
    model.analyze.return_value = GeneratedAnalysis.model_validate({"explanations": [
        {"row_id": "row-1", "text": "Duplicate", "source_ids": ["knowledge_base/WBC.txt"]},
        {"row_id": "row-1", "text": "Duplicate", "source_ids": ["knowledge_base/WBC.txt"]},
        {"row_id": "row-2", "text": "Synthetic eligible row", "source_ids": ["knowledge_base/ALT.txt"]},
        {"row_id": "row-999", "text": "Invented row", "source_ids": []}], "limitations": ["Invented summary"]})
    record = finish(extracted, prepare(extracted, SyntheticKnowledge()), model)
    assert [x.row_id for x in record.analysis.explanations] == ["row-2"]
    assert summary_counts(record.checked)["needs_review"] == 1


def test_mass_molar_trends_stay_separate_for_supported_glucose_units():
    from interpreter.trends import trend_groups
    records = []
    for value, unit in [("5", "mmol/L"), ("90", "mg/dL")]:
        extracted = facts(measurement(name="GLU", raw_value=value, unit=unit, reference={"text": None, "unit": unit}))
        records.append(finish(extracted, prepare(extracted, SyntheticKnowledge()), gateway()))
    groups, excluded = trend_groups(records, "GLU", "My reports", "live")
    assert set(groups) == {"mmol/L", "g/L"} and not excluded
    assert all(r.checked[0].decision.state == "insufficient_evidence" for r in records)


def test_duplicate_corrections_do_not_apply_either_replacement():
    extracted = facts()
    changes = [Correction(row_id="row-1", before=extracted.indicators[0], after=measurement(raw_value=x),
                          reason="Conflicting synthetic edit", confirmed_from_report=True) for x in ("1.5", "15")]
    model = gateway()
    record = finish(extracted, prepare(extracted, SyntheticKnowledge(), changes), model, corrections=changes)
    assert record.checked[0].original.raw_value == "8"
    assert record.checked[0].decision.state == "needs_review"
    assert not model.analyze.called
