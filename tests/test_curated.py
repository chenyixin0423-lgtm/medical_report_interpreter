"""Source-checked corpus routing with synthetic reports and mocked paid APIs."""
import json
import shutil
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from interpreter.knowledge import KnowledgeBase, KB_PATH
from interpreter.curated import entry_from
from interpreter.models import ExtractedReport, Correction, ReportRecord
from interpreter.pipeline import prepare, finish
from interpreter.catalog import normalize
from interpreter.llm import ClaudeGateway
from interpreter.storage import HistoryStore
from tests.test_abstention import gateway


def report(code="WBC", value="8", unit="10^9/L", specimen="blood", fasting="unknown"):
    return ExtractedReport(indicators=[{"name": code, "raw_value": value, "unit": unit,
        "specimen": specimen, "fasting": fasting, "reference": {"text": "4-10", "unit": unit}}])


@pytest.fixture
def kb(tmp_path):
    return KnowledgeBase(tmp_path / "chroma")


def test_corpus_contract_and_all_supported_directions(kb):
    assert len(kb.curated_ids) == 16 and not kb.invalid_entries
    for code in kb.curated_ids:
        evidence = kb.retrieve(code)
        entry = entry_from(evidence)
        meta = evidence.metadata
        assert meta.review_status == "source_checked"
        assert meta.reviewer is meta.reviewed_on is None
        assert entry.clinical_review == "not_performed"
        assert meta.source_checked_on == "2026-10-17"
        assert all(s.url.startswith("https://medlineplus.gov/lab-tests/") for s in meta.sources)
        assert all(normalize(a) == code for a in [entry.name_en, entry.name_zh, *entry.aliases])
        for value, direction in [("8", "within_range"), ("12", "high"), ("2", "low")]:
            facts = report(code, value, entry.units[0], entry.specimens[0])
            model = gateway()
            record = finish(facts, prepare(facts, kb), model)
            supported = direction == "within_range" or getattr(entry, direction) is not None
            assert model.analyze.called == supported, (code, direction)
            assert (record.checked[0].decision.state == "interpretable") == supported
            if supported:
                assert record.analysis.explanations[0].source_ids == [evidence.source_id]
            else:
                assert "knowledge_context" in [x.code for x in record.checked[0].decision.reasons]


@pytest.mark.parametrize("specimen,unit", [("unknown", "10^9/L"), ("urine", "10^9/L"),
    ("serum", "10^9/L"), ("blood", "10^12/L")])
def test_context_blocks_otherwise_valid_rows(kb, specimen, unit):
    facts = report(specimen=specimen, unit=unit)
    model = gateway()
    record = finish(facts, prepare(facts, kb), model)
    assert not model.analyze.called and record.analysis is None
    assert record.checked[0].evidence is not None


def test_fasting_branches_and_no_fasting_inference(kb):
    for context in ("unknown", "fasting", "nonfasting"):
        rows = prepare(report("FBG", unit="mmol/L", fasting=context), kb)
        assert rows[0].decision.state == "interpretable"
        entry = entry_from(rows[0].evidence)
        assert entry.fasting_notes[context] in rows[0].evidence.selected_text
    assert "Fasting status is unknown" in prepare(report("FBG", unit="mmol/L"), kb)[0].evidence.selected_text


def test_no_urea_bun_or_mass_molar_guessing(kb):
    assert normalize("urea") is None
    facts = report("BUN", unit="mmol/L")
    model = gateway()
    assert finish(facts, prepare(facts, kb), model).analysis is None
    assert not model.analyze.called


def test_partial_analysis_and_source_linked_correction(kb, tmp_path):
    facts = report(specimen="unknown")
    facts = ExtractedReport(indicators=facts.indicators + report("TG", "2", "mg/dL").indicators
                            + report("MCV", "8", "fL").indicators)
    assert all(r.decision.state != "interpretable" for r in prepare(facts, kb))
    before = facts.indicators[0]
    after = before.model_copy(update={"specimen": "whole_blood"})
    correction = Correction(row_id="row-1", before=before, after=after, reason="Synthetic source confirms whole blood", confirmed_from_report=True)
    model = gateway()
    record = finish(facts, prepare(facts, kb, [correction]), model, corrections=[correction])
    assert [r.row_id for r in model.analyze.call_args.args[0]] == ["row-1"]
    assert record.extracted.sources[0].raw.specimen == "unknown"
    assert record.checked[0].original.specimen == "whole_blood"
    assert record.checked[0].observation_id == facts.sources[0].observation_id
    store = HistoryStore(tmp_path / "h.sqlite3")
    store.save(record)
    assert store.load() == ([record], 0)
    correction.confirmed_from_report = False
    assert prepare(facts, kb, [correction])[0].decision.state == "needs_review"


def test_gateway_sends_only_selected_branch_and_keeps_real_source(kb):
    rows = prepare(report(value="12"), kb)
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", name="submit_result", input={"explanations": [
            {"row_id": "row-1", "text": "Synthetic mock result", "source_ids": [rows[0].evidence.source_id]}], "limitations": []})])
    ClaudeGateway(client=client).analyze(rows)
    payload = json.loads(client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"])
    sent = payload["checked_indicators"][0]["evidence"]
    entry = entry_from(rows[0].evidence)
    assert entry.high in sent["text"] and entry.low not in sent["text"]
    assert sent["metadata"]["sources"][0]["url"] == entry.sources[0].url
    rows[0].original.specimen = "urine"  # stale selection cannot bypass the gateway
    client.reset_mock()
    assert ClaudeGateway(client=client).analyze(rows).explanations == []
    assert not client.messages.create.called


def test_modified_corpus_not_silently_source_checked(tmp_path):
    target = tmp_path / "kb"
    shutil.copytree(KB_PATH, target)
    kb = KnowledgeBase(tmp_path / "chroma", target)
    original = kb.retrieve("WBC")
    path = target / "curated" / "WBC.json"
    content = json.loads(path.read_text(encoding="utf-8"))
    content["high"] = "Unverified synthetic alteration."
    path.write_text(json.dumps(content), encoding="utf-8")
    refreshed = KnowledgeBase(tmp_path / "chroma", target)
    assert "WBC" in refreshed.invalid_entries and "WBC" not in refreshed.curated_ids
    assert refreshed.retrieve("WBC").provenance == "unverified_project_note"
    assert refreshed.retrieve("WBC").metadata.review_status == "unverified"
    assert original.metadata.review_status == "source_checked"  # historical snapshot unchanged


def test_history_rejects_changed_selected_context(kb):
    facts = report()
    record = finish(facts, prepare(facts, kb), gateway())
    data = record.model_dump()
    data["checked"][0]["evidence"]["selected_text"] = "Unsupported invented explanation"
    with pytest.raises(ValueError):
        ReportRecord.model_validate(data)


def test_known_urine_results_never_merge_into_blood_trends(kb):
    from interpreter.trends import trend_groups
    records = []
    for specimen in ("blood", "urine"):
        facts = report("GLU", unit="mmol/L", specimen=specimen)
        facts.report_date = "2026-01-01"
        records.append(finish(facts, prepare(facts, kb), gateway()))
    groups, excluded = trend_groups(records, "GLU", "My reports", "live")
    assert len(groups["mmol/L"]) == 1 and len(excluded) == 1
    assert "Specimen" in excluded[0]["Reason"]
