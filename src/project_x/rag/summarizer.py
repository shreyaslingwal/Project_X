"""Document summarization engine for Studio capabilities.

Generates structured briefings from indexed document chunks using the local
Ollama model. Supports both synchronous and async streaming output for
real-time token delivery via FastAPI SSE endpoints.
"""

import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from project_x.core.config import settings
from project_x.ingestion.models import DocumentChunk
from project_x.rag.generator import StreamEvent

logger = logging.getLogger(__name__)


SUMMARY_SYSTEM_PROMPT = """You are a document analysis assistant that creates structured briefings from source documents.

Rules:
1. Base your summary strictly on the provided document content. Do not add external knowledge.
2. Use the following structure for your output:

## Executive Overview
Write 2-3 concise paragraphs capturing the document's core thesis, purpose, and scope.

## Key Topics & Themes
List the major concepts and themes as bullet points. Include page or section references where available.

## Core Takeaways
Summarize the most important findings, decisions, or data points as bullet points.

## Suggested Follow-up Questions
Provide exactly 3-4 specific questions a reader could ask to explore the document further. Prefix each with "Q: ".

3. Keep the language clear and direct. Avoid filler phrases.
4. Use markdown formatting (bold, bullet lists, headers) for readability.
5. If the document content is too short or fragmentary to produce a full briefing, summarize what is available and note the limitation."""


def _format_chunks_for_summary(chunks: list[DocumentChunk]) -> str:
    """Assemble document chunks into a sequential text block for summarization.

    Chunks are sorted by page number and chunk index to preserve document flow.
    Each block is labeled with its source location for the LLM's reference.
    """
    if not chunks:
        return ""

    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c.metadata.page or 0, c.metadata.chunk_index),
    )

    blocks: list[str] = []
    for chunk in sorted_chunks:
        meta = chunk.metadata
        if meta.page is not None:
            location = f"Page {meta.page}"
        elif meta.section:
            location = f"Section: {meta.section}"
        else:
            location = "Document content"

        block = f"[{location}]\n{chunk.text.strip()}"
        blocks.append(block)

    return "\n\n".join(blocks)


def _build_summary_user_prompt(
    formatted_content: str,
    source_name: str = "the selected documents",
) -> str:
    """Construct the user prompt for document summarization."""
    return (
        f"Analyze the following content from {source_name} and produce "
        f"a structured briefing.\n\n"
        f"Document content:\n{formatted_content}"
    )


class DocumentSummarizer:
    """Generates structured document briefings using a local Ollama model.

    Produces executive overviews, key themes, core takeaways, and
    suggested follow-up questions from indexed document chunks.
    """

    def __init__(self) -> None:
        self._llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_ctx=settings.OLLAMA_NUM_CTX,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )

    def _build_messages(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
    ) -> list:
        """Construct the system + user message pair for summarization."""
        formatted_content = _format_chunks_for_summary(chunks)
        user_prompt = _build_summary_user_prompt(formatted_content, source_name)
        return [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

    def summarize(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
    ) -> str:
        """Generate a complete summary (blocking, non-streaming).

        Args:
            chunks: Document chunks to summarize, sorted by page/sequence.
            source_name: Display name for the source scope.

        Returns:
            Full summary text with structured sections.
        """
        if not chunks:
            return "No document content available to summarize."

        messages = self._build_messages(chunks, source_name)

        try:
            response = self._llm.invoke(messages)
            return response.content.strip()
        except Exception as exc:
            logger.error("Summary generation failed: %s", exc)
            return f"Summary generation failed: {exc}"

    async def astream_summary(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
    ) -> AsyncIterator[StreamEvent]:
        """Async stream summary tokens for FastAPI SSE endpoints.

        Yields StreamEvent objects with type 'token' for each text fragment,
        and type 'done' when generation completes. On failure, yields an
        'error' event.

        Args:
            chunks: Document chunks to summarize.
            source_name: Display name for the source scope.
        """
        if not chunks:
            yield StreamEvent(
                type="token",
                content="No document content available to summarize.",
            )
            yield StreamEvent(type="done")
            return

        messages = self._build_messages(chunks, source_name)

        try:
            async for chunk in self._llm.astream(messages):
                token = chunk.content
                if token:
                    yield StreamEvent(type="token", content=token)
        except Exception as exc:
            logger.error("Async summary streaming failed: %s", exc)
            yield StreamEvent(type="error", content=str(exc))
            return

        yield StreamEvent(type="done")


@lru_cache
def get_document_summarizer() -> DocumentSummarizer:
    """Singleton getter for the document summarizer."""
    return DocumentSummarizer()
