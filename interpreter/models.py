"""Strict contracts. Extracted strings are never replaced by generated explanations."""
from datetime import date, datetime, timezone
from typing import Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_max_length=4000, allow_inf_nan=False)


class ReferenceRange(Model):
    text: str | None = None
    unit: str | None = None
    context_required: bool = False
    context_confirmed: bool = False


class Measurement(Model):
    name: str = Field(min_length=1, max_length=150)
    raw_value: str | None
    unit: str | None
    reference: ReferenceRange
    report_flag: Literal["high", "low", "normal", "unknown"] = "unknown"
    uncertain: bool = False
    specimen: Literal["unknown", "blood", "whole_blood", "serum", "plasma", "urine", "other"] = "unknown"
    fasting: Literal["unknown", "fasting", "nonfasting"] = "unknown"


class ExtractionPayload(Model):
    report_date: str | None = None
    indicators: list[Measurement] = Field(min_length=1, max_length=200)
    warnings: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("report_date")
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("Use an unambiguous ISO date.")
        return value


class ReportSource(Model):
    observation_id: str
    row_id: str
    raw: Measurement
    origin: Literal["model_extraction", "unknown", "synthetic"] = "unknown"
    verification: Literal["unverified", "text_match", "synthetic"] = "unverified"
    excerpt: str | None = Field(default=None, max_length=500)
    page: int | None = Field(default=None, ge=1, le=20)
    location: str | None = None

    @model_validator(mode="after")
    def location_contract(self):
        if self.verification != "text_match" and (self.page is not None or self.location is not None or self.excerpt is not None):
            raise ValueError("Unverified or synthetic evidence cannot claim a document location/excerpt.")
        if self.verification == "text_match" and not (self.excerpt and self.page and self.location):
            raise ValueError("Text matches require a retained excerpt and location.")
        return self


class ExtractedReport(ExtractionPayload):
    extraction_id: str = Field(default_factory=lambda: str(uuid4()))
    sources: list[ReportSource] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def source_links(self):
        if not self.sources:
            self.sources = [ReportSource(observation_id=str(uuid5(NAMESPACE_URL, f"{self.extraction_id}/row-{i+1}")),
                row_id=f"row-{i+1}", raw=r.model_copy(deep=True)) for i, r in enumerate(self.indicators)]
        if len(self.sources) != len(self.indicators):
            raise ValueError("Every occurrence requires its own source snapshot.")
        for i, source in enumerate(self.sources):
            if source.row_id != f"row-{i+1}" or source.observation_id != str(uuid5(NAMESPACE_URL, f"{self.extraction_id}/row-{i+1}")):
                raise ValueError("Source occurrence identity mismatch.")
        return self


class KnowledgeSource(Model):
    name: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    scope: str = Field(min_length=1)


class KnowledgeMetadata(Model):
    entry_id: str
    version: str
    review_status: Literal["unverified", "reviewed", "source_checked"] = "unverified"
    sources: list[KnowledgeSource] = Field(default_factory=list)
    applicability: str = "Unknown; not established for patient interpretation."
    reviewer: str | None = None
    reviewed_on: str | None = None
    audit_note: str = "No traceable source or clinical review is recorded."
    source_checked_on: str | None = None
    verification_method: str | None = None

    @model_validator(mode="after")
    def review_contract(self):
        if self.review_status == "source_checked":
            if not (self.sources and self.source_checked_on and self.verification_method):
                raise ValueError("Source checking requires sources, date and method.")
            date.fromisoformat(self.source_checked_on)
        if self.review_status == "reviewed":
            if not (self.sources and self.reviewer and self.reviewed_on):
                raise ValueError("Reviewed content needs explicit sources and review details.")
            date.fromisoformat(self.reviewed_on)
        return self


class Evidence(Model):
    source_id: str
    indicator_id: str
    text: str
    provenance: Literal["unverified_project_note", "source_checked_summary"] = "unverified_project_note"
    sha256: str
    metadata: KnowledgeMetadata | None = None
    selected_text: str | None = None

    @model_validator(mode="after")
    def metadata_identity(self):
        if self.metadata and (self.metadata.entry_id != "kb:" + self.source_id.rsplit("/", 1)[-1].removesuffix(".txt").removesuffix(".json")
                              or self.metadata.version != "sha256:" + self.sha256):
            raise ValueError("Knowledge metadata identity/version integrity failed.")
        return self


Status = Literal["within_range", "high", "low", "unknown", "conflict"]

Readiness = Literal["interpretable", "needs_review", "insufficient_evidence", "unsupported"]


class DecisionReason(Model):
    code: str
    message: str
    action: str


class InterpretationDecision(Model):
    state: Readiness
    reasons: list[DecisionReason] = Field(min_length=1)
    scope: str = "Educational explanation only; not clinical verification or a risk grade."


class Correction(Model):
    row_id: str
    before: Measurement
    after: Measurement
    reason: str = Field(min_length=1, max_length=500)
    confirmed_from_report: bool = False


class CheckedIndicator(Model):
    row_id: str
    observation_id: str | None = None
    canonical_id: str | None
    display_name: str
    original: Measurement
    numeric_value: float | None = None
    status: Status = "unknown"
    issues: list[str] = Field(default_factory=list)
    evidence: Evidence | None = None
    knowledge_rejected: bool = False
    decision: InterpretationDecision | None = None


class Explanation(Model):
    row_id: str
    text: str = Field(min_length=1, max_length=1500)
    source_ids: list[str] = Field(max_length=3)


class GeneratedAnalysis(Model):
    explanations: list[Explanation] = Field(max_length=200)
    limitations: list[str] = Field(max_length=20)


class ReportRecord(Model):
    schema_version: Literal[2, 3, 4] = 4
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    series: str = Field(default="My reports", min_length=1, max_length=60)
    mode: Literal["synthetic", "live"]
    facts_reviewed: bool = False
    extracted: ExtractedReport
    checked: list[CheckedIndicator]
    analysis: GeneratedAnalysis | None = None
    analysis_issue: str | None = None
    corrections: list[Correction] = Field(default_factory=list)
    analysis_rejections: list[str] = Field(default_factory=list)
    data_conflicts: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy(cls, data):
        # Reclassify old records in memory, never overwrite their files automatically.
        if isinstance(data, dict) and data.get("schema_version") in (2, 3):
            from copy import deepcopy
            data = deepcopy(data)
            if isinstance(data.get("extracted"), ExtractedReport):
                data["extracted"] = data["extracted"].model_dump()
            if not isinstance(data.get("extracted"), dict) or not isinstance(data.get("id"), str):
                raise ValueError("Legacy record lacks its original identity or extraction.")
            data["schema_version"] = 4
            data["extracted"].setdefault("extraction_id", "legacy:" + data.get("id", "unknown"))
            data["analysis"] = None
            data["analysis_issue"] = "Legacy record: readiness rechecked; old explanations withheld. Reanalyze to generate gated explanations."
            if not isinstance(data.get("checked"), list):
                raise ValueError("Legacy checked rows are invalid.")
            for index, row in enumerate(data["checked"]):
                if isinstance(row, CheckedIndicator):
                    row = data["checked"][index] = row.model_dump()
                if not isinstance(row, dict) or not isinstance(row.get("row_id"), str):
                    raise ValueError("Legacy row identity is missing.")
                row.pop("decision", None)
                row.setdefault("observation_id", str(uuid5(NAMESPACE_URL, f"{data['extracted']['extraction_id']}/{row['row_id']}")))
        return data

    @model_validator(mode="after")
    def consistent_rows(self):
        if len(self.checked) != len(self.extracted.indicators):
            raise ValueError("Facts and checked rows must correspond.")
        ids = [x.row_id for x in self.checked]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate row IDs.")
        if any(s.raw != raw for s, raw in zip(self.extracted.sources, self.extracted.indicators)):
            raise ValueError("Source snapshot differs from retained extraction.")
        from interpreter.review import effective_report, correction_conflicts
        effective = effective_report(self.extracted, self.corrections)
        if any(c.original != raw for c, raw in zip(self.checked, effective.indicators)):
            raise ValueError("Original facts changed.")
        # Revalidate persisted derived data too: schema-valid JSON alone is insufficient.
        from hashlib import sha256
        from interpreter.validation import check_report, validate_analysis
        from interpreter.knowledge import SOURCE_MAP
        expected = check_report(effective)
        for actual, computed in zip(self.checked, expected):
            for field in ("row_id", "observation_id", "canonical_id", "display_name", "numeric_value", "status"):
                if getattr(actual, field) != getattr(computed, field):
                    raise ValueError("Derived data does not agree with original facts.")
            if not all(issue in actual.issues for issue in computed.issues):
                raise ValueError("Required review warnings are missing.")
            if actual.evidence:
                evidence = actual.evidence
                source = SOURCE_MAP.get(actual.canonical_id, actual.canonical_id)
                if (not source or evidence.indicator_id != actual.canonical_id
                        or evidence.source_id not in (f"knowledge_base/{source}.txt", f"knowledge_base/curated/{actual.canonical_id}.json")
                        or sha256(evidence.text.encode()).hexdigest() != evidence.sha256):
                    raise ValueError("Evidence identity or integrity check failed.")
        from interpreter.abstention import assign_decisions
        computed_rows = [r.model_copy(deep=True) for r in self.checked]
        if not set(self.analysis_rejections + self.data_conflicts).issubset(ids):
            raise ValueError("Unknown analysis rejection row.")
        assign_decisions(computed_rows, self.corrections, self.analysis_rejections,
                         correction_conflicts(self.extracted, self.corrections), self.data_conflicts,
                         synthetic=self.mode == "synthetic")
        for actual, computed in zip(self.checked, computed_rows):
            if actual.decision is not None and actual.decision != computed.decision:
                raise ValueError("Readiness must agree with deterministic checks.")
            actual.decision = computed.decision
        if self.analysis:
            validate_analysis(self.analysis, self.checked)
        return self
