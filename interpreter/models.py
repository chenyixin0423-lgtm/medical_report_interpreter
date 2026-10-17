"""Strict contracts. Extracted strings are never replaced by generated explanations."""
from datetime import date, datetime, timezone
from typing import Literal
from uuid import uuid4

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


class ExtractedReport(Model):
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


class Evidence(Model):
    source_id: str
    indicator_id: str
    text: str
    provenance: Literal["unverified_project_note"] = "unverified_project_note"
    sha256: str


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
    schema_version: Literal[2, 3] = 3
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
    def upgrade_v2(cls, data):
        # Reclassify old records in memory, never overwrite their files automatically.
        if isinstance(data, dict) and data.get("schema_version") == 2:
            from copy import deepcopy
            data = deepcopy(data)
            data["schema_version"] = 3
            data["analysis"] = None
            data["analysis_issue"] = "Legacy record: readiness rechecked; old explanations withheld. Reanalyze to generate gated explanations."
            for row in data.get("checked", []):
                row.pop("decision", None)
        return data

    @model_validator(mode="after")
    def consistent_rows(self):
        if len(self.checked) != len(self.extracted.indicators):
            raise ValueError("Facts and checked rows must correspond.")
        ids = [x.row_id for x in self.checked]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate row IDs.")
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
            for field in ("row_id", "canonical_id", "display_name", "numeric_value", "status"):
                if getattr(actual, field) != getattr(computed, field):
                    raise ValueError("Derived data does not agree with original facts.")
            if not all(issue in actual.issues for issue in computed.issues):
                raise ValueError("Required review warnings are missing.")
            if actual.evidence:
                evidence = actual.evidence
                source = SOURCE_MAP.get(actual.canonical_id, actual.canonical_id)
                if (not source or evidence.indicator_id != actual.canonical_id
                        or evidence.source_id != f"knowledge_base/{source}.txt"
                        or sha256(evidence.text.encode()).hexdigest() != evidence.sha256):
                    raise ValueError("Evidence identity or integrity check failed.")
        from interpreter.abstention import assign_decisions
        computed_rows = [r.model_copy(deep=True) for r in self.checked]
        if not set(self.analysis_rejections + self.data_conflicts).issubset(ids):
            raise ValueError("Unknown analysis rejection row.")
        assign_decisions(computed_rows, self.corrections, self.analysis_rejections,
                         correction_conflicts(self.extracted, self.corrections), self.data_conflicts)
        for actual, computed in zip(self.checked, computed_rows):
            if actual.decision is not None and actual.decision != computed.decision:
                raise ValueError("Readiness must agree with deterministic checks.")
            actual.decision = computed.decision
        if self.analysis:
            validate_analysis(self.analysis, self.checked)
        return self
