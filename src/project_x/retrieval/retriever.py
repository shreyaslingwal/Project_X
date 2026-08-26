"""Two-stage retrieval coordinator combining FAISS vector search and FlashRank re-ranking."""

import logging
from project_x.core.config import settings
from project_x.core.vector_store import FAISSVectorStore
from project_x.ingestion.models import DocumentChunk
from project_x.retrieval.reranker import RerankService, get_rerank_service

logger = logging.getLogger(__name__)


class TwoStageRetriever:
    """Coordinates broad FAISS vector retrieval followed by FlashRank precision re-ranking.

    Stage 1: Bi-encoder cosine similarity search across FAISS index (Top-15).
    Stage 2: Cross-encoder re-ranking using FlashRank to score and filter to Top-4.
    """

    def __init__(
        self,
        vector_store: FAISSVectorStore | None = None,
        rerank_service: RerankService | None = None,
    ):
        self._vector_store = vector_store or FAISSVectorStore()
        self._rerank_service = rerank_service or get_rerank_service()

    @property
    def vector_store(self) -> FAISSVectorStore:
        """Access underlying FAISS vector store."""
        return self._vector_store

    def retrieve(
        self,
        query: str,
        top_k_initial: int | None = None,
        top_k_final: int | None = None,
        doc_ids: list[str] | set[str] | None = None,
        score_threshold: float = 0.0,
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform 2-stage retrieval for the given query.

        Args:
            query: User search query.
            top_k_initial: Number of broad candidates from FAISS (default: settings.TOP_K_RETRIEVAL).
            top_k_final: Number of final re-ranked results (default: settings.TOP_K_RERANK).
            doc_ids: Optional list/set of doc_ids to filter sources (source-scoping).
            score_threshold: Minimum cosine similarity score for initial FAISS stage.

        Returns:
            List of (DocumentChunk, rerank_score) tuples sorted by relevance descending.
        """
        if not query or not query.strip():
            return []

        if top_k_initial is None:
            top_k_initial = settings.TOP_K_RETRIEVAL

        if top_k_final is None:
            top_k_final = settings.TOP_K_RERANK

        # Stage 1: Broad FAISS Vector Search
        initial_candidates = self._vector_store.similarity_search(
            query=query,
            top_k=top_k_initial,
            score_threshold=score_threshold,
        )

        if not initial_candidates:
            return []

        # Optional Source-Scoping Filter
        if doc_ids is not None:
            allowed_ids = set(doc_ids)
            initial_candidates = [
                (chunk, score)
                for chunk, score in initial_candidates
                if chunk.metadata.doc_id in allowed_ids
            ]

        if not initial_candidates:
            return []

        # Stage 2: FlashRank Precision Re-ranking
        reranked_results = self._rerank_service.rerank(
            query=query,
            candidates=initial_candidates,
            top_k=top_k_final,
        )

        return reranked_results


_retriever: TwoStageRetriever | None = None


def get_retriever() -> TwoStageRetriever:
    """Singleton getter for the TwoStageRetriever coordinator."""
    global _retriever
    if _retriever is None:
        _retriever = TwoStageRetriever()
    return _retriever
