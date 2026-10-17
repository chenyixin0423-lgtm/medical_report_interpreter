from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from interpreter.catalog import normalize
from interpreter.models import ExtractedReport, GeneratedAnalysis, Measurement, ReferenceRange
from interpreter.validation import check_report, numeric, range_status, validate_analysis
from interpreter.units import convert


def report(value="8", unit="10^9/L", bounds="4-10", **kwargs):
    return ExtractedReport(indicators=[Measurement(name="白细胞(WBC)", raw_value=value, unit=unit,
        reference=ReferenceRange(text=bounds, unit=unit), **kwargs)])


@pytest.mark.parametrize("name,code", [("白细胞(WBC)", "WBC"), (" haemoglobin ", "HGB"),
    ("糖化血红蛋白", "HbA1c"), ("SCr", "CREA"), ("间接胆红素", "IBIL"),
    ("urea", None), ("WBC antibody", None), ("RBC(WBC)", None), ("NEUT%", "NEUT")])
def test_aliases(name, code):
    assert normalize(name) == code


@pytest.mark.parametrize("value,bounds,expected", [(8, "4–10", "within_range"), (10, "<10", "high"),
    (10, "≤10", "within_range"), (3, "4-10", "low"), (12, "4-10", "high"),
    (8, "male 4-10 female 3-9", "unknown"), (8, "10-4", "unknown"), (-1, "-2 - 3", "within_range")])
def test_ranges(value, bounds, expected):
    assert range_status(value, bounds) == expected


@pytest.mark.parametrize("value", ["<5", "positive", "1,000", "NaN", "1e3", None])
def test_non_numeric(value):
    assert numeric(value) is None


def test_conflicts_and_unknowns():
    assert check_report(report(report_flag="high"))[0].status == "conflict"
    assert check_report(report(uncertain=True))[0].status == "unknown"
    assert check_report(report(bounds=None))[0].status == "unknown"
    assert check_report(report(unit=None))[0].status == "unknown"


def test_strict_schema():
    raw = report().model_dump()
    raw["urgency"] = "urgent"
    with pytest.raises(ValidationError):
        ExtractedReport.model_validate(raw)
    raw.pop("urgency")
    raw["indicators"][0]["raw_value"] = 8
    with pytest.raises(ValidationError):
        ExtractedReport.model_validate(raw)


def test_units():
    assert convert(14, "g/dL", "g/L") == 140
    assert convert(0.42, "L/L", "%") == 42
    assert convert(6, "K/µL", "10^9/L") == 6
    assert convert(100, "µmol/L", "mmol/L") == pytest.approx(.1)
    for a, b in [("mg/dL", "mmol/L"), ("%", "10^9/L"), ("mystery", "mystery")]:
        with pytest.raises(ValueError):
            convert(10, a, b)


def test_analysis_rejects_invented_sources():
    rows = check_report(report())
    analysis = GeneratedAnalysis.model_validate({"explanations": [{"row_id": "row-1", "text": "Test",
        "source_ids": ["invented journal"]}], "limitations": []})
    with pytest.raises(ValueError):
        validate_analysis(analysis, rows)


def test_mock_claude_extraction():
    from interpreter.llm import ClaudeGateway, ModelError
    from interpreter.security import ValidatedUpload
    client = Mock()
    block = SimpleNamespace(type="tool_use", name="submit_result", input=report().model_dump())
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[block])
    gateway = ClaudeGateway(client=client)
    assert gateway.extract(ValidatedUpload(b"fake for mocked API", "image/png")) == report()
    request = client.messages.create.call_args.kwargs
    assert request["tools"][0]["input_schema"]["additionalProperties"] is False
    client.messages.create.return_value.stop_reason = "max_tokens"
    with pytest.raises(ModelError, match="incomplete"):
        gateway.extract(ValidatedUpload(b"", "image/png"))
    client.messages.create.side_effect = RuntimeError("SECRET patient data sk-secret")
    with pytest.raises(ModelError) as exc:
        gateway.extract(ValidatedUpload(b"", "image/png"))
    assert "SECRET" not in str(exc.value)


def test_mock_claude_analysis_includes_only_row_evidence():
    from interpreter.llm import ClaudeGateway
    client = Mock()
    payload = {"explanations": [{"row_id": "row-1", "text": "No knowledge coverage.", "source_ids": []}], "limitations": []}
    client.messages.create.return_value = SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", name="submit_result", input=payload)])
    rows = check_report(report())
    result = ClaudeGateway(client=client).analyze(rows, "Explain this")
    validate_analysis(result, rows)
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]
    assert "row-1" in sent and "Explain this" in sent


def test_incomplete_duplicate_and_extra_analysis_rows():
    rows = check_report(report())
    payload = {"explanations": [{"row_id": "wrong", "text": "Text", "source_ids": []}], "limitations": []}
    with pytest.raises(ValueError):
        validate_analysis(GeneratedAnalysis.model_validate(payload), rows)
    payload["explanations"][0]["row_id"] = "row-1"
    payload["explanations"].append(payload["explanations"][0].copy())
    with pytest.raises(ValueError):
        validate_analysis(GeneratedAnalysis.model_validate(payload), rows)


def test_reference_unit_conflict():
    facts = report()
    facts.indicators[0].reference.unit = "g/L"
    assert check_report(facts)[0].status == "unknown"
