"""FlashRank CPU cross-encoder reranking service for high-precision context filtering."""

import logging
from flashrank import Ranker, RerankRequest

from project_x.core.config import settings
from project_x.ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)


class RerankService:
    """Manages cross-encoder re-ranking using FlashRank on CPU.

    Uses ms-marco-MiniLM-L-12-v2 by default (~15MB RAM, ONNX Runtime).
    Computes cross-attention between Query and Chunk text to re-score
    and filter broad candidate chunks from the vector search stage.
    """

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.RERANKER_MODEL
        self._ranker: Ranker | None = None

    @property
    def ranker(self) -> Ranker:
        """Lazy-load the FlashRank model on first use."""
        if self._ranker is None:
            self._ranker = Ranker(model_name=self._model_name)
        return self._ranker

    def rerank(
        self,
        query: str,
        candidates: list[tuple[DocumentChunk, float]],
        top_k: int | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Re-rank candidate chunks against the query using cross-attention.

        Args:
            query: The user search query.
            candidates: List of (DocumentChunk, bi_encoder_score) tuples from vector search.
            top_k: Number of top re-ranked chunks to return (default: settings.TOP_K_RERANK).

        Returns:
            List of (DocumentChunk, cross_encoder_score) tuples sorted by score descending.
        """
        if not candidates:
            return []

        if top_k is None:
            top_k = settings.TOP_K_RERANK

        # Build passage payloads for FlashRank
        chunk_map: dict[str, DocumentChunk] = {}
        passages: list[dict] = []

        for i, (chunk, _) in enumerate(candidates):
            passage_id = chunk.chunk_id or f"chunk_{i}"
            chunk_map[passage_id] = chunk
            passages.append({
                "id": passage_id,
                "text": chunk.text,
            })

        rerank_request = RerankRequest(query=query, passages=passages)
        ranked_results = self.ranker.rerank(rerank_request)

        reranked_chunks: list[tuple[DocumentChunk, float]] = []
        for item in ranked_results[:top_k]:
            passage_id = str(item["id"])
            score = float(item["score"])
            original_chunk = chunk_map.get(passage_id)
            if original_chunk is not None:
                reranked_chunks.append((original_chunk, score))

        return reranked_chunks


_rerank_service: RerankService | None = None


def get_rerank_service() -> RerankService:
    """Singleton getter for the re-ranking service."""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service
