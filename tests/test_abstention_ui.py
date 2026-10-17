from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from interpreter import ui
from interpreter.models import ExtractedReport, GeneratedAnalysis

APP = Path(__file__).resolve().parents[1] / "app.py"


def element(elements, label):
    return next(x for x in elements if x.label == label)


def test_mixed_report_correction_form_and_partial_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-key")
    model = Mock()
    def respond(rows, question):
        return GeneratedAnalysis.model_validate({"explanations": [
            {"row_id": r.row_id, "text": "Synthetic eligible result", "source_ids": [r.evidence.source_id]}
            for r in rows], "limitations": []})
    model.analyze.side_effect = respond
    monkeypatch.setattr(ui, "ClaudeGateway", lambda: model)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[0].set_value("Live analysis").run()
    app.session_state["pending"] = ExtractedReport.model_validate({"report_date": "2026-01-01", "indicators": [
        {"name": "WBC", "raw_value": "1.5 or 15", "unit": "10^9/L", "uncertain": True,
         "reference": {"text": "4-10", "unit": "10^9/L"}},
        {"name": "HGB", "raw_value": "140", "unit": "g/L", "reference": {"text": "130-170", "unit": "g/L"}},
        {"name": "GLU", "raw_value": "999", "unit": "mmol/L", "reference": {"text": None, "unit": "mmol/L"}},
        {"name": "Synthetic unknown", "raw_value": "9999", "unit": "U/L", "reference": {"text": "0-1", "unit": "U/L"}},
    ]})
    app.radio[1].set_value("Upload & Analyze").run()
    assert not app.exception
    assert element(app.button, "Analyze reviewed facts").disabled
    element(app.text_input, "Value as printed").set_value("1.5")
    element(app.checkbox, "Text is still unclear").uncheck()
    element(app.text_input, "Reason for correction (no identifying information)").set_value("Synthetic source confirms decimal")
    # Applying an unconfirmed correction must NOT make the row interpretable.
    element(app.button, "Apply correction and revalidate").click().run()
    assert not app.exception
    frame = app.dataframe[-1].value
    assert frame.iloc[0]["Readiness"] == "needs_review"
    element(app.checkbox, "I checked these changed fields against the original report").check()
    element(app.button, "Apply correction and revalidate").click().run()
    assert not app.exception
    assert app.dataframe[-1].value.iloc[0]["Readiness"] == "interpretable"
    app.checkbox(key="review_facts").check().run()
    element(app.button, "Analyze reviewed facts").click().run()
    assert not app.exception
    record = app.session_state["live_records"][0]
    assert [r.decision.state for r in record.checked] == ["interpretable", "interpretable", "insufficient_evidence", "unsupported"]
    assert record.extracted.indicators[0].raw_value == "1.5 or 15"
    assert record.checked[0].original.raw_value == "1.5"
    assert [r.row_id for r in model.analyze.call_args.args[0]] == ["row-1", "row-2"]
    app.radio[1].set_value("Dashboard").run()
    assert [m.value for m in app.metric][-4:] == ["2", "0", "1", "1"]
    assert next(m for m in app.metric if m.label == "Eligible outside range").value == "1"
    for page in ["Detailed Results", "History", "Trends"]:
        app.radio[1].set_value(page).run()
        assert not app.exception
