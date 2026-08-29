"""Source-grounded LLM generator with real-time token streaming.

Uses ChatOllama to produce answers strictly grounded in retrieved document
chunks, with inline [N] citation markers mapped by the CitationEngine.
Supports both synchronous streaming (CLI) and async streaming (FastAPI SSE).
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from functools import lru_cache

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from project_x.core.config import settings
from project_x.ingestion.models import DocumentChunk
from project_x.rag.citation_engine import Citation, CitationEngine
from project_x.rag.prompts import (
    GROUNDED_SYSTEM_PROMPT,
    format_grounded_user_prompt,
    format_sources_for_prompt,
)

logger = logging.getLogger(__name__)


class GroundedResponse(BaseModel):
    """Complete response from a grounded generation call."""

    answer: str = Field(description="Full generated answer text with inline citations")
    citations: list[Citation] = Field(default_factory=list)
    raw_chunks: list[DocumentChunk] = Field(default_factory=list)


class StreamEvent(BaseModel):
    """A single event emitted during streaming generation."""

    type: str = Field(description="Event type: 'token', 'citations', or 'error'")
    content: str = Field(default="", description="Token text or error message")
    citations: list[Citation] = Field(default_factory=list)


class GroundedGenerator:
    """Generates source-grounded answers using a local Ollama model.

    Enforces strict citation behavior through prompt engineering and
    maps inline citation markers back to exact source metadata.
    """

    def __init__(self) -> None:
        self._llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            num_ctx=settings.OLLAMA_NUM_CTX,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
        self._citation_engine = CitationEngine()

    def _build_messages(
        self,
        query: str,
        chunks: list[tuple[DocumentChunk, float]],
        chat_history: str = "",
    ) -> list:
        """Construct the system + user message pair for the LLM."""
        formatted_sources = format_sources_for_prompt(chunks)
        user_prompt = format_grounded_user_prompt(
            query=query,
            formatted_sources=formatted_sources,
            formatted_history=chat_history,
        )
        return [
            SystemMessage(content=GROUNDED_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

    def generate_response(
        self,
        query: str,
        chunks: list[tuple[DocumentChunk, float]],
        chat_history: str = "",
    ) -> GroundedResponse:
        """Generate a complete grounded response (blocking, non-streaming).

        Args:
            query: The user question (already contextualized).
            chunks: Retrieved and re-ranked (DocumentChunk, score) tuples.
            chat_history: Optional formatted conversation history string.

        Returns:
            GroundedResponse with answer text and resolved citations.
        """
        if not chunks:
            return GroundedResponse(
                answer="I could not find relevant information in the uploaded documents to answer this question.",
                citations=[],
                raw_chunks=[],
            )

        messages = self._build_messages(query, chunks, chat_history)

        try:
            response = self._llm.invoke(messages)
            answer = response.content.strip()
        except Exception as exc:
            logger.error("Generation failed: %s", exc)
            return GroundedResponse(
                answer=f"Generation failed: {exc}",
                citations=[],
                raw_chunks=[c for c, _ in chunks],
            )

        citations = self._citation_engine.extract_citations(answer, chunks)
        raw_chunks = [c for c, _ in chunks]

        return GroundedResponse(
            answer=answer,
            citations=citations,
            raw_chunks=raw_chunks,
        )

    def stream_response(
        self,
        query: str,
        chunks: list[tuple[DocumentChunk, float]],
        chat_history: str = "",
    ) -> Iterator[StreamEvent]:
        """Stream tokens in real-time followed by a citation resolution event.

        Yields StreamEvent objects:
        - type="token": individual text chunks as they arrive
        - type="citations": final event with resolved citation metadata

        Args:
            query: The user question (already contextualized).
            chunks: Retrieved and re-ranked (DocumentChunk, score) tuples.
            chat_history: Optional formatted conversation history string.
        """
        if not chunks:
            yield StreamEvent(
                type="token",
                content="I could not find relevant information in the uploaded documents to answer this question.",
            )
            yield StreamEvent(type="citations", citations=[])
            return

        messages = self._build_messages(query, chunks, chat_history)
        full_answer: list[str] = []

        try:
            for chunk in self._llm.stream(messages):
                token = chunk.content
                if token:
                    full_answer.append(token)
                    yield StreamEvent(type="token", content=token)
        except Exception as exc:
            logger.error("Streaming generation failed: %s", exc)
            yield StreamEvent(type="error", content=str(exc))
            return

        answer_text = "".join(full_answer)
        citations = self._citation_engine.extract_citations(answer_text, chunks)
        yield StreamEvent(type="citations", citations=citations)

    async def astream_response(
        self,
        query: str,
        chunks: list[tuple[DocumentChunk, float]],
        chat_history: str = "",
    ) -> AsyncIterator[StreamEvent]:
        """Async stream tokens for FastAPI SSE endpoints.

        Same behavior as stream_response but yields asynchronously.

        Args:
            query: The user question (already contextualized).
            chunks: Retrieved and re-ranked (DocumentChunk, score) tuples.
            chat_history: Optional formatted conversation history string.
        """
        if not chunks:
            yield StreamEvent(
                type="token",
                content="I could not find relevant information in the uploaded documents to answer this question.",
            )
            yield StreamEvent(type="citations", citations=[])
            return

        messages = self._build_messages(query, chunks, chat_history)
        full_answer: list[str] = []

        try:
            async for chunk in self._llm.astream(messages):
                token = chunk.content
                if token:
                    full_answer.append(token)
                    yield StreamEvent(type="token", content=token)
        except Exception as exc:
            logger.error("Async streaming generation failed: %s", exc)
            yield StreamEvent(type="error", content=str(exc))
            return

        answer_text = "".join(full_answer)
        citations = self._citation_engine.extract_citations(answer_text, chunks)
        yield StreamEvent(type="citations", citations=citations)


@lru_cache
def get_grounded_generator() -> GroundedGenerator:
    """Singleton getter for the grounded generator."""
    return GroundedGenerator()
