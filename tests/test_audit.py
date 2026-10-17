"""Synthetic end-to-end claim audit tests; no paid model requests."""
from unittest.mock import Mock
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from interpreter.audit import fact_text, audit_record
from interpreter.models import GeneratedAnalysis, ReportRecord, Correction
from interpreter.pipeline import prepare, finish
from interpreter.knowledge import KnowledgeBase
from interpreter.storage import HistoryStore
from interpreter.llm import ClaudeGateway
from tests.test_abstention import facts, measurement
from tests.synthetic import SyntheticKnowledge


def run(claims, extracted=None, knowledge=None, corrections=()):
    extracted = extracted or facts()
    rows = prepare(extracted, knowledge or SyntheticKnowledge(), corrections)
    model = Mock()
    model.analyze.side_effect = lambda eligible, question: GeneratedAnalysis.model_validate({
        "explanations": [{"row_id": row.row_id, "claims": claims(row) if callable(claims) else claims,
            "source_ids": [row.evidence.source_id]} for row in eligible], "limitations": []})
    return finish(extracted, rows, model, corrections=corrections)


@pytest.mark.parametrize("claim,outcome", [
    ("Report fact: WBC = 8 10^9/L; range status = within_range.", "Supported"),
    ("Report fact: WBC = 80 10^9/L; range status = within_range.", "Contradicted"),
    ("Report fact: WBC = 8 g/L; range status = within_range.", "Contradicted"),
    ("Report fact: WBC = 8 10^9/L; range status = high.", "Contradicted"),
    ("Report fact: TROPONIN = 8 10^9/L; range status = within_range.", "Unsupported"),
    ("You have leukemia.", "Unsupported"),
    ("This definitely proves infection.", "Unsupported"),
    ("Start antibiotics today.", "Unsupported"),
    ("Your condition is improving.", "Unsupported"),
    ("WBC is 999.", "Contradicted"),
    ("WBC is 8 g/L.", "Contradicted"),
    ("WBC is high.", "Contradicted"),
    ("Troponin is 2.", "Unsupported"),
    ("Troponin is elevated.", "Unsupported"),
    ("There may be several explanations for this observation.", "Needs Review"),
])
def test_actual_pipeline_claim_outcomes(claim, outcome):
    record = run([claim])
    audit = record.claim_audits[0]
    assert audit.outcome == outcome and audit.reason
    assert audit.observation_id == record.extracted.sources[0].observation_id
    assert record.checked[0].decision.state == "interpretable"  # Separate dimensions.
    assert audit_record(record) == record.claim_audits


def test_retrieved_context_not_just_source_id(tmp_path):
    kb = KnowledgeBase(tmp_path / "chroma")
    extracted = facts(measurement(specimen="blood", raw_value="12"))
    record = run(lambda r: [fact_text(r), "General context: " + r.evidence.selected_text], extracted, kb)
    assert [a.outcome for a in record.claim_audits] == ["Supported", "Supported"]
    context = record.claim_audits[1]
    assert context.knowledge_id == "kb:WBC" and context.knowledge_version.startswith("sha256:")
    assert context.evidence_text == record.checked[0].evidence.selected_text
    # Even a true sentence lifted from a related source loses its qualifiers/scope.
    clipped = "General context: " + context.evidence_text.split("\n")[0]
    assert run([clipped], extracted, kb).claim_audits[0].outcome == "Unsupported"
    assert run(["General context: This proves leukemia."], extracted, kb).claim_audits[0].outcome == "Unsupported"
    # No general semantic entailment is claimed for a plausible paraphrase.
    assert run(["Several contextual factors may affect the result."], extracted, kb).claim_audits[0].outcome == "Needs Review"


def test_missing_source_cannot_be_supported_context():
    record = run(["General context: Synthetic educational knowledge."])
    assert record.claim_audits[0].outcome == "Unsupported"


def test_corrections_history_and_forged_audit_are_rechecked(tmp_path):
    extracted = facts()
    correction = Correction(row_id="row-1", before=extracted.indicators[0], after=measurement(raw_value="9"),
        confirmed_from_report=True, reason="Synthetic original says nine")
    record = run(["Report fact: WBC = 8 10^9/L; range status = within_range."], extracted,
                 corrections=[correction])
    assert record.claim_audits[0].outcome == "Contradicted"
    assert record.extracted.sources[0].raw.raw_value == "8"
    assert record.claim_audits[0].observation_id == extracted.sources[0].observation_id
    payload = record.model_dump()
    payload["claim_audits"][0]["outcome"] = "Supported"
    assert ReportRecord.model_validate(payload).claim_audits == record.claim_audits
    payload.pop("claim_audits")  # Pre-audit v4 history.
    assert ReportRecord.model_validate(payload).claim_audits == record.claim_audits
    store = HistoryStore(tmp_path / "history.sqlite3")
    store.save(record)
    loaded, rejected = store.load()
    assert not rejected and loaded[0].claim_audits == record.claim_audits


def test_partial_claim_rejection_and_abstention_do_not_fail_report():
    extracted = facts(measurement(), measurement(name="ALT", unit="U/L", reference={"text": "0-40", "unit": "U/L"}),
        measurement(name="HGB", unit=None))
    record = run(lambda r: [fact_text(r), "WBC is 999."] if r.canonical_id == "WBC" else [fact_text(r)], extracted)
    assert [a.outcome for a in record.claim_audits] == ["Supported", "Contradicted", "Supported"]
    assert all(a.row_id != "row-3" for a in record.claim_audits)
    assert not any("999" in x for x in record.analysis.limitations)


def test_legacy_prose_and_extra_text_cannot_escape_audit():
    record = run(lambda r: [fact_text(r)])
    payload = record.model_dump()
    payload["analysis"]["explanations"][0]["text"] = "WBC is 80. Start treatment. Another idea."
    reloaded = ReportRecord.model_validate(payload)
    assert [a.outcome for a in reloaded.claim_audits] == ["Supported", "Contradicted", "Unsupported", "Needs Review"]
    compound = run(lambda r: [fact_text(r) + " Therefore you are healthy."])
    assert [a.outcome for a in compound.claim_audits] == ["Supported", "Unsupported"]


def test_claude_tool_output_flows_through_audit(tmp_path):
    kb = KnowledgeBase(tmp_path / "chroma")
    extracted = facts(measurement(specimen="blood"))
    rows = prepare(extracted, kb)
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[SimpleNamespace(
        type="tool_use", name="submit_result", input={"explanations": [{"row_id": "row-1",
            "claims": [fact_text(rows[0]), "You have leukemia."], "source_ids": [rows[0].evidence.source_id]}], "limitations": []})])
    record = finish(extracted, rows, ClaudeGateway(client=client))
    assert [a.outcome for a in record.claim_audits] == ["Supported", "Unsupported"]
    assert client.messages.create.call_count == 1  # No second semantic-audit model.
    assert "auditable_fact_template" in str(client.messages.create.call_args.kwargs["messages"])


def test_mixed_audit_ui_withholds_contradicted_text():
    record = run(lambda r: [fact_text(r), "WBC is 98765.", "Start antibiotics.", "Unresolved meaning."])
    def render(record_json):
        from interpreter.models import ReportRecord
        from interpreter.ui import detail
        detail(ReportRecord.model_validate_json(record_json))
    app = AppTest.from_function(render, args=(record.model_dump_json(),), default_timeout=30).run()
    assert not app.exception
    visible = " ".join(x.value for x in app.text)
    assert "98765" not in visible
    assert "Supported" in visible and "Unsupported" in visible and "Needs Review" in visible
    assert any("Contradicted claim withheld" in x.value for x in app.warning)
    assert any("Unconfirmed generated claim" in x.value for x in app.warning)


def test_synthetic_demo_audit_keeps_presets_and_occurrence_ids(tmp_path):
    from interpreter.demo import demo_reports
    kb = KnowledgeBase(tmp_path / "chroma")
    reports = demo_reports(kb)
    assert len(reports) == 3
    for record in reports:
        assert record.mode == "synthetic"
        supported = [a for a in record.claim_audits if a.outcome == "Supported"]
        assert len(supported) == 4 and all(a.basis == "report_fact" for a in supported)
        assert all(a.observation_id in {s.observation_id for s in record.extracted.sources} for a in supported)
