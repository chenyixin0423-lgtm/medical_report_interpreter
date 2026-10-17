"""Single revision against immutable extraction; no silent overwrites or model consensus."""
from interpreter.models import Correction, ExtractedReport


def correction_conflicts(extracted, corrections):
    ids = [f"row-{i + 1}" for i in range(len(extracted.indicators))]
    from collections import Counter
    counts = Counter(c.row_id for c in corrections)
    conflicts = set()
    for c in corrections:
        if c.row_id not in ids:
            raise ValueError("Correction references an unknown row.")
        if counts[c.row_id] > 1 or c.before != extracted.indicators[ids.index(c.row_id)]:
            conflicts.add(c.row_id)
    return conflicts


def effective_report(extracted: ExtractedReport, corrections: list[Correction]) -> ExtractedReport:
    result = extracted.model_copy(deep=True)
    conflicts = correction_conflicts(extracted, corrections)
    for change in corrections:
        if change.row_id in conflicts:
            continue
        ids = [f"row-{i + 1}" for i in range(len(extracted.indicators))]
        if change.row_id not in ids:
            raise ValueError("Correction references an unknown row.")
        index = ids.index(change.row_id)
        result.indicators[index] = change.after.model_copy(deep=True)
    return result
