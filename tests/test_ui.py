from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_demo_navigation_and_live_empty_states(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert [x.value for x in app.metric] == ["6", "1", "2", "4 / 6"]
    for page in ["Upload & Analyze", "Detailed Results", "History", "Trends"]:
        app.radio[1].set_value(page).run()
        assert not app.exception, page
    app.radio[0].set_value("Live analysis").run()
    for page in ["Dashboard", "Upload & Analyze", "Detailed Results", "History", "Trends"]:
        app.radio[1].set_value(page).run()
        assert not app.exception, page


def test_demo_hide_and_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path / "data"))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[1].set_value("History").run()
    app.button[0].click().run()
    assert len(app.session_state["demo_records"]) == 2
    [b for b in app.button if b.label == "Restore synthetic examples"][0].click().run()
    assert len(app.session_state["demo_records"]) == 3
    assert not app.exception


def test_live_review_and_mock_analysis(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from interpreter.models import ExtractedReport, GeneratedAnalysis
    from interpreter import ui
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-only")
    gateway = Mock()
    gateway.analyze.return_value = GeneratedAnalysis.model_validate({"explanations": [{
        "row_id": "row-1", "text": "<script>alert('x')</script> ![remote](https://invalid.example/pixel)",
        "source_ids": ["knowledge_base/WBC.txt"]}], "limitations": []})
    monkeypatch.setattr(ui, "ClaudeGateway", lambda: gateway)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[0].set_value("Live analysis").run()
    app.session_state["pending"] = ExtractedReport.model_validate({"report_date": "2026-01-01", "indicators": [{
        "name": "WBC", "raw_value": "8", "unit": "10^9/L", "reference": {"text": "4-10", "unit": "10^9/L"}}]})
    app.radio[1].set_value("Upload & Analyze").run()
    button = [b for b in app.button if b.label == "Analyze reviewed facts"][0]
    assert button.disabled
    app.checkbox(key="review_facts").check().run()
    [b for b in app.button if b.label == "Analyze reviewed facts"][0].click().run()
    assert not app.exception
    assert len(app.session_state["live_records"]) == 1
    assert any("<script>" in x.value for x in app.text)
    assert not any("<script>" in x.value for x in app.markdown)
    assert gateway.analyze.call_count == 1
