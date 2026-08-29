"""BM25 sparse lexical search index for hybrid retrieval.

Provides exact keyword matching that complements FAISS dense vector
search. Particularly effective for invoice numbers, error codes,
medical terms, and acronyms that embedding models may under-represent.
"""

import logging
import re

from rank_bm25 import BM25Okapi

from project_x.ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)

# Stopwords to remove during tokenization (common English words
# that carry minimal discriminative value for retrieval)
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these", "they",
    "this", "to", "was", "will", "with",
})

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:[-_.][a-zA-Z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens with stopword removal.

    Preserves hyphenated compounds (e.g., 'ms-marco', 'BOM5-158510')
    and dotted identifiers (e.g., 'v1.5', 'sec3.2') as single tokens.
    """
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


class BM25Index:
    """In-memory BM25Okapi sparse index over DocumentChunk text.

    Builds a tokenized corpus from document chunks and supports
    scored retrieval, source-scoped filtering, and incremental
    document deletion with index rebuild.
    """

    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []
        self._corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    @property
    def total_chunks(self) -> int:
        """Number of chunks currently indexed."""
        return len(self._chunks)

    def index_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Add chunks to the BM25 index.

        Tokenizes each chunk's text and rebuilds the BM25Okapi model.

        Args:
            chunks: List of DocumentChunk objects to index.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        for chunk in chunks:
            self._chunks.append(chunk)
            self._corpus.append(tokenize(chunk.text))

        self._rebuild()
        logger.info(
            "BM25 index updated: added %d chunks (total: %d)",
            len(chunks), len(self._chunks),
        )
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 15,
        doc_ids: list[str] | set[str] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search the BM25 index for the most relevant chunks.

        Args:
            query: User search query.
            top_k: Maximum number of results to return.
            doc_ids: Optional source-scoping filter.

        Returns:
            List of (DocumentChunk, bm25_score) tuples sorted by
            relevance descending.
        """
        if self._bm25 is None or not self._chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Build (index, score) pairs and optionally filter by doc_ids.
        # BM25Okapi can produce negative IDF values for terms appearing
        # in more than half the corpus, so we only skip exact-zero scores
        # (documents that share zero query terms).
        allowed_ids = set(doc_ids) if doc_ids is not None else None
        candidates: list[tuple[int, float]] = []
        for idx, score in enumerate(scores):
            if score == 0.0:
                continue
            if allowed_ids and self._chunks[idx].metadata.doc_id not in allowed_ids:
                continue
            candidates.append((idx, float(score)))

        # Sort by score descending and take top_k
        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:top_k]

        return [(self._chunks[idx], score) for idx, score in candidates]

    def delete_document(self, doc_id: str) -> int:
        """Remove all chunks belonging to a document and rebuild.

        Args:
            doc_id: The document identifier to remove.

        Returns:
            Number of chunks removed.
        """
        original_count = len(self._chunks)
        remaining_chunks = [
            c for c in self._chunks
            if c.metadata.doc_id != doc_id
        ]
        removed = original_count - len(remaining_chunks)

        if removed == 0:
            return 0

        self._chunks = remaining_chunks
        self._corpus = [tokenize(c.text) for c in self._chunks]
        self._rebuild()

        logger.info(
            "BM25 index: deleted %d chunks for doc_id '%s' (remaining: %d)",
            removed, doc_id, len(self._chunks),
        )
        return removed

    def clear(self) -> None:
        """Reset the BM25 index to empty state."""
        self._chunks = []
        self._corpus = []
        self._bm25 = None
        logger.info("BM25 index cleared")

    def _rebuild(self) -> None:
        """Rebuild the BM25Okapi model from the current corpus."""
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
        else:
            self._bm25 = None
