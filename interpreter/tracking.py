"""Occurrence-linked source snapshots. Text matching is not clinical verification."""
from io import BytesIO
import re

from interpreter.models import ExtractedReport


def track_extraction(payload, upload):
    report = ExtractedReport(**payload.model_dump())
    for source in report.sources:
        source.origin = "model_extraction"
    if upload.media_type != "application/pdf":
        return report  # No independent OCR: image positions remain Unknown.
    try:
        from pypdf import PdfReader
        pages = []
        for page in PdfReader(BytesIO(upload.data), strict=True).pages[:20]:
            # Guard decompression before text extraction; raw document never persisted.
            contents = page.get_contents()
            if contents and len(contents.get_data()) > 2_000_000:
                return report
            text = page.extract_text() or ""
            if len(text) > 100_000:
                return report
            pages.append(text)
        attach_text_matches(report, pages)
    except Exception:
        # Parser errors must not leak uploaded data into application logs.
        pass
    return report


def attach_text_matches(report, pages):
    """Conservative exact single-line matches only; no inferred page or bounding box.

    Every extracted field must occur in order and the entire line must contain only
    these fields (plus whitespace). This avoids retaining adjacent identifying text.
    Repeated lines/occurrences and multiline tables intentionally remain unknown.
    """
    from collections import Counter
    signatures = Counter((r.name, r.raw_value, r.unit, r.reference.text) for r in report.indicators)
    for source in report.sources:
        raw = source.raw
        fields = (raw.name, raw.raw_value, raw.unit, raw.reference.text)
        if not all(fields) or signatures[fields] != 1 or raw.report_flag != "unknown":
            continue
        pattern = r"\s*" + r"\s+".join(re.escape(x) for x in fields) + r"\s*"
        matches = [(p, n, line) for p, text in enumerate(pages, 1)
                   for n, line in enumerate(text.splitlines(), 1)
                   if len(line) <= 500 and re.fullmatch(pattern, line)]
        if len(matches) == 1:
            page, line, excerpt = matches[0]
            source.verification = "text_match"
            source.page = page
            source.location = f"Extracted text line {line}; not a visual bounding box"
            source.excerpt = excerpt
