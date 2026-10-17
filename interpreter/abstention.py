"""Deterministic educational interpretation gate, not a medical confidence score."""
import re
from collections import Counter
from hashlib import sha256

from interpreter.catalog import ALIASES, key
from interpreter.models import DecisionReason, InterpretationDecision
from interpreter.units import specification, unit_key

STATES = ("interpretable", "needs_review", "insufficient_evidence", "unsupported")
# Dimensions, not medical thresholds. Unknown units never become assumptions.
DIMENSIONS = {
    **{c: {"count"} for c in ("WBC", "RBC", "PLT")},
    **{c: {"count", "fraction"} for c in ("NEUT", "LYMPH", "MONO", "EOS")},
    **{c: {"mass"} for c in ("HGB", "MCHC", "ALB", "TP")},
    **{c: {"activity"} for c in ("ALT", "AST", "GGT", "ALP")},
    **{c: {"mass", "molar"} for c in ("GLU", "BUN", "CREA", "UA", "TBIL", "DBIL", "IBIL")},
    "HCT": {"fraction"}, "HbA1c": {"fraction"}, "MCV": {"volume"}, "MCH": {"cell_mass"}, "eGFR": {"egfr"},
}


def usable_evidence(evidence, code):
    from interpreter.knowledge import SOURCE_MAP
    expected = SOURCE_MAP.get(code, code)
    header = evidence.text.splitlines()[0] if evidence.text.strip() else ""
    return bool(expected and evidence.indicator_id == code
        and evidence.source_id == f"knowledge_base/{expected}.txt"
        and sha256(evidence.text.encode()).hexdigest() == evidence.sha256
        and re.search(rf"\b{re.escape(expected)}\b", header, re.I)
        and len(evidence.text.strip()) >= 80)


def assign_decisions(rows, corrections=(), analysis_rejections=(), review_conflicts=(), data_conflicts=(), *, synthetic=False):
    counts = Counter(r.canonical_id for r in rows if r.canonical_id)
    pending = {c.row_id for c in corrections if not c.confirmed_from_report}
    for row in rows:
        raw, findings = row.original, []
        def add(state, code, message, action):
            findings.append((state, DecisionReason(code=code, message=message, action=action)))
        if row.row_id in review_conflicts:
            add("needs_review", "correction_conflict", "The correction has a stale baseline or multiple conflicting replacements.", "Reconcile changes against the original extraction. Conflicting replacements were not applied.")
        if row.row_id in data_conflicts:
            add("needs_review", "derived_data_conflict", "Derived values, units, identity or status disagree with the retained report facts.", "Recheck the processing inputs. Derived data was recomputed and this row was withheld from explanation.")
        if row.row_id in pending:
            add("needs_review", "correction_unconfirmed", "The correction has not been checked against the source report.", "Check the changed fields against the original and explicitly confirm the correction.")
        if raw.uncertain:
            add("needs_review", "uncertain_extraction", "The extracted text is marked ambiguous; OCR accuracy is unresolved.", "Inspect the source, correct any misread characters and clear uncertainty only when resolved.")
        if row.numeric_value is None:
            if raw.raw_value is None or not raw.raw_value.strip():
                add("insufficient_evidence", "missing_value", "No measurable value was supplied.", "Enter the value exactly as printed, or leave this row uninterpreted.")
            else:
                add("needs_review", "unparsed_value", "The value is qualified, qualitative or cannot be parsed unambiguously.", "Check the original. Do not remove < or > to manufacture an exact value; qualitative interpretation is not supported.")
        if not row.canonical_id:
            candidates = {ALIASES.get(key(p)) for p in re.split(r"[()/（）]", raw.name)} - {None}
            if len(candidates) > 1:
                add("needs_review", "ambiguous_name", "The name contains conflicting standard indicator matches.", "Confirm the actual analyte name from the report; do not choose a match by guessing.")
            else:
                add("unsupported", "unmapped_indicator", "The system cannot map this indicator reliably.", "Check its full name and abbreviation. Unsupported analytes can still be displayed as facts.")
        if row.canonical_id and counts[row.canonical_id] > 1:
            add("needs_review", "duplicate_indicator", "Repeated indicator rows may describe conflicting values, specimens or methods.", "Verify specimen, date and method for each occurrence; this version does not reconcile repeated analytes.")
        unit, refunit = specification(raw.unit), specification(raw.reference.unit)
        if not raw.unit or not raw.unit.strip():
            add("insufficient_evidence", "missing_unit", "The measurement unit is missing.", "Copy the unit from the original report; do not infer it from typical values.")
        elif not unit:
            add("unsupported", "unsupported_unit", "This measurement unit is not supported by the conversion allowlist.", "Verify the printed unit. Do not substitute a familiar unit without a verified conversion.")
        elif row.canonical_id in DIMENSIONS and unit[0] not in DIMENSIONS[row.canonical_id]:
            add("needs_review", "incompatible_unit", "The unit dimension does not match the recognized indicator.", "Verify both the indicator name and unit against the original report.")
        if not raw.reference.text or not raw.reference.text.strip():
            add("insufficient_evidence", "missing_reference", "There is no printed reference interval for a range-based explanation.", "Obtain the applicable laboratory interval; do not copy a generic interval from the knowledge note.")
        else:
            if not raw.reference.unit:
                add("insufficient_evidence", "missing_reference_unit", "Reference interval units are not confirmed.", "Confirm the interval's printed unit, including whether it shares the measurement unit.")
            elif not refunit:
                add("unsupported", "unsupported_reference_unit", "The reference unit is unsupported.", "Confirm the original interval and unit with the laboratory.")
            elif unit and unit_key(raw.unit) != unit_key(raw.reference.unit):
                add("needs_review", "reference_unit_mismatch", "Value and reference units differ; a range judgment has not been made.", "Check and explicitly reconcile the units and interval together; no automatic range conversion is assumed.")
            if (row.status == "unknown" and row.numeric_value is not None and not raw.uncertain
                    and unit and refunit and unit_key(raw.unit) == unit_key(raw.reference.unit)):
                add("needs_review", "unusable_reference", "The reference interval or its units are ambiguous, conflicting or unsupported.", "Check lower/upper limits, qualifiers and units. Select only a laboratory interval applicable to this report.")
        context_hint = re.search(r"age|sex|male|female|child|adult|method|assay|年龄|性别|儿童|成人|方法", raw.reference.text or "", re.I)
        if (raw.reference.context_required or context_hint) and not raw.reference.context_confirmed:
            add("needs_review", "reference_context", "Age, sex, method or laboratory applicability has not been confirmed.", "Confirm which printed interval applies; this app does not infer demographic or assay-specific intervals.")
        if row.status == "conflict":
            add("needs_review", "flag_conflict", "Printed flag and calculated range status disagree.", "Check the value, reference interval and printed flag together.")
        if row.evidence is None:
            if row.knowledge_rejected:
                add("insufficient_evidence", "unusable_knowledge", "Retrieved content failed the local identity/content relevance checks.", "Review the local note. Display facts only; do not substitute unrelated text.")
            else:
                add("unsupported", "no_knowledge", "No relevant knowledge note covers this row.", "Display the report facts only; seek appropriate laboratory or professional interpretation.")
        else:
            if not synthetic and not supported_knowledge(row.evidence):
                add("insufficient_evidence", "unverified_knowledge", "The retrieved note has no usable reviewed source; retrieval is not medical verification.", "Display report facts only. A scoped, source-checked knowledge entry is required before live explanation.")
            if not usable_evidence(row.evidence, row.canonical_id):
                add("insufficient_evidence", "unusable_knowledge", "The retrieved note does not pass the local identity/content relevance checks.", "Withhold the explanation and review the local knowledge entry; do not use unrelated text.")
        if row.row_id in analysis_rejections:
            add("needs_review", "analysis_conflict", "The generated response was missing, duplicated or inconsistent with the allowed row/source contract.", "Keep facts only for this row and retry after checking the inputs.")
        if findings:
            # All reasons survive; a single primary state gives a count, not a risk rank.
            priority = ("needs_review", "unsupported", "insufficient_evidence")
            state = next(s for s in priority if any(f[0] == s for f in findings))
            row.decision = InterpretationDecision(state=state, reasons=[f[1] for f in findings])
        else:
            row.decision = InterpretationDecision(state="interpretable", reasons=[DecisionReason(
                code="conditions_met", message="Current checks permit a bounded educational explanation from the printed facts and local note.",
                action="Compare with the original report. Reference applicability and medical meaning still require professional judgment.")])
    return rows


def supported_knowledge(evidence):
    if not evidence or not evidence.metadata:
        return False
    meta = evidence.metadata
    # Metadata is trusted local curation, never model output. A hash identifies the
    # reviewed revision; it does not establish the truth of its medical claims.
    return (meta.review_status == "reviewed" and bool(meta.sources and meta.reviewer and meta.reviewed_on)
            and meta.version == "sha256:" + evidence.sha256
            and meta.entry_id == "kb:" + evidence.source_id.rsplit("/", 1)[-1].removesuffix(".txt"))


def summary_counts(rows):
    counts = {state: 0 for state in STATES}
    for row in rows:
        counts[row.decision.state if row.decision else "needs_review"] += 1
    counts["interpretable_outside_range"] = sum(r.decision is not None and r.decision.state == "interpretable"
                                               and r.status in ("high", "low") for r in rows)
    return counts
