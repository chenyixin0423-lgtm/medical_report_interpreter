from collections import Counter

from interpreter.models import GeneratedAnalysis, ReportRecord
from interpreter.validation import check_report, validate_analysis
from interpreter.abstention import assign_decisions, usable_evidence
from interpreter.review import effective_report, correction_conflicts


def prepare(report, knowledge, corrections=(), *, synthetic=False):
    rows = check_report(effective_report(report, corrections))
    for row in rows:
        try:
            row.evidence = (knowledge.retrieve_for(row) if callable(getattr(type(knowledge), "retrieve_for", None))
                            else knowledge.retrieve(row.canonical_id))
        except ValueError:
            row.knowledge_rejected = True
        if row.evidence is not None and not usable_evidence(row.evidence, row.canonical_id):
            row.evidence = None
            row.knowledge_rejected = True
        if row.evidence is None:
            row.issues.append("Knowledge base coverage is insufficient for this indicator.")
    return assign_decisions(rows, corrections, review_conflicts=correction_conflicts(report, corrections), synthetic=synthetic)


def finish(report, rows, gateway, series="My reports", question="", corrections=()):
    from interpreter.llm import ModelError
    expected = check_report(effective_report(report, corrections))
    if len(rows) != len(expected):
        raise ValueError("Row count changed; prepare the report again.")
    input_conflicts = []
    checked = []
    for supplied, computed in zip(rows, expected):
        row = supplied.model_copy(deep=True)
        if any(getattr(row, f) != getattr(computed, f) for f in
               ("row_id", "observation_id", "canonical_id", "original", "numeric_value", "status")):
            input_conflicts.append(computed.row_id)
            row = computed
            row.evidence = supplied.evidence
        if row.evidence is not None and not usable_evidence(row.evidence, row.canonical_id):
            row.evidence = None
            row.knowledge_rejected = True
        checked.append(row)
    rows = assign_decisions(checked, corrections, review_conflicts=correction_conflicts(report, corrections), data_conflicts=input_conflicts)
    # Validate caller-supplied derived facts before any external request.
    candidate = ReportRecord(mode="live", series=series, facts_reviewed=True, extracted=report,
                             checked=rows, corrections=list(corrections), data_conflicts=input_conflicts)
    rows = candidate.checked
    eligible = [r for r in rows if r.decision.state == "interpretable"]
    analysis, issue, rejected = None, None, []
    if not eligible:
        candidate.analysis_issue = "No indicators meet the current explanation requirements. No model request was made."
        return candidate
    try:
        # Free-text questions can reintroduce refused facts; this iteration restricts
        # analysis to row explanations and does not forward arbitrary questions.
        response = gateway.analyze(eligible, "")
        counts = Counter(x.row_id for x in response.explanations)
        accepted = []
        for row in eligible:
            items = [x for x in response.explanations if x.row_id == row.row_id]
            try:
                if counts[row.row_id] != 1:
                    raise ValueError("Missing or duplicate explanation")
                validate_analysis(GeneratedAnalysis(explanations=items, limitations=[]), [row])
                accepted.extend(items)
            except ValueError:
                rejected.append(row.row_id)
        assign_decisions(rows, corrections, rejected, correction_conflicts(report, corrections), input_conflicts)
        # No model-written report summary/limitations: those could contain refused facts.
        analysis = GeneratedAnalysis(explanations=accepted, limitations=[
            "Only eligible rows were sent for educational explanations. Refused rows are not diagnostic evidence.",
            "Source checking is not clinical expert review. Interpretation readiness does not establish medical correctness."])
        if rejected:
            issue = "Some generated explanations failed row/source validation and were withheld. Other eligible rows remain available."
        if not accepted:
            analysis = None
    except (ValueError, ModelError):
        analysis = None
        issue = "Generated explanations were unavailable or failed validation. Extracted facts and rule checks remain available."
    return ReportRecord(mode="live", series=series, facts_reviewed=True, extracted=report,
                        checked=rows, analysis=analysis, analysis_issue=issue,
                        corrections=list(corrections), analysis_rejections=rejected, data_conflicts=input_conflicts)
