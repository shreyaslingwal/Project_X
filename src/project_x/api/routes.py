"""FastAPI route handlers for document management and streaming chat.

Endpoints:
    GET  /api/health              - System diagnostics
    POST /api/upload              - Ingest PDF/MD file
    GET  /api/documents           - List indexed sources
    DELETE /api/documents/{doc_id} - Remove a document
    POST /api/chat                - Streaming or blocking RAG chat
    POST /api/chat/clear          - Reset conversation session
    GET  /api/chat/history/{id}   - Retrieve session message history
"""

import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from project_x.api.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ClearChatRequest,
    ClearChatResponse,
    DeleteDocumentResponse,
    DocumentItem,
    DocumentListResponse,
    HealthResponse,
    SummaryRequest,
    SummaryResponse,
    UploadResponse,
)
from project_x.core.config import settings
from project_x.core.vector_store import FAISSVectorStore
from project_x.ingestion.loader import ingest_file
from project_x.rag.pipeline import RAGPipeline
from project_x.rag.summarizer import DocumentSummarizer, get_document_summarizer
from project_x.retrieval.retriever import TwoStageRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# Shared singleton instances initialized at module scope
_vector_store: FAISSVectorStore | None = None
_pipeline: RAGPipeline | None = None
_summarizer: DocumentSummarizer | None = None


def _get_vector_store() -> FAISSVectorStore:
    """Lazy singleton for the FAISS vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
    return _vector_store


def _get_pipeline() -> RAGPipeline:
    """Lazy singleton for the RAG pipeline (shares the vector store)."""
    global _pipeline
    if _pipeline is None:
        vs = _get_vector_store()
        retriever = TwoStageRetriever(vector_store=vs)
        _pipeline = RAGPipeline(retriever=retriever)
    return _pipeline


def _get_summarizer() -> DocumentSummarizer:
    """Lazy singleton for the document summarizer."""
    global _summarizer
    if _summarizer is None:
        _summarizer = get_document_summarizer()
    return _summarizer


def _get_chunks_for_docs(
    doc_ids: list[str] | None = None,
) -> tuple[list, list[str], int]:
    """Retrieve stored chunks filtered by doc_ids.

    Returns:
        Tuple of (filtered_chunks, matched_doc_ids, total_docs_in_scope).
    """
    vs = _get_vector_store()
    all_chunks = vs.get_all_chunks()

    if not doc_ids:
        unique_ids = list({c.metadata.doc_id for c in all_chunks})
        return all_chunks, unique_ids, len(unique_ids)

    doc_id_set = set(doc_ids)
    filtered = [c for c in all_chunks if c.metadata.doc_id in doc_id_set]
    matched_ids = list({c.metadata.doc_id for c in filtered})
    return filtered, matched_ids, len(matched_ids)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return system status, model configuration, and index statistics."""
    vs = _get_vector_store()
    docs = vs.list_documents()
    return HealthResponse(
        app_name=settings.APP_NAME,
        generator_model=settings.OLLAMA_MODEL,
        rewriter_model=settings.REWRITE_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        reranker_model=settings.RERANKER_MODEL,
        total_documents=len(docs),
        total_chunks=vs.total_chunks,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload, validate, ingest, and index a PDF or Markdown document.

    Security checks (extension whitelist, size limit, magic byte inspection)
    are performed by the ingestion pipeline's validate_file() function.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    # Check extension before writing to disk
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(settings.ALLOWED_EXTENSIONS)}",
        )

    # Check content-length if available
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.",
        )

    # Save uploaded file to disk
    settings.ensure_directories()
    save_path = settings.UPLOAD_DIR / file.filename
    try:
        with open(save_path, "wb") as buffer:
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                save_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.",
                )
            buffer.write(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")

    # Ingest and index
    try:
        result = ingest_file(save_path)
        pipeline = _get_pipeline()
        pipeline.retriever.add_chunks(result.chunks)

        return UploadResponse(
            doc_id=result.doc_id,
            filename=result.filename,
            file_type=result.file_type,
            total_pages=result.total_pages,
            total_chunks=result.total_chunks,
            total_chars=result.total_chars,
        )
    except ValueError as exc:
        # Security validation failure from validate_file()
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        logger.error("Ingestion failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """Return all indexed documents with metadata summaries."""
    vs = _get_vector_store()
    docs = vs.list_documents()
    items = [
        DocumentItem(
            doc_id=d["doc_id"],
            source=d["source"],
            total_chunks=d["total_chunks"],
            total_pages=d.get("total_pages"),
        )
        for d in docs
    ]
    return DocumentListResponse(
        documents=items,
        total_documents=len(items),
        total_chunks=vs.total_chunks,
    )


@router.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(doc_id: str):
    """Remove a document from both FAISS and BM25 indexes and delete the uploaded file."""
    pipeline = _get_pipeline()
    vs = pipeline.retriever.vector_store

    # Find the source filename before deletion
    docs = vs.list_documents()
    source_filename = None
    for d in docs:
        if d["doc_id"] == doc_id:
            source_filename = d["source"]
            break

    removed = pipeline.retriever.delete_document(doc_id)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    # Clean up the uploaded file from disk
    if source_filename:
        upload_path = settings.UPLOAD_DIR / source_filename
        upload_path.unlink(missing_ok=True)

    return DeleteDocumentResponse(doc_id=doc_id, chunks_removed=removed)


@router.post("/chat")
async def chat(request: ChatRequest):
    """Query the RAG pipeline with optional SSE streaming.

    When stream=True (default), returns a text/event-stream with:
        data: {"type": "token", "content": "..."}
        data: {"type": "citations", "citations": [...]}
        data: {"type": "done"}

    When stream=False, returns a JSON response with the complete answer.
    """
    pipeline = _get_pipeline()

    if not request.stream:
        # Blocking mode: return complete response as JSON
        response = pipeline.query(
            session_id=request.session_id,
            user_query=request.query,
            doc_ids=request.doc_ids,
        )
        return {
            "answer": response.answer,
            "citations": [c.model_dump() for c in response.citations],
        }

    # Streaming mode: SSE
    async def event_generator():
        try:
            async for event in pipeline.astream_query(
                session_id=request.session_id,
                user_query=request.query,
                doc_ids=request.doc_ids,
            ):
                if event.type == "token":
                    payload = json.dumps({"type": "token", "content": event.content})
                    yield f"data: {payload}\n\n"
                elif event.type == "citations":
                    citations_data = [c.model_dump() for c in event.citations]
                    payload = json.dumps({"type": "citations", "citations": citations_data})
                    yield f"data: {payload}\n\n"
                elif event.type == "error":
                    payload = json.dumps({"type": "error", "content": event.content})
                    yield f"data: {payload}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("SSE stream error: %s", exc)
            error_payload = json.dumps({"type": "error", "content": str(exc)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/clear", response_model=ClearChatResponse)
async def clear_chat(request: ClearChatRequest):
    """Clear conversation memory for a specific session."""
    pipeline = _get_pipeline()
    pipeline.memory.clear_session(request.session_id)
    return ClearChatResponse(session_id=request.session_id)


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Retrieve the conversation history for a session."""
    pipeline = _get_pipeline()
    messages = pipeline.memory.get_history(session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[m.model_dump() for m in messages],
        turn_count=len(messages) // 2,
    )


@router.post("/studio/summary")
async def studio_summary(request: SummaryRequest):
    """Generate a structured document summary with optional SSE streaming.

    When stream=True (default), returns a text/event-stream with:
        data: {"type": "token", "content": "..."}
        data: {"type": "done"}

    When stream=False, returns a JSON SummaryResponse.
    """
    chunks, matched_ids, doc_count = _get_chunks_for_docs(request.doc_ids)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No indexed chunks found for the requested documents.",
        )

    # Build a human-readable scope label for the prompt
    vs = _get_vector_store()
    doc_list = vs.list_documents()
    id_to_name = {d["doc_id"]: d["source"] for d in doc_list}
    if len(matched_ids) == 1:
        source_name = id_to_name.get(matched_ids[0], "the selected document")
    else:
        source_name = f"{doc_count} selected documents"

    summarizer = _get_summarizer()

    if not request.stream:
        summary_text = summarizer.summarize(chunks, source_name=source_name)
        return SummaryResponse(
            summary=summary_text,
            doc_count=doc_count,
            chunk_count=len(chunks),
        )

    # Streaming mode: SSE
    async def event_generator():
        try:
            async for event in summarizer.astream_summary(
                chunks, source_name=source_name
            ):
                if event.type == "token":
                    payload = json.dumps({"type": "token", "content": event.content})
                    yield f"data: {payload}\n\n"
                elif event.type == "error":
                    payload = json.dumps({"type": "error", "content": event.content})
                    yield f"data: {payload}\n\n"
                elif event.type == "done":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("Studio summary SSE error: %s", exc)
            error_payload = json.dumps({"type": "error", "content": str(exc)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
