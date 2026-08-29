"""Hybrid retrieval coordinator combining Dense FAISS + Sparse BM25 + RRF + FlashRank.

When hybrid search is enabled (default), queries both FAISS vector search
and BM25 lexical search in parallel, merges with Reciprocal Rank Fusion,
then applies FlashRank cross-encoder precision re-ranking.

When hybrid search is disabled, falls back to pure FAISS + FlashRank.
"""

import logging

from project_x.core.config import settings
from project_x.core.vector_store import FAISSVectorStore
from project_x.ingestion.models import DocumentChunk
from project_x.retrieval.bm25 import BM25Index
from project_x.retrieval.fusion import reciprocal_rank_fusion
from project_x.retrieval.reranker import RerankService, get_rerank_service

logger = logging.getLogger(__name__)


class TwoStageRetriever:
    """Coordinates hybrid retrieval across dense and sparse indexes.

    Stage 1a: Bi-encoder cosine similarity via FAISS (Top-K dense).
    Stage 1b: BM25 lexical matching via rank-bm25 (Top-K sparse).
    Stage 2:  Reciprocal Rank Fusion merges both ranked lists.
    Stage 3:  FlashRank cross-encoder re-ranks fused candidates to Top-4.
    """

    def __init__(
        self,
        vector_store: FAISSVectorStore | None = None,
        bm25_index: BM25Index | None = None,
        rerank_service: RerankService | None = None,
    ):
        self._vector_store = vector_store or FAISSVectorStore()
        self._bm25_index = bm25_index or BM25Index()
        self._rerank_service = rerank_service or get_rerank_service()

        # Hydrate BM25 from existing FAISS metadata on startup
        if settings.ENABLE_HYBRID_SEARCH and self._bm25_index.total_chunks == 0:
            existing_chunks = self._vector_store.get_all_chunks()
            if existing_chunks:
                self._bm25_index.index_chunks(existing_chunks)
                logger.info(
                    "Hydrated BM25 index with %d chunks from FAISS metadata",
                    len(existing_chunks),
                )

    @property
    def vector_store(self) -> FAISSVectorStore:
        """Access underlying FAISS vector store."""
        return self._vector_store

    @property
    def bm25_index(self) -> BM25Index:
        """Access underlying BM25 sparse index."""
        return self._bm25_index

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Add chunks to both FAISS and BM25 indexes.

        Args:
            chunks: List of DocumentChunk objects to index.

        Returns:
            Number of chunks added to FAISS.
        """
        count = self._vector_store.add_chunks(chunks)
        if settings.ENABLE_HYBRID_SEARCH and count > 0:
            self._bm25_index.index_chunks(chunks)
        return count

    def delete_document(self, doc_id: str) -> int:
        """Remove a document from both FAISS and BM25 indexes.

        Args:
            doc_id: The document identifier to remove.

        Returns:
            Number of chunks removed from FAISS.
        """
        removed = self._vector_store.delete_document(doc_id)
        if settings.ENABLE_HYBRID_SEARCH and removed > 0:
            self._bm25_index.delete_document(doc_id)
        return removed

    def retrieve(
        self,
        query: str,
        top_k_initial: int | None = None,
        top_k_final: int | None = None,
        doc_ids: list[str] | set[str] | None = None,
        score_threshold: float = 0.0,
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform hybrid retrieval for the given query.

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

        # Stage 1a: Dense FAISS Vector Search
        dense_candidates = self._vector_store.similarity_search(
            query=query,
            top_k=top_k_initial,
            score_threshold=score_threshold,
        )

        # Stage 1b: Sparse BM25 Lexical Search (when hybrid is enabled)
        if settings.ENABLE_HYBRID_SEARCH and self._bm25_index.total_chunks > 0:
            sparse_candidates = self._bm25_index.search(
                query=query,
                top_k=settings.TOP_K_BM25,
                doc_ids=doc_ids,
            )

            # Stage 2: Reciprocal Rank Fusion
            fused_candidates = reciprocal_rank_fusion(
                dense_results=dense_candidates,
                sparse_results=sparse_candidates,
                k=settings.RRF_K,
            )

            logger.info(
                "Hybrid retrieval: %d dense + %d sparse -> %d fused candidates",
                len(dense_candidates), len(sparse_candidates), len(fused_candidates),
            )
        else:
            fused_candidates = dense_candidates

        if not fused_candidates:
            return []

        # Apply source-scoping filter (dense-only results may not be filtered yet)
        if doc_ids is not None:
            allowed_ids = set(doc_ids)
            fused_candidates = [
                (chunk, score)
                for chunk, score in fused_candidates
                if chunk.metadata.doc_id in allowed_ids
            ]

        if not fused_candidates:
            return []

        # Stage 3: FlashRank Precision Re-ranking
        reranked_results = self._rerank_service.rerank(
            query=query,
            candidates=fused_candidates,
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
