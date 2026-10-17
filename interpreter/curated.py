"""Source-checked summaries, not clinical review. Deterministic context selection."""
import json
from hashlib import sha256
from urllib.parse import urlparse
from datetime import date
from typing import Literal
from pydantic import Field, model_validator

from interpreter.models import Model, KnowledgeSource, KnowledgeMetadata, Evidence
from interpreter.units import unit_key


class CuratedEntry(Model):
    code: str
    name_en: str
    name_zh: str
    aliases: list[str]
    revision: str
    source_checked_on: str
    verification_method: Literal["AI-assisted comparison with the linked public source; not clinician review"]
    clinical_review: Literal["not_performed"]
    sources: list[KnowledgeSource] = Field(min_length=1)
    units: list[str] = Field(min_length=1)
    specimens: list[str] = Field(min_length=1)
    scope: str
    overview: str
    high: str | None
    low: str | None
    caveats: str
    fasting_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def checked_source(self):
        date.fromisoformat(self.source_checked_on)
        from interpreter.catalog import normalize
        if any(normalize(n) != self.code for n in [self.name_en, self.name_zh, *self.aliases]):
            raise ValueError("Curated aliases disagree with catalog.")
        for source in self.sources:
            if urlparse(source.url).hostname != "medlineplus.gov":
                raise ValueError("This corpus requires an inspected MedlinePlus source.")
        return self


def to_evidence(entry):
    # Hash includes applicability, full paraphrases, links and checking metadata.
    text = f"Indicator: {entry.code}\n" + entry.model_dump_json()
    digest = sha256(text.encode()).hexdigest()
    return Evidence(source_id=f"knowledge_base/curated/{entry.code}.json", indicator_id=entry.code,
        text=text, sha256=digest, provenance="source_checked_summary",
        metadata=KnowledgeMetadata(entry_id="kb:" + entry.code, version="sha256:" + digest,
            review_status="source_checked", sources=entry.sources, applicability=entry.scope,
            source_checked_on=entry.source_checked_on, verification_method=entry.verification_method,
            audit_note="Source text checked for these bounded paraphrases. Clinical expert review not performed."))


def entry_from(evidence):
    entry = CuratedEntry.model_validate_json(evidence.text.split("\n", 1)[1])
    expected = to_evidence(entry)
    if (evidence.source_id != expected.source_id or evidence.indicator_id != entry.code
            or evidence.sha256 != expected.sha256 or evidence.metadata != expected.metadata):
        raise ValueError("Curated snapshot or provenance mismatch.")
    return entry


def select_text(entry, row):
    raw = row.original
    if raw.specimen not in entry.specimens:
        return None, "Specimen is unknown or outside the source summary's blood-test scope."
    if unit_key(raw.unit) not in {unit_key(u) for u in entry.units}:
        return None, "The unit is outside this analyte's checked knowledge scope."
    if row.status not in {"high", "low", "within_range"}:
        return None, "A reliable printed-range comparison is unavailable."
    directional = getattr(entry, row.status) if row.status in {"high", "low"} else "The value lies within the supplied laboratory interval; that comparison alone cannot establish health."
    if directional is None:
        return None, f"The checked source summary does not support an explanation of {row.status} results for this indicator."
    pieces = [entry.overview, directional, entry.caveats, entry.fasting_notes.get(raw.fasting, ""),
              "Educational possibilities only, not a diagnosis, risk score, treatment target or instruction. No clinical expert review."]
    return "\n".join(x for x in pieces if x), None


def context_problem(row):
    try:
        entry = entry_from(row.evidence)
        text, problem = select_text(entry, row)
        return problem or ("Selected knowledge does not match the current report context." if row.evidence.selected_text != text else None)
    except (ValueError, IndexError):
        return "The structured knowledge snapshot failed its integrity checks."
