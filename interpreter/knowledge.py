"""Exact Chroma retrieval with source-checked, context-selected educational summaries."""
from hashlib import sha256
from pathlib import Path
import json

from interpreter.models import Evidence, KnowledgeMetadata

KB_PATH = Path(__file__).resolve().parents[1] / "knowledge_base"
# IBIL shares a legacy note, but retains a distinct analyte ID.
SOURCE_MAP = {"IBIL": "DBIL"}


class KnowledgeBase:
    def __init__(self, path: Path, kb_path: Path = KB_PATH, *, use_curated=True):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection("indicator_notes_v4" if use_curated else "indicator_notes_v3", embedding_function=None)
        self.curated_ids, self.invalid_entries = set(), []
        try:
            inventory = json.loads((kb_path / "provenance.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            inventory = {}
        if not isinstance(inventory, dict):
            inventory = {}
        files = sorted(kb_path.glob("*.txt"))
        self.ids = {f.stem for f in files}
        # Explicit dummy vectors satisfy Chroma storage; never used for similarity.
        # Exact keyed retrieval is intentional, not a semantic embedding model.
        for file in files:
            text = file.read_text(encoding="utf-8")
            digest = sha256(text.encode()).hexdigest()
            details = inventory.get(file.stem, {})
            if not isinstance(details, dict) or not all(isinstance(v, str) for v in details.values()):
                details = {}
            # Inventory describes legacy content; it deliberately confers no authority.
            meta = KnowledgeMetadata(entry_id="kb:" + file.stem, version="sha256:" + digest,
                applicability=details.get("applicability", "Unknown; no applicability established."),
                audit_note=details.get("audit_note", "Missing provenance inventory. Source is unverified."))
            self.collection.upsert(ids=[file.stem], documents=[text], embeddings=[[1.0]],
                                   metadatas=[{"sha256": digest, "provenance_json": meta.model_dump_json(),
                                               "source_id": f"knowledge_base/{file.stem}.txt", "kind": "unverified_project_note"}])
        if use_curated:
            from interpreter.curated import CuratedEntry, to_evidence
            try:
                manifest = json.loads((kb_path / "curated" / "manifest.json").read_text(encoding="utf-8"))
            except (ValueError, OSError):
                manifest = {}
            if not isinstance(manifest, dict):
                manifest = {}
            for file in sorted((kb_path / "curated").glob("*.json")):
                if file.name == "manifest.json":
                    continue
                try:
                    raw = file.read_text(encoding="utf-8")
                    if manifest.get(file.stem) != sha256(raw.encode()).hexdigest():
                        raise ValueError("Content changed since source check; recheck before updating manifest.")
                    entry = CuratedEntry.model_validate_json(raw)
                    if entry.code != file.stem:
                        raise ValueError("Entry ID differs from filename.")
                    evidence = to_evidence(entry)
                except (ValueError, OSError):
                    self.invalid_entries.append(file.stem)
                    continue  # Fail closed; any old note remains unverified.
                self.collection.upsert(ids=[entry.code], documents=[evidence.text], embeddings=[[1.0]],
                    metadatas=[{"sha256": evidence.sha256, "provenance_json": evidence.metadata.model_dump_json(),
                                "source_id": evidence.source_id, "kind": evidence.provenance}])
                self.curated_ids.add(entry.code)
                self.ids.add(entry.code)
        stale = set(self.collection.get()["ids"]) - self.ids
        if stale:
            self.collection.delete(ids=sorted(stale))

    def retrieve(self, code: str | None) -> Evidence | None:
        if not code:
            return None
        source = SOURCE_MAP.get(code, code)
        if source not in self.ids:
            return None
        found = self.collection.get(ids=[source], include=["documents", "metadatas"])
        if not found["ids"]:
            return None
        raw_metadata = found["metadatas"][0].get("provenance_json")
        return Evidence(source_id=found["metadatas"][0].get("source_id", f"knowledge_base/{source}.txt"), indicator_id=code,
                        provenance=found["metadatas"][0].get("kind", "unverified_project_note"),
                        text=found["documents"][0], sha256=found["metadatas"][0]["sha256"],
                        metadata=KnowledgeMetadata.model_validate_json(raw_metadata) if raw_metadata else None)

    def retrieve_for(self, row):
        evidence = self.retrieve(row.canonical_id)
        if evidence and evidence.provenance == "source_checked_summary":
            from interpreter.curated import entry_from, select_text
            evidence.selected_text, _ = select_text(entry_from(evidence), row)
        return evidence
