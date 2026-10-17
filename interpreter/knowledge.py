"""Chroma document retrieval by normalized IDs, sized for a 26-note corpus."""
from hashlib import sha256
from pathlib import Path

from interpreter.models import Evidence

KB_PATH = Path(__file__).resolve().parents[1] / "knowledge_base"
# IBIL shares a legacy note, but retains a distinct analyte ID.
SOURCE_MAP = {"IBIL": "DBIL"}


class KnowledgeBase:
    def __init__(self, path: Path, kb_path: Path = KB_PATH):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection("indicator_notes_v2", embedding_function=None)
        files = sorted(kb_path.glob("*.txt"))
        self.ids = {f.stem for f in files}
        # Explicit dummy vectors satisfy Chroma storage; never used for similarity.
        # Exact keyed retrieval is intentional, not a semantic embedding model.
        for file in files:
            text = file.read_text(encoding="utf-8")
            self.collection.upsert(ids=[file.stem], documents=[text], embeddings=[[1.0]],
                                   metadatas=[{"sha256": sha256(text.encode()).hexdigest()}])
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
        return Evidence(source_id=f"knowledge_base/{source}.txt", indicator_id=code,
                        text=found["documents"][0], sha256=found["metadatas"][0]["sha256"])
