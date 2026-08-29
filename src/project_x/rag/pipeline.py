"""Master RAG pipeline coordinator uniting all milestone components.

Orchestrates the full query flow:
Memory -> Query Rewriter -> Two-Stage Retriever -> Grounded Generator -> Citations
"""

import logging
import time
from collections.abc import AsyncIterator, Iterator
from functools import lru_cache

from project_x.core.config import settings
from project_x.core.vector_store import FAISSVectorStore
from project_x.rag.citation_engine import CitationEngine
from project_x.rag.generator import (
    GroundedGenerator,
    GroundedResponse,
    StreamEvent,
    get_grounded_generator,
)
from project_x.rag.memory import ConversationMemory, get_conversation_memory
from project_x.retrieval.query_rewriter import QueryRewriter, get_query_rewriter
from project_x.retrieval.retriever import TwoStageRetriever, get_retriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end RAG pipeline with conversational memory and streaming generation.

    Connects all pipeline stages:
    1. Retrieves sliding-window chat history from ConversationMemory.
    2. Contextualizes query with QueryRewriter (Qwen 4B).
    3. Retrieves and re-ranks chunks with TwoStageRetriever (FAISS + FlashRank).
    4. Generates grounded answer with GroundedGenerator (streaming or blocking).
    5. Extracts and resolves inline citations.
    6. Commits user query and assistant response to session memory.
    """

    def __init__(
        self,
        memory: ConversationMemory | None = None,
        rewriter: QueryRewriter | None = None,
        retriever: TwoStageRetriever | None = None,
        generator: GroundedGenerator | None = None,
    ) -> None:
        self._memory = memory or get_conversation_memory()
        self._rewriter = rewriter or get_query_rewriter()
        self._retriever = retriever or get_retriever()
        self._generator = generator or get_grounded_generator()

    @property
    def memory(self) -> ConversationMemory:
        """Expose memory manager for external session management."""
        return self._memory

    @property
    def retriever(self) -> TwoStageRetriever:
        """Expose retriever for direct vector store access."""
        return self._retriever

    def _contextualize_query(self, session_id: str, query: str) -> str:
        """Rewrite query using conversation history for pronoun resolution.

        Skips rewriting on the first turn (no prior assistant turns) for instant response.
        """
        history_msgs = self._memory.get_history(session_id)
        has_prior_assistant = any(m.role == "assistant" for m in history_msgs)
        if not has_prior_assistant:
            return query

        history = self._memory.get_formatted_history(session_id)
        if not history:
            return query
        return self._rewriter.rewrite_query(query, history)

    def query(
        self,
        session_id: str,
        user_query: str,
        doc_ids: list[str] | None = None,
    ) -> GroundedResponse:
        """Execute the full RAG pipeline (blocking, non-streaming).

        Args:
            session_id: Conversation session identifier.
            user_query: The user's raw question.
            doc_ids: Optional list of doc_ids for source scoping.

        Returns:
            GroundedResponse with answer, citations, and raw chunks.
        """
        start = time.time()

        # Record user message in memory
        self._memory.add_user_message(session_id, user_query)

        # Contextualize query using conversation history
        standalone_query = self._contextualize_query(session_id, user_query)
        logger.info("Contextualized query: '%s' -> '%s'", user_query, standalone_query)

        # Retrieve and re-rank relevant chunks
        chunks = self._retriever.retrieve(standalone_query, doc_ids=doc_ids)

        # Get formatted history for generation context
        history = self._memory.get_formatted_history(session_id)

        # Generate grounded response
        response = self._generator.generate_response(
            query=standalone_query,
            chunks=chunks,
            chat_history=history,
        )

        # Save assistant response to memory with citation metadata
        citation_dicts = [c.model_dump() for c in response.citations]
        self._memory.add_assistant_message(
            session_id, response.answer, citations=citation_dicts
        )

        elapsed = time.time() - start
        logger.info(
            "Pipeline completed in %.1fs (%d citations)", elapsed, len(response.citations)
        )

        return response

    def stream_query(
        self,
        session_id: str,
        user_query: str,
        doc_ids: list[str] | None = None,
    ) -> Iterator[StreamEvent]:
        """Execute the RAG pipeline with real-time token streaming.

        Yields StreamEvent objects as tokens arrive from the LLM.
        Final event contains resolved citation metadata.
        Automatically commits the complete response to session memory.

        Args:
            session_id: Conversation session identifier.
            user_query: The user's raw question.
            doc_ids: Optional list of doc_ids for source scoping.
        """
        # Record user message in memory
        self._memory.add_user_message(session_id, user_query)

        # Contextualize query using conversation history
        standalone_query = self._contextualize_query(session_id, user_query)
        logger.info("Contextualized query: '%s' -> '%s'", user_query, standalone_query)

        # Retrieve and re-rank relevant chunks
        chunks = self._retriever.retrieve(standalone_query, doc_ids=doc_ids)

        # Get formatted history for generation context
        history = self._memory.get_formatted_history(session_id)

        # Stream grounded response and collect full answer for memory
        full_answer_parts: list[str] = []
        final_citations = []

        for event in self._generator.stream_response(
            query=standalone_query,
            chunks=chunks,
            chat_history=history,
        ):
            if event.type == "token":
                full_answer_parts.append(event.content)
            elif event.type == "citations":
                final_citations = event.citations

            yield event

        # Save complete assistant response to memory
        full_answer = "".join(full_answer_parts)
        if full_answer:
            citation_dicts = [c.model_dump() for c in final_citations]
            self._memory.add_assistant_message(
                session_id, full_answer, citations=citation_dicts
            )

    async def astream_query(
        self,
        session_id: str,
        user_query: str,
        doc_ids: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Async version of stream_query for FastAPI SSE endpoints.

        Args:
            session_id: Conversation session identifier.
            user_query: The user's raw question.
            doc_ids: Optional list of doc_ids for source scoping.
        """
        # Record user message in memory
        self._memory.add_user_message(session_id, user_query)

        # Contextualize query using conversation history
        standalone_query = self._contextualize_query(session_id, user_query)

        # Retrieve and re-rank relevant chunks
        chunks = self._retriever.retrieve(standalone_query, doc_ids=doc_ids)

        # Get formatted history for generation context
        history = self._memory.get_formatted_history(session_id)

        # Async stream grounded response
        full_answer_parts: list[str] = []
        final_citations = []

        async for event in self._generator.astream_response(
            query=standalone_query,
            chunks=chunks,
            chat_history=history,
        ):
            if event.type == "token":
                full_answer_parts.append(event.content)
            elif event.type == "citations":
                final_citations = event.citations

            yield event

        # Save complete assistant response to memory
        full_answer = "".join(full_answer_parts)
        if full_answer:
            citation_dicts = [c.model_dump() for c in final_citations]
            self._memory.add_assistant_message(
                session_id, full_answer, citations=citation_dicts
            )


@lru_cache
def get_rag_pipeline() -> RAGPipeline:
    """Singleton getter for the RAG pipeline."""
    return RAGPipeline()
