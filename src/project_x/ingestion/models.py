"""Pydantic models for document ingestion, chunking, and metadata tracking."""

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata attached to every document chunk for citation tracking."""

    source: str = Field(description="Original filename (e.g. 'paper.pdf')")
    doc_id: str = Field(description="Unique document identifier (UUID or hash)")
    page: int | None = Field(default=None, description="1-indexed page number (PDF only)")
    section: str | None = Field(default=None, description="Header breadcrumb (Markdown only)")
    chunk_index: int = Field(description="Sequential chunk index within the document")
    char_count: int = Field(description="Character count of the chunk text")


class DocumentChunk(BaseModel):
    """A single text chunk with full citation metadata."""

    chunk_id: str = Field(description="Unique chunk identifier (e.g. 'abc123_p3_c0')")
    text: str = Field(description="Clean text content of the chunk")
    metadata: ChunkMetadata


class IngestionResult(BaseModel):
    """Summary of a completed document ingestion."""

    doc_id: str
    filename: str
    file_type: str = Field(description="File extension (.pdf or .md)")
    total_pages: int | None = Field(default=None, description="Page count (PDF only)")
    total_chunks: int
    total_chars: int
    chunks: list[DocumentChunk]
