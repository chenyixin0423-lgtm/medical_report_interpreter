"""Bounded local validation. Raw uploads are never written to disk."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_PAGES = 20


class UploadError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    media_type: str


def _inspect_pdf(reader):
    forbidden = {"/JavaScript", "/JS", "/OpenAction", "/AA", "/Launch", "/EmbeddedFiles",
                 "/EmbeddedFile", "/EF", "/AF", "/FileAttachment", "/RichMedia", "/XFA",
                 "/AcroForm", "/URI", "/SubmitForm", "/GoToR"}
    seen = set()
    stack = [reader.trailer]
    visited = 0
    while stack:
        item = stack.pop()
        visited += 1
        if visited > 50_000:
            raise UploadError("PDF is too complex. Use a flattened image instead.")
        if isinstance(item, IndirectObject):
            identity = (item.idnum, item.generation)
            if identity in seen:
                continue
            seen.add(identity)
            stack.append(item.get_object())
        elif isinstance(item, DictionaryObject):
            if (forbidden.intersection(item.keys())
                    or any(str(item.get(k)) in forbidden for k in ("/S", "/Type", "/Subtype"))):
                raise UploadError("Interactive or embedded PDF content is not accepted. Use a flattened image.")
            stack.extend(item.values())
        elif isinstance(item, ArrayObject):
            stack.extend(item)


def validate_upload(data: bytes, filename: str) -> ValidatedUpload:
    if not data or len(data) > MAX_BYTES:
        raise UploadError("Choose a non-empty file of at most 10 MB.")
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise UploadError("The file content does not match PDF format.")
        try:
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise UploadError("Encrypted PDFs are not supported.")
            if not 1 <= len(reader.pages) <= MAX_PAGES:
                raise UploadError("PDFs must contain 1–20 pages.")
            _inspect_pdf(reader)
        except UploadError:
            raise
        except Exception:
            raise UploadError("The PDF could not be validated. Use a flattened image.") from None
        return ValidatedUpload(data, "application/pdf")
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
    if suffix not in expected:
        raise UploadError("Use PDF, JPEG, PNG, or WEBP.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as im:
                if im.format != expected[suffix]:
                    raise UploadError("The file extension does not match its image content.")
                if im.width * im.height > MAX_PIXELS or getattr(im, "n_frames", 1) != 1:
                    raise UploadError("Use a single-frame image of at most 20 megapixels.")
                im.verify()
            with Image.open(BytesIO(data)) as im:
                output = BytesIO()
                # Decode and re-encode: strip metadata and trailing payloads.
                ImageOps.exif_transpose(im).convert("RGB").save(output, format="PNG")
                cleaned = output.getvalue()
                if len(cleaned) > MAX_BYTES:
                    raise UploadError("The decoded image is too large. Resize it before uploading.")
                return ValidatedUpload(cleaned, "image/png")
    except UploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise UploadError("The image could not be safely decoded.") from None
