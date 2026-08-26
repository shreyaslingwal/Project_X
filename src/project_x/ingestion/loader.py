"""Unified document ingestion coordinator for PDF and Markdown files."""

import uuid
from pathlib import Path

from project_x.ingestion.chunker import chunk_markdown_sections, chunk_pdf_pages
from project_x.ingestion.md_loader import load_markdown
from project_x.ingestion.models import IngestionResult
from project_x.ingestion.pdf_loader import load_pdf
from project_x.ingestion.security import validate_file


def ingest_file(file_path: Path | str) -> IngestionResult:
    """Ingest a document file and produce metadata-rich chunks.

    Validates the file, extracts text using the appropriate loader
    (PDF or Markdown), and splits into boundary-aware chunks with
    full citation metadata.

    Args:
        file_path: Path to the file to ingest.

    Returns:
        IngestionResult with document info and all chunks.

    Raises:
        ValueError: If the file fails security validation or has no content.
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file_path)
    validate_file(file_path)

    doc_id = uuid.uuid4().hex[:12]
    filename = file_path.name
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        pages = load_pdf(file_path)
        chunks = chunk_pdf_pages(pages, doc_id=doc_id, source=filename)
        total_pages = len(pages)
    else:
        sections = load_markdown(file_path)
        chunks = chunk_markdown_sections(sections, doc_id=doc_id, source=filename)
        total_pages = None

    total_chars = sum(chunk.metadata.char_count for chunk in chunks)

    return IngestionResult(
        doc_id=doc_id,
        filename=filename,
        file_type=ext,
        total_pages=total_pages,
        total_chunks=len(chunks),
        total_chars=total_chars,
        chunks=chunks,
    )
