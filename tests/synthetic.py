"""Fabricated source metadata solely to exercise the reviewed-content code path.

No actual medical source is represented; .invalid domains cannot be real citations.
"""
from hashlib import sha256
from interpreter.models import Evidence, KnowledgeMetadata, KnowledgeSource


class SyntheticKnowledge:
    def retrieve(self, code):
        if code not in {"WBC", "HGB", "GLU", "ALT"}:
            return None
        text = f"Indicator: {code}\nSynthetic educational testing note only. This fabricated note exercises software routing and does not describe patient care."
        digest = sha256(text.encode()).hexdigest()
        return Evidence(source_id=f"knowledge_base/{code}.txt", indicator_id=code,
            text=text, sha256=digest, metadata=KnowledgeMetadata(entry_id=f"kb:{code}", version="sha256:" + digest,
            review_status="reviewed", sources=[KnowledgeSource(name="SYNTHETIC TEST FIXTURE — not a medical source",
                url="https://fixture.invalid/", scope="Software test only")], applicability="Software test only",
            reviewer="Synthetic test fixture", reviewed_on="2026-01-01"))
