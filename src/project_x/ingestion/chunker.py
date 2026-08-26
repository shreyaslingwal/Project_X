"""Boundary-aware recursive text chunker preserving page and section metadata."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from project_x.core.config import settings
from project_x.ingestion.models import ChunkMetadata, DocumentChunk

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _create_splitter() -> RecursiveCharacterTextSplitter:
    """Create a configured recursive text splitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def chunk_pdf_pages(
    pages: list[tuple[int, str]],
    doc_id: str,
    source: str,
) -> list[DocumentChunk]:
    """Chunk PDF pages while strictly preserving page boundaries.

    Each page is chunked independently so that no chunk ever
    spans across two different pages. This guarantees accurate
    page-level citations.

    Args:
        pages: List of (page_number, text) from the PDF loader.
        doc_id: Unique document identifier.
        source: Original filename.

    Returns:
        List of DocumentChunk objects with page metadata.
    """
    splitter = _create_splitter()
    chunks: list[DocumentChunk] = []
    global_index = 0

    for page_num, page_text in pages:
        page_chunks = splitter.split_text(page_text)
        for chunk_text in page_chunks:
            chunk_id = f"{doc_id}_p{page_num}_c{global_index}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=ChunkMetadata(
                        source=source,
                        doc_id=doc_id,
                        page=page_num,
                        section=None,
                        chunk_index=global_index,
                        char_count=len(chunk_text),
                    ),
                )
            )
            global_index += 1

    return chunks


def chunk_markdown_sections(
    sections: list[tuple[str, str]],
    doc_id: str,
    source: str,
) -> list[DocumentChunk]:
    """Chunk Markdown sections while preserving header boundaries.

    Each section is chunked independently so that no chunk ever
    spans across two different header sections. This preserves
    section context for citations.

    Args:
        sections: List of (section_breadcrumb, text) from the MD loader.
        doc_id: Unique document identifier.
        source: Original filename.

    Returns:
        List of DocumentChunk objects with section metadata.
    """
    splitter = _create_splitter()
    chunks: list[DocumentChunk] = []
    global_index = 0

    for section_name, section_text in sections:
        section_chunks = splitter.split_text(section_text)
        for chunk_text in section_chunks:
            chunk_id = f"{doc_id}_s{global_index}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=ChunkMetadata(
                        source=source,
                        doc_id=doc_id,
                        page=None,
                        section=section_name,
                        chunk_index=global_index,
                        char_count=len(chunk_text),
                    ),
                )
            )
            global_index += 1

    return chunks
