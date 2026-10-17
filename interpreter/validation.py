"""Deterministic checks; no diagnostic thresholds and no model-assigned status."""
import re
from collections import Counter
from math import isfinite

from interpreter.catalog import CATALOG, normalize
from interpreter.models import CheckedIndicator, ExtractedReport, GeneratedAnalysis
from interpreter.units import unit_key

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"


def numeric(text: str | None) -> float | None:
    if text is None or not re.fullmatch(NUMBER, text.strip()):
        return None
    value = float(text)
    return value if isfinite(value) else None


def range_status(value: float, text: str | None) -> str:
    text = (text or "").strip().replace("–", "-").replace("—", "-").replace("~", "-").replace("～", "-")
    m = re.fullmatch(rf"({NUMBER})\s*-\s*({NUMBER})", text)
    if m:
        low, high = map(float, m.groups())
        if not (isfinite(low) and isfinite(high)) or low > high:
            return "unknown"
        return "low" if value < low else "high" if value > high else "within_range"
    m = re.fullmatch(rf"(<=|>=|<|>|≤|≥)\s*({NUMBER})", text)
    if m:
        op, limit = m[1], float(m[2])
        if not isfinite(limit):
            return "unknown"
        matches = {"<": value < limit, "<=": value <= limit, "≤": value <= limit,
                   ">": value > limit, ">=": value >= limit, "≥": value >= limit}
        return "within_range" if matches[op] else "high" if op in ("<", "<=", "≤") else "low"
    return "unknown"


def check_report(report: ExtractedReport) -> list[CheckedIndicator]:
    codes = [normalize(i.name) for i in report.indicators]
    counts = Counter(c for c in codes if c)
    rows = []
    for index, (raw, code) in enumerate(zip(report.indicators, codes)):
        row = CheckedIndicator(row_id=f"row-{index + 1}", canonical_id=code,
                               observation_id=report.sources[index].observation_id,
                               display_name=CATALOG[code][0] if code else raw.name,
                               original=raw, numeric_value=numeric(raw.raw_value))
        if not code:
            row.issues.append("Indicator name is not recognized; check the original report.")
        if raw.uncertain:
            row.issues.append("Extraction is uncertain; check the original report.")
        elif row.numeric_value is None:
            row.issues.append("Missing, qualified, or non-numeric value; no automatic classification.")
        elif not raw.unit or not raw.reference.unit or unit_key(raw.unit) != unit_key(raw.reference.unit):
            row.issues.append("Missing or mismatched reference units; check the original report.")
        else:
            row.status = range_status(row.numeric_value, raw.reference.text)
            if row.status == "unknown":
                row.issues.append("Missing or ambiguous reference range; no automatic classification.")
        if raw.report_flag != "unknown" and row.status != "unknown":
            expected = "within_range" if raw.report_flag == "normal" else raw.report_flag
            if expected != row.status:
                row.status = "conflict"
                row.issues.append("Printed report flag conflicts with the range calculation; manual review required.")
        if code and counts[code] > 1:
            row.issues.append("Repeated indicator; excluded from trends to avoid matching different specimens or methods.")
        rows.append(row)
    return rows


def validate_analysis(analysis: GeneratedAnalysis, rows: list[CheckedIndicator]) -> None:
    expected = {r.row_id: r for r in rows if r.decision is not None and r.decision.state == "interpretable"}
    ids = [x.row_id for x in analysis.explanations]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Analysis must cover only interpretable rows, exactly once.")
    for explanation in analysis.explanations:
        evidence = expected[explanation.row_id].evidence
        allowed = [evidence.source_id] if evidence else []
        if explanation.source_ids != allowed:
            raise ValueError("Analysis contains missing or unsupported source references.")
