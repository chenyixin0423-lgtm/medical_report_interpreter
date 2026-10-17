"""Opt-in single-user SQLite storage; parameterized SQL and no source filenames."""
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from interpreter.models import ReportRecord


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def save(self, record: ReportRecord):
        if record.mode != "live":
            raise ValueError("Synthetic examples must remain separate from live history.")
        with self.connect() as db:
            db.execute("INSERT INTO reports VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                       (record.id, record.created_at, record.model_dump_json()))

    def load(self):
        records, rejected = [], 0
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM reports ORDER BY created_at DESC").fetchall()
        for (payload,) in rows:
            try:
                records.append(ReportRecord.model_validate_json(payload))
            except ValidationError:
                rejected += 1
        return records, rejected

    def delete(self, record_id: str):
        with self.connect() as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DELETE FROM reports WHERE id=?", (record_id,))
