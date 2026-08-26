"""PDF document loader using PyMuPDF for page-aware text extraction."""

from pathlib import Path

import pymupdf

from project_x.core.config import settings
from project_x.ingestion.security import clean_text


def load_pdf(file_path: Path) -> list[tuple[int, str]]:
    """Extract text from a PDF file, page by page.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of (page_number, cleaned_text) tuples.
        Page numbers are 1-indexed.

    Raises:
        ValueError: If the PDF exceeds the configured page limit or has no extractable text.
    """
    doc = pymupdf.open(str(file_path))
    try:
        page_count = len(doc)
        if page_count > settings.MAX_PAGES_PER_PDF:
            raise ValueError(
                f"PDF has {page_count} pages, exceeding the "
                f"{settings.MAX_PAGES_PER_PDF}-page limit."
            )

        pages: list[tuple[int, str]] = []
        for page_num in range(page_count):
            page = doc[page_num]
            raw_text = page.get_text("text")
            cleaned = clean_text(raw_text)
            if cleaned:
                pages.append((page_num + 1, cleaned))

        if not pages:
            raise ValueError(
                f"No extractable text found in '{file_path.name}'. "
                f"The PDF may be image-based or empty."
            )
        return pages
    finally:
        doc.close()
