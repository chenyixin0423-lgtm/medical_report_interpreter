from interpreter.models import ReportRecord
from interpreter.validation import check_report, validate_analysis


def prepare(report, knowledge):
    rows = check_report(report)
    for row in rows:
        row.evidence = knowledge.retrieve(row.canonical_id)
        if row.evidence is None:
            row.issues.append("Knowledge base coverage is insufficient for this indicator.")
    return rows


def finish(report, rows, gateway, series="My reports", question=""):
    from interpreter.llm import ModelError
    analysis, issue = None, None
    try:
        analysis = gateway.analyze(rows, question)
        validate_analysis(analysis, rows)
    except (ValueError, ModelError):
        analysis = None
        issue = "Generated explanations were unavailable or failed validation. Extracted facts and rule checks remain available."
    return ReportRecord(mode="live", series=series, facts_reviewed=True, extracted=report,
                        checked=rows, analysis=analysis, analysis_issue=issue)
