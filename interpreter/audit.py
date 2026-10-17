"""Conservative closed-form audit, not clinical or general semantic verification.

Only exact fact grammar and complete selected context can be Supported. Everything
else fails closed to review, even when keyword heuristics miss unsafe language.
"""
import re
from uuid import uuid5, NAMESPACE_URL

from interpreter.models import AuditedClaim
from interpreter.validation import NUMBER, numeric
from interpreter.catalog import normalize
from interpreter.units import unit_key, specification
from interpreter.abstention import supported_knowledge
from interpreter.curated import context_problem

FACT = re.compile(rf"Report fact: (.+?) = ({NUMBER}) (.+?); range status = (\w+)\.")
UNSAFE = re.compile(
    r"\b(you have|patient has|diagnos\w*|confirms?|proves?|definitely|certainly|"
    r"caused by|due to|rules out|no disease|healthy|risk of|worsen\w*|improv\w*|"
    r"take|start|stop|prescrib\w*|recommend\w*|treat\w*|medication|dose|"
    r"antibiotic\w*|supplement\w*|within \d+ (?:hours|days))\b", re.I)


def fact_text(row):
    return (f"Report fact: {row.canonical_id} = {row.original.raw_value} {row.original.unit}; "
            f"range status = {row.status}.")


def claim_texts(explanation):
    # New output is atomic blocks. Legacy prose is split conservatively, never
    # at decimal points. Both fields are audited if a model supplies both.
    blocks = list(explanation.claims)
    if explanation.text.strip():
        blocks.append(explanation.text)
    texts = []
    for block in blocks:
        # A full context is one bounded evidence unit: splitting away its caveats
        # would falsely certify individual diagnostic possibilities.
        if block.startswith("General context: "):
            texts.append(block)
        else:
            texts.extend(re.split(r"(?<=[.!?])\s+(?=[A-Z])|\n+", block))
    return [text.strip() for text in texts if text.strip()]


def audit_claim(row, text, index, reviewed):
    result = AuditedClaim(claim_id=str(uuid5(NAMESPACE_URL,
        f"{row.observation_id}/claim-audit-v1/{index}/{text}")), row_id=row.row_id,
        observation_id=row.observation_id, text=text, outcome="Needs Review",
        reason="Free-form meaning is not deterministically verified. Check the report and selected source; do not treat this as a confirmed conclusion.")

    def verdict(outcome, reason):
        result.outcome, result.reason = outcome, reason
        return result

    if not reviewed or not row.decision or row.decision.state != "interpretable":
        return verdict("Needs Review", "Report facts are not ready for interpretation. Resolve the row's review reasons first.")
    # Search also detects a contradictory fact followed by an extra inference.
    match = FACT.search(text)
    if match:
        name, value, unit, status = match.groups()
        if normalize(name) != row.canonical_id:
            return verdict("Unsupported", "Claim introduces a different or unrecognized indicator; it is not this observation.")
        result.evidence_text = fact_text(row)
        if numeric(value) != row.numeric_value or unit_key(unit) != unit_key(row.original.unit) or status != row.status:
            return verdict("Contradicted", "Claim value, unit or range status disagrees with the current checked report. No implicit unit conversion is accepted.")
        if FACT.fullmatch(text):
            result.basis = "report_fact"
            return verdict("Supported", "Matches the reviewed effective report fields and calculated range status only; original extraction accuracy and medical correctness are not established.")

    if text.startswith("General context: "):
        evidence = row.evidence
        if (not evidence or not supported_knowledge(evidence)
                or evidence.provenance != "source_checked_summary" or context_problem(row)):
            return verdict("Unsupported", "No applicable source-checked selected context supports this claim.")
        result.knowledge_id = evidence.metadata.entry_id
        result.knowledge_version = evidence.metadata.version
        result.evidence_text = evidence.selected_text
        if text == "General context: " + evidence.selected_text:
            result.basis = "general_context"
            return verdict("Supported", "Exact complete selected educational context, including caveats; not a patient-specific cause, diagnosis or independently verified medical truth.")
        return verdict("Unsupported", "Claim is not the complete retrieved context. Changed wording, omitted caveats or an unselected branch cannot be certified by a related citation.")

    # Limited natural-language fact checks help diagnose common mistakes. They
    # never promote free prose to Supported; ambiguous language remains review.
    assertion = re.search(rf"\b([A-Za-z][A-Za-z0-9-]*)\s*(?:is|=|:)\s*({NUMBER})(?:\s+([^\s,;.]+))?", text)
    if assertion:
        name, value, unit = assertion.groups()
        code = normalize(name)
        if code != row.canonical_id:
            return verdict("Unsupported", "An asserted indicator is absent from this linked observation or cannot be identified.")
        if numeric(value) != row.numeric_value:
            result.evidence_text = fact_text(row)
            return verdict("Contradicted", "Asserted value differs from the checked report value. Verify the original report.")
        if unit and specification(unit) and unit_key(unit) != unit_key(row.original.unit):
            result.evidence_text = fact_text(row)
            return verdict("Contradicted", "Asserted unit differs from the checked report unit. No implicit conversion is accepted.")
    status_assertion = re.fullmatch(r"([A-Za-z0-9-]+) is (high|low|normal|within_range|elevated)\.?", text)
    if status_assertion:
        name, status = status_assertion.groups()
        if normalize(name) != row.canonical_id:
            return verdict("Unsupported", "The status assertion names a different or unknown indicator.")
        if {"normal": "within_range", "elevated": "high"}.get(status, status) != row.status:
            result.evidence_text = fact_text(row)
            return verdict("Contradicted", "Asserted abnormality status conflicts with the checked report range.")
    if UNSAFE.search(text):
        return verdict("Unsupported", "Potential diagnosis, causal overreach, risk inference or treatment advice is outside the supported educational contract. No patient-specific conclusion is established.")
    return result


def audit_record(record):
    if not record.analysis:
        return []
    rows = {row.row_id: row for row in record.checked}
    return [audit_claim(rows[explanation.row_id], text, index, record.facts_reviewed)
            for explanation in record.analysis.explanations
            for index, text in enumerate(claim_texts(explanation))]
