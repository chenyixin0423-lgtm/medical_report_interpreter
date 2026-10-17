from pathlib import Path

from streamlit.testing.v1 import AppTest

from interpreter.models import ExtractedReport, ReportRecord
from interpreter.storage import HistoryStore
from interpreter.validation import check_report


def test_opt_in_save_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("MRI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MRI_ENABLE_LOCAL_HISTORY", "true")
    facts = ExtractedReport.model_validate({"report_date": "2026-01-01", "indicators": [{
        "name": "HGB", "raw_value": "140", "unit": "g/L", "reference": {"text": "130-170", "unit": "g/L"}}]})
    record = ReportRecord(mode="live", facts_reviewed=True, extracted=facts, checked=check_report(facts))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    app.radio[0].set_value("Live analysis").run()
    app.session_state["live_records"] = [record]
    app.radio[1].set_value("History").run()
    assert not app.exception
    [b for b in app.button if b.label == "Save locally"][0].click().run()
    store = HistoryStore(tmp_path / "history.sqlite3")
    assert len(store.load()[0]) == 1
    [b for b in app.button if b.label == "Delete"][0].click().run()
    assert not app.exception
    assert store.load()[0] == []
    assert not app.session_state["live_records"]
