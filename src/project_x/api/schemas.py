"""Pydantic schemas for FastAPI request validation and response serialization."""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response after successful document ingestion and indexing."""

    doc_id: str
    filename: str
    file_type: str = Field(description="File extension (.pdf or .md)")
    total_pages: int | None = Field(default=None)
    total_chunks: int
    total_chars: int
    status: str = "indexed"


class DocumentItem(BaseModel):
    """Single document metadata entry for source listing."""

    doc_id: str
    source: str = Field(description="Original filename")
    total_chunks: int
    total_pages: int | None = Field(default=None)


class DocumentListResponse(BaseModel):
    """Response for GET /api/documents with summary statistics."""

    documents: list[DocumentItem]
    total_documents: int
    total_chunks: int


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    query: str = Field(min_length=1, description="User question text")
    session_id: str = Field(default="default", description="Conversation session identifier")
    doc_ids: list[str] | None = Field(default=None, description="Optional source-scoping filter")
    stream: bool = Field(default=True, description="Enable SSE token streaming")


class ClearChatRequest(BaseModel):
    """Request body for clearing a conversation session."""

    session_id: str = Field(default="default")


class ClearChatResponse(BaseModel):
    """Response after clearing a conversation session."""

    session_id: str
    status: str = "cleared"


class ChatHistoryResponse(BaseModel):
    """Response containing formatted conversation history."""

    session_id: str
    messages: list[dict]
    turn_count: int


class DeleteDocumentResponse(BaseModel):
    """Response after deleting a document from the index."""

    doc_id: str
    chunks_removed: int
    status: str = "deleted"


class HealthResponse(BaseModel):
    """System health and diagnostics."""

    status: str = "healthy"
    app_name: str
    generator_model: str
    rewriter_model: str
    embedding_model: str
    reranker_model: str
    total_documents: int
    total_chunks: int
