from io import BytesIO

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from interpreter.knowledge import KnowledgeBase
from interpreter.security import UploadError, validate_upload


def test_chroma_exact_retrieval_and_refresh(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "WBC.txt").write_text("White blood cells", encoding="utf-8")
    store = KnowledgeBase(tmp_path / "chroma", kb)
    assert store.retrieve("WBC").text == "White blood cells"
    assert store.retrieve("WBC").provenance == "unverified_project_note"
    assert store.retrieve("not-known") is None
    assert store.retrieve(None) is None
    old_hash = store.retrieve("WBC").sha256
    (kb / "WBC.txt").write_text("Updated note", encoding="utf-8")
    refreshed = KnowledgeBase(tmp_path / "chroma", kb)
    assert refreshed.retrieve("WBC").sha256 != old_hash
    (kb / "WBC.txt").unlink()
    assert KnowledgeBase(tmp_path / "chroma", kb).collection.count() == 0


def test_images():
    buf = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    data = buf.getvalue() + b"<script>payload</script>"
    result = validate_upload(data, "../../patient.png")
    assert b"payload" not in result.data
    assert result.media_type == "image/png"
    for contents, name in [(data, "fake.jpg"), (b"bad", "fake.png"), (data, "file.exe"),
                           (b"x" * (10 * 1024 * 1024 + 1), "large.png"), (b"", "empty.png")]:
        with pytest.raises(UploadError):
            validate_upload(contents, name)


def pdf_bytes(writer):
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_pdf_validation():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    assert validate_upload(pdf_bytes(writer), "report.pdf").media_type == "application/pdf"
    writer.add_open_action(DictionaryObject({NameObject("/S"): NameObject("/JavaScript"),
                                             NameObject("/JS"): TextStringObject("app.alert('bad')")}))
    with pytest.raises(UploadError):
        validate_upload(pdf_bytes(writer), "report.pdf")
    encrypted = PdfWriter()
    encrypted.add_blank_page(width=100, height=100)
    encrypted.encrypt("password")
    with pytest.raises(UploadError):
        validate_upload(pdf_bytes(encrypted), "report.pdf")
    with pytest.raises(UploadError):
        validate_upload(b"%PDF-broken", "report.pdf")


def test_pdf_page_and_image_pixel_limits():
    writer = PdfWriter()
    for _ in range(21):
        writer.add_blank_page(width=100, height=100)
    with pytest.raises(UploadError, match="1–20"):
        validate_upload(pdf_bytes(writer), "large.pdf")
    buf = BytesIO()
    Image.new("1", (5000, 5000)).save(buf, format="PNG")
    with pytest.raises(UploadError, match="megapixels"):
        validate_upload(buf.getvalue(), "big.png")


def test_evidence_integrity(tmp_path):
    from interpreter.demo import demo_reports
    from interpreter.models import ReportRecord
    from pydantic import ValidationError
    kb = KnowledgeBase(tmp_path / "chroma")
    record = demo_reports(kb)[0]
    payload = record.model_dump()
    payload["checked"][0]["evidence"]["text"] = "Tampered"
    with pytest.raises(ValidationError, match="integrity"):
        ReportRecord.model_validate(payload)


def test_pdf_attachment_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_attachment("hidden.txt", b"Untrusted content")
    with pytest.raises(UploadError, match="embedded"):
        validate_upload(pdf_bytes(writer), "attachment.pdf")
