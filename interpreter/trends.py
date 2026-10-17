"""Comparable numeric observations only; never interpret direction as health change."""
from collections import Counter
from math import isfinite

from interpreter.units import specification


def trend_groups(records, code: str, series: str, mode: str):
    groups, excluded = {}, []
    for report in records:
        if report.series != series or report.mode != mode:
            continue
        counts = Counter(r.canonical_id for r in report.checked)
        for row in report.checked:
            if row.canonical_id != code:
                continue
            reason = None
            spec = specification(row.original.unit)
            if not report.facts_reviewed:
                reason = "Facts not reviewed"
            elif not report.extracted.report_date:
                reason = "Report date missing"
            elif counts[code] > 1:
                reason = "Repeated indicator"
            elif row.original.uncertain or row.status == "conflict":
                reason = "Uncertain or conflicting facts"
            elif row.decision and any(x.code in {"correction_unconfirmed", "correction_conflict", "incompatible_unit", "derived_data_conflict"}
                                      for x in row.decision.reasons):
                reason = "Unconfirmed correction or incompatible unit"
            elif row.numeric_value is None:
                reason = "Non-numeric value"
            elif not spec:
                reason = "Unsupported or missing unit"
            elif not isfinite(row.numeric_value * spec[2]):
                reason = "Converted number is outside supported limits"
            if reason:
                excluded.append({"Report": report.id[:8], "Reason": reason})
                continue
            dimension, unit, factor = spec
            groups.setdefault(unit, []).append({"Date": report.extracted.report_date,
                "Value": row.numeric_value * factor, "Unit": unit,
                "Original value": row.original.raw_value, "Original unit": row.original.unit,
                "Report": report.id, "Observation ID": row.observation_id,
                "Extraction value": report.extracted.sources[int(row.row_id.split("-")[1])-1].raw.raw_value,
                "Conversion factor": factor})
    for points in groups.values():
        points.sort(key=lambda p: (p["Date"], p["Report"]))
    return groups, excluded
