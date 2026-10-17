from pathlib import Path
from streamlit.testing.v1 import AppTest
from interpreter import ui
from tests.test_abstention import gateway
from tests.test_curated import report


def test_source_checked_live_ui_requires_specimen_correction(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-mock-only")
    model = gateway()
    monkeypatch.setattr(ui, "ClaudeGateway", lambda: model)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    app.radio[0].set_value("Live analysis").run()
    facts = report(specimen="unknown")
    app.session_state["pending"] = facts
    app.radio[1].set_value("Upload & Analyze").run()
    assert app.dataframe[-1].value.iloc[0]["Readiness"] == "insufficient_evidence"
    next(s for s in app.selectbox if s.label == "Specimen as reported").set_value("whole_blood")
    next(t for t in app.text_input if t.label == "Reason for correction (no identifying information)").set_value("Synthetic sample states whole blood")
    next(c for c in app.checkbox if c.label == "I checked these changed fields against the original report").check()
    next(b for b in app.button if b.label == "Apply correction and revalidate").click().run()
    assert not app.exception
    assert app.dataframe[-1].value.iloc[0]["Readiness"] == "interpretable"
    app.checkbox(key="review_facts").check().run()
    next(b for b in app.button if b.label == "Analyze reviewed facts").click().run()
    assert not app.exception and model.analyze.call_count == 1
    app.radio[1].set_value("Detailed Results").run()
    text = "\n".join(t.value for t in app.text)
    assert "source_checked" in text and "Clinical expert review: not performed" in text
    assert "https://medlineplus.gov/lab-tests/white-blood-count-wbc/" in text
    record = app.session_state["live_records"][0]
    assert record.extracted.sources[0].raw.specimen == "unknown"
    assert record.checked[0].original.specimen == "whole_blood"
    assert not app.exception
