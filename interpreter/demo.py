"""Fabricated observations and preset explanations; never real-time AI output."""
from interpreter.models import ExtractedReport, GeneratedAnalysis, ReportRecord
from interpreter.pipeline import prepare
from interpreter.validation import validate_analysis


def demo_reports(knowledge):
    reports = []
    for index, (day, wbc, hgb, glu) in enumerate([
        ("2026-01-15", "7.2", "13.4", "5.2"),
        ("2026-03-15", "11.2", "128", "6.3"),
        ("2026-05-15", "9.1", "13.1", "5.7"),
    ]):
        def item(name, value, unit, bounds):
            return {"name": name, "raw_value": value, "unit": unit,
                    "reference": {"text": bounds, "unit": unit}}
        facts = ExtractedReport.model_validate({"report_date": day, "indicators": [
            item("白细胞(WBC)", wbc, "10^9/L", "4.0-10.0"),
            item("Hemoglobin", hgb, "g/L" if index == 1 else "g/dL", "130-170" if index == 1 else "13.0-17.0"),
            item("Glucose", glu, "mmol/L", "3.9-5.5"),
            item("ALT", "28", "U/L", "0-40"),
            item("TSH", "2.1", "mIU/L", None),
            item("Urine protein", "Negative", None, "Negative"),
        ], "warnings": ["SYNTHETIC: all values and reference ranges are invented for software demonstration."]})
        rows = prepare(facts, knowledge)
        analysis = GeneratedAnalysis.model_validate({"explanations": [
            {"row_id": row.row_id,
             "text": ("Preset example: the displayed status is calculated only from the synthetic report's printed range. "
                      "It is not a diagnosis. The linked project note is unverified educational context."
                      if row.evidence else "Preset example: knowledge base coverage is insufficient. Check the original report with a qualified professional."),
             "source_ids": [row.evidence.source_id] if row.evidence else []} for row in rows],
            "limitations": ["Preset explanations, not a real-time model response.",
                            "Synthetic ranges do not establish reference intervals for any population."]})
        validate_analysis(analysis, rows)
        reports.append(ReportRecord(id=f"synthetic-{index + 1}", created_at=f"{day}T12:00:00+00:00",
            mode="synthetic", series="Synthetic series A", facts_reviewed=True,
            extracted=facts, checked=rows, analysis=analysis))
    return list(reversed(reports))
