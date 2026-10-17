"""Chroma document retrieval by normalized IDs, sized for a 26-note corpus."""
from hashlib import sha256
from pathlib import Path
import json

from interpreter.models import Evidence, KnowledgeMetadata

KB_PATH = Path(__file__).resolve().parents[1] / "knowledge_base"
# IBIL shares a legacy note, but retains a distinct analyte ID.
SOURCE_MAP = {"IBIL": "DBIL"}


class KnowledgeBase:
    def __init__(self, path: Path, kb_path: Path = KB_PATH):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection("indicator_notes_v3", embedding_function=None)
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
                                   metadatas=[{"sha256": digest, "provenance_json": meta.model_dump_json()}])
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
        return Evidence(source_id=f"knowledge_base/{source}.txt", indicator_id=code,
                        text=found["documents"][0], sha256=found["metadatas"][0]["sha256"],
                        metadata=KnowledgeMetadata.model_validate_json(raw_metadata) if raw_metadata else None)
