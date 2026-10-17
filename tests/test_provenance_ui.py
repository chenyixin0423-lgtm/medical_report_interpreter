from pathlib import Path
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest

from interpreter import ui
from interpreter.models import ExtractedReport
from interpreter.tracking import attach_text_matches

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_synthetic_evidence_view_and_live_unverified_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-mock-only")
    model = Mock()
    monkeypatch.setattr(ui, "ClaudeGateway", lambda: model)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[1].set_value("Detailed Results").run()
    assert not app.exception
    texts = "\n".join(x.value for x in app.text)
    assert "Observation ID:" in texts and "Knowledge ID: kb:WBC" in texts
    assert "PDF page: Unknown" in texts and "Synthetic fixture: no real patient document" in texts
    assert "Clinical expert review: not performed" in texts
    assert "Review status: source_checked" in texts
    # Retained advice is opt-in, never presented as an endorsed explanation.
    note = next(c for c in app.checkbox if c.key.startswith("note-"))
    note.check().run()
    assert not app.exception
    assert any("Indicator: WBC" in x.value for x in app.text)
    app.radio[0].set_value("Live analysis").run()
    facts = ExtractedReport(indicators=[{"name": "WBC", "raw_value": "8", "unit": "10^9/L",
        "reference": {"text": "4-10", "unit": "10^9/L"}}])
    attach_text_matches(facts, ["WBC 8 10^9/L 4-10"])
    app.session_state["pending"] = facts
    app.radio[1].set_value("Upload & Analyze").run()
    app.checkbox(key="review_facts").check().run()
    next(b for b in app.button if b.label == "Analyze reviewed facts").click().run()
    assert not app.exception and not model.analyze.called
    app.radio[1].set_value("Detailed Results").run()
    texts = "\n".join(x.value for x in app.text)
    assert "PDF page: 1" in texts and "WBC 8 10^9/L 4-10" in texts
    assert "Use: retrieved only" in texts
    record = app.session_state["live_records"][0]
    assert record.checked[0].decision.state == "insufficient_evidence"
    assert record.extracted.sources[0].observation_id == record.checked[0].observation_id
    assert not app.exception
