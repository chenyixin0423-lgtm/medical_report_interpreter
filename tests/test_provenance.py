"""End-to-end source association and fail-closed provenance, entirely synthetic."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import json

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from interpreter.knowledge import KB_PATH, KnowledgeBase
from interpreter.models import Correction, ExtractedReport, ExtractionPayload, ReportRecord
from interpreter.pipeline import prepare, finish
from interpreter.tracking import attach_text_matches
from interpreter.llm import ClaudeGateway, ModelError
from interpreter.security import validate_upload, ValidatedUpload
from interpreter.storage import HistoryStore
from interpreter.trends import trend_groups
from interpreter.demo import demo_reports
from tests.synthetic import SyntheticKnowledge


def facts(value="8"):
    return ExtractedReport(report_date="2026-01-01", indicators=[{
        "name": "WBC", "raw_value": value, "unit": "10^9/L",
        "reference": {"text": "4-10", "unit": "10^9/L"}}])


def pdf(text="WBC 8 10^9/L 4-10"):
    writer = PdfWriter()
    page = writer.add_blank_page(600, 800)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 700 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = stream
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def extract(upload, payload=None):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", name="submit_result",
            input=payload or facts().model_dump(exclude={"sources", "extraction_id"}))])
    return ClaudeGateway(client=client).extract(upload)


def test_real_pdf_text_match_from_mock_extraction_to_saved_record(tmp_path):
    extracted = extract(validate_upload(pdf(), "synthetic.pdf"))
    source = extracted.sources[0]
    assert source.verification == "text_match" and source.page == 1
    assert source.excerpt == "WBC 8 10^9/L 4-10"
    kb = KnowledgeBase(tmp_path / "chroma")
    model = Mock()
    record = finish(extracted, prepare(extracted, kb), model)
    assert not model.analyze.called  # matching report text does not authenticate KB notes
    store = HistoryStore(tmp_path / "history.sqlite3")
    store.save(record)
    loaded, rejected = store.load()
    assert not rejected and loaded[0].extracted.sources == extracted.sources


@pytest.mark.parametrize("pages", [["WBC 18 10^9/L 4-10"], ["WBC 8 10^9/L 4-10", "WBC 8 10^9/L 4-10"],
    ["SYNTHETIC_IDENTIFIER WBC 8 10^9/L 4-10"], ["WBC\n8\n10^9/L\n4-10"], [""]])
def test_ambiguous_inexact_and_identifying_lines_do_not_become_evidence(pages):
    report = facts()
    attach_text_matches(report, pages)
    source = report.sources[0]
    assert source.verification == "unverified"
    assert source.excerpt is source.page is source.location is None


def test_image_and_model_claimed_locations_are_not_verified():
    upload = ValidatedUpload(b"mock-only-image", "image/png")
    report = extract(upload)
    assert report.sources[0].origin == "model_extraction"
    assert report.sources[0].page is None
    payload = facts().model_dump()  # forbidden app-owned identity/source fields
    with pytest.raises(ModelError, match="structural"):
        extract(upload, payload)


def test_duplicate_names_have_distinct_stable_ids():
    raw = facts().indicators[0]
    report = ExtractedReport(indicators=[raw, raw.model_copy(deep=True)])
    first = prepare(report, SyntheticKnowledge())
    second = prepare(report, SyntheticKnowledge())
    assert len({r.observation_id for r in first}) == 2
    assert [r.observation_id for r in first] == [r.observation_id for r in second]
    assert first[0].observation_id != prepare(facts(), SyntheticKnowledge())[0].observation_id
    attach_text_matches(report, ["WBC 8 10^9/L 4-10"])
    assert all(s.page is None for s in report.sources)


def test_correction_and_conversion_keep_original_source(tmp_path):
    extracted = facts()
    after = extracted.indicators[0].model_copy(deep=True)
    after.raw_value = "9"
    change = Correction(row_id="row-1", before=extracted.indicators[0], after=after,
        reason="Synthetic correction", confirmed_from_report=True)
    kb = KnowledgeBase(tmp_path / "chroma")
    record = finish(extracted, prepare(extracted, kb, [change]), Mock(), corrections=[change])
    source = record.extracted.sources[0]
    assert source.raw.raw_value == "8" and record.checked[0].original.raw_value == "9"
    assert source.observation_id == record.checked[0].observation_id
    groups, _ = trend_groups([record], "WBC", "My reports", "live")
    point = groups["10^9/L"][0]
    assert point["Observation ID"] == source.observation_id and point["Extraction value"] == "8"
    assert point["Value"] == 9 and point["Conversion factor"] == 1
    assert record.checked[0].decision.state == "insufficient_evidence"


def test_all_26_notes_retain_unverified_versioned_metadata_and_block_live(tmp_path):
    kb = KnowledgeBase(tmp_path / "chroma", use_curated=False)
    inventory = json.loads((KB_PATH / "provenance.json").read_text())
    assert set(inventory) == kb.ids and len(kb.ids) == 26
    for code in kb.ids:
        evidence = kb.retrieve(code)
        meta = evidence.metadata
        assert meta.entry_id == "kb:" + code and meta.version == "sha256:" + evidence.sha256
        assert meta.review_status == "unverified" and not meta.sources
        assert meta.reviewer is meta.reviewed_on is None
    assert kb.retrieve("IBIL").metadata.entry_id == "kb:DBIL"
    report = facts()
    model = Mock()
    record = finish(report, prepare(report, kb), model)
    assert record.analysis is None and not model.analyze.called
    assert "unverified_knowledge" in [r.code for r in record.checked[0].decision.reasons]
    assert record.checked[0].evidence is not None  # retained, not falsely called used


def test_revision_refresh_preserves_history_snapshot_and_missing_metadata_blocks(tmp_path):
    directory = tmp_path / "kb"
    directory.mkdir()
    path = directory / "WBC.txt"
    path.write_text("Indicator: WBC\n" + "Synthetic unverified note. " * 5)
    kb = KnowledgeBase(tmp_path / "chroma", directory)
    report = facts()
    record = finish(report, prepare(report, kb), Mock())
    old = record.checked[0].evidence.model_dump()
    path.write_text(path.read_text() + " New synthetic revision.")
    updated = KnowledgeBase(tmp_path / "chroma", directory).retrieve("WBC")
    assert updated.metadata.version != old["metadata"]["version"]
    assert record.checked[0].evidence.model_dump() == old
    assert "Missing provenance" in updated.metadata.audit_note


@pytest.mark.parametrize("version", [2, 3])
def test_legacy_history_unknown_evidence_and_deterministic_migration(tmp_path, version):
    kb = KnowledgeBase(tmp_path / "chroma")
    report = facts()
    data = finish(report, prepare(report, kb), Mock()).model_dump()
    data["schema_version"] = version
    data["extracted"].pop("sources")
    data["extracted"].pop("extraction_id")
    for row in data["checked"]:
        row.pop("observation_id")
        row["evidence"].pop("metadata")
    a, b = ReportRecord.model_validate(data), ReportRecord.model_validate(data)
    assert a == b and a.schema_version == 4 and a.analysis is None
    source = a.extracted.sources[0]
    assert source.origin == "unknown" and source.page is source.excerpt is None
    assert source.observation_id == a.checked[0].observation_id
    assert a.checked[0].decision.state == "insufficient_evidence"


def test_demo_presets_cannot_unlock_live_model(tmp_path):
    kb = KnowledgeBase(tmp_path / "chroma")
    demo = demo_reports(kb)[0]
    assert demo.analysis.explanations and all(s.origin == "synthetic" for s in demo.extracted.sources)
    client = Mock()
    assert not ClaudeGateway(client=client).analyze(demo.checked).explanations
    assert not client.messages.create.called
    model = Mock()
    record = finish(demo.extracted, demo.checked, model)
    assert record.analysis is None and not model.analyze.called


@pytest.mark.parametrize("field", ["observation", "snapshot", "version"])
def test_tampered_links_fail_history_validation(tmp_path, field):
    report = facts()
    kb = KnowledgeBase(tmp_path / "chroma")
    payload = finish(report, prepare(report, kb), Mock()).model_dump()
    if field == "observation":
        payload["checked"][0]["observation_id"] = "other"
    elif field == "snapshot":
        payload["extracted"]["sources"][0]["raw"]["raw_value"] = "100"
    else:
        payload["checked"][0]["evidence"]["metadata"]["version"] = "invented"
    with pytest.raises(ValidationError):
        ReportRecord.model_validate(payload)


@pytest.mark.parametrize("payload", [{"schema_version": 3}, {"schema_version": 2, "id": "synthetic", "extracted": {}, "checked": [None]}])
def test_malformed_legacy_records_are_validation_errors(payload):
    with pytest.raises(ValidationError):
        ReportRecord.model_validate(payload)


def test_malformed_inventory_stays_unverified(tmp_path):
    directory = tmp_path / "kb"
    directory.mkdir()
    (directory / "WBC.txt").write_text("Indicator: WBC\n" + "Synthetic text. " * 10)
    (directory / "provenance.json").write_text("[]")
    kb = KnowledgeBase(tmp_path / "chroma", directory)
    assert kb.retrieve("WBC").metadata.review_status == "unverified"
