"""Reciprocal Rank Fusion (RRF) for merging dense and sparse retrieval results.

RRF combines ranked lists from multiple retrieval methods using rank
positions instead of raw scores, avoiding score-calibration issues between
FAISS cosine similarity (0.0 to 1.0) and BM25 log-odds (0 to 25+).

Formula: RRF_score(d) = sum( 1 / (k + rank_m(d)) ) for each method m
Default k=60 follows the original RRF paper (Cormack et al., 2009).
"""

import logging

from project_x.ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    dense_results: list[tuple[DocumentChunk, float]],
    sparse_results: list[tuple[DocumentChunk, float]],
    k: int = 60,
) -> list[tuple[DocumentChunk, float]]:
    """Merge dense (FAISS) and sparse (BM25) ranked lists using RRF.

    Each document receives an RRF score based on its rank position
    in each result list. Documents appearing in both lists accumulate
    scores from both ranks.

    Args:
        dense_results: Ranked (chunk, score) pairs from FAISS vector search.
        sparse_results: Ranked (chunk, score) pairs from BM25 lexical search.
        k: RRF smoothing constant (default: 60).

    Returns:
        Merged list of (DocumentChunk, rrf_score) sorted by RRF score descending.
    """
    # Map chunk_id to (chunk, accumulated_rrf_score)
    scores: dict[str, tuple[DocumentChunk, float]] = {}

    # Score dense results by rank position
    for rank, (chunk, _original_score) in enumerate(dense_results):
        cid = chunk.chunk_id
        rrf_score = 1.0 / (k + rank + 1)
        if cid in scores:
            existing_chunk, existing_score = scores[cid]
            scores[cid] = (existing_chunk, existing_score + rrf_score)
        else:
            scores[cid] = (chunk, rrf_score)

    # Score sparse results by rank position
    for rank, (chunk, _original_score) in enumerate(sparse_results):
        cid = chunk.chunk_id
        rrf_score = 1.0 / (k + rank + 1)
        if cid in scores:
            existing_chunk, existing_score = scores[cid]
            scores[cid] = (existing_chunk, existing_score + rrf_score)
        else:
            scores[cid] = (chunk, rrf_score)

    # Sort by RRF score descending
    merged = sorted(scores.values(), key=lambda x: x[1], reverse=True)

    logger.debug(
        "RRF fusion: %d dense + %d sparse -> %d merged candidates",
        len(dense_results), len(sparse_results), len(merged),
    )

    return merged
