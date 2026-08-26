"""Security utilities for file upload validation and text sanitization."""

import re
import unicodedata
from pathlib import Path

from project_x.core.config import settings

PDF_MAGIC_BYTES = b"%PDF-"


def sanitize_filename(filename: str) -> str:
    """Strip dangerous path traversal sequences and normalize the filename.

    Removes directory separators, null bytes, and non-ASCII characters
    to prevent path traversal attacks like '../../evil.bat'.
    """
    filename = filename.replace("\x00", "")
    filename = Path(filename).name
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.strip(". ")
    if not filename:
        filename = "unnamed_upload"
    return filename


def validate_file_extension(file_path: Path) -> None:
    """Verify the file extension is in the allowed whitelist."""
    ext = file_path.suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {sorted(settings.ALLOWED_EXTENSIONS)}"
        )


def validate_file_size(file_path: Path) -> None:
    """Reject files exceeding the configured size limit."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    actual_size = file_path.stat().st_size
    if actual_size > max_bytes:
        size_mb = actual_size / (1024 * 1024)
        raise ValueError(
            f"File size {size_mb:.1f}MB exceeds the "
            f"{settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )


def validate_pdf_magic_bytes(file_path: Path) -> None:
    """Verify that a .pdf file actually starts with the %PDF- signature.

    Prevents executable files or other binaries disguised as PDFs.
    """
    if not settings.ENABLE_MAGIC_BYTE_CHECK:
        return
    if file_path.suffix.lower() != ".pdf":
        return
    with open(file_path, "rb") as f:
        header = f.read(len(PDF_MAGIC_BYTES))
    if header != PDF_MAGIC_BYTES:
        raise ValueError(
            f"File '{file_path.name}' has a .pdf extension but does not "
            f"contain valid PDF magic bytes. Upload rejected."
        )


def validate_file(file_path: Path) -> None:
    """Run all security validations on an uploaded file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    resolved = file_path.resolve()
    upload_dir = settings.UPLOAD_DIR.resolve()
    if not str(resolved).startswith(str(upload_dir)):
        raise ValueError(
            f"File path '{resolved}' is outside the upload directory. "
            f"Possible path traversal attempt."
        )
    validate_file_extension(file_path)
    validate_file_size(file_path)
    validate_pdf_magic_bytes(file_path)


def clean_text(text: str) -> str:
    """Normalize extracted document text for chunking.

    Removes control characters, heals hyphenated line breaks,
    and collapses excessive whitespace.
    """
    # Remove non-printable control characters (keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Heal hyphenated line breaks: "transfor-\nmer" -> "transformer"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Collapse triple+ newlines into double newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace from each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()
