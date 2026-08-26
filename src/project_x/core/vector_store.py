"""FAISS vector store manager with safe JSON metadata persistence."""

import json
import logging
from pathlib import Path

import faiss
import numpy as np

from project_x.core.config import settings
from project_x.ingestion.models import ChunkMetadata, DocumentChunk
from project_x.retrieval.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"


class FAISSVectorStore:
    """Manages a FAISS IndexFlatIP index with structured JSON metadata.

    Uses L2-normalized embeddings so that Inner Product equals
    Cosine Similarity. Metadata is stored as JSON alongside the
    binary FAISS index to avoid pickle security risks.
    """

    def __init__(self, index_dir: Path | None = None):
        self._index_dir = Path(index_dir) if index_dir else settings.FAISS_INDEX_DIR
        self._embedding_service = get_embedding_service()
        self._dimension = int(self._embedding_service.dimension)

        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(self._dimension)
        self._metadata: dict[int, dict] = {}
        self._vectors: list[np.ndarray] = []
        self._next_id: int = 0

        self._try_load()

    def _try_load(self) -> None:
        """Attempt to load an existing index from disk."""
        index_path = self._index_dir / INDEX_FILENAME
        meta_path = self._index_dir / METADATA_FILENAME

        if index_path.exists() and meta_path.exists():
            try:
                self._index = faiss.read_index(str(index_path))
                with open(meta_path, "r", encoding="utf-8") as f:
                    raw_meta = json.load(f)
                self._metadata = {int(k): v for k, v in raw_meta.items()}
                self._next_id = max(self._metadata.keys(), default=-1) + 1
                # Reconstruct stored vectors for potential rebuild operations
                if self._index.ntotal > 0:
                    self._vectors = [
                        self._index.reconstruct(i) for i in range(self._index.ntotal)
                    ]
                logger.info(
                    "Loaded FAISS index with %d vectors from %s",
                    self._index.ntotal, self._index_dir,
                )
            except Exception as e:
                logger.warning("Failed to load index from %s: %s", self._index_dir, e)
                self._reset()

    def _reset(self) -> None:
        """Reset to an empty index state."""
        self._index = faiss.IndexFlatIP(int(self._dimension))
        self._metadata = {}
        self._vectors = []
        self._next_id = 0

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Embed and add document chunks to the FAISS index.

        Args:
            chunks: List of DocumentChunk objects from the ingestion engine.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        vectors = self._embedding_service.embed_documents(texts)

        for i, chunk in enumerate(chunks):
            idx = self._next_id
            self._metadata[idx] = chunk.model_dump()
            self._vectors.append(vectors[i])
            self._next_id += 1

        self._index.add(vectors)
        self._save()

        logger.info("Added %d chunks to index (total: %d)", len(chunks), self._index.ntotal)
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float = 0.0,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search the index for chunks most similar to the query.

        Args:
            query: Search query string.
            top_k: Maximum number of results to return (default from config).
            score_threshold: Minimum cosine similarity score to include.

        Returns:
            List of (DocumentChunk, similarity_score) tuples, sorted by score descending.
        """
        if self._index.ntotal == 0:
            return []

        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL

        top_k = min(top_k, self._index.ntotal)
        query_vector = self._embedding_service.embed_query(query)
        scores, indices = self._index.search(query_vector, top_k)

        results: list[tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < score_threshold:
                continue
            chunk_data = self._metadata.get(int(idx))
            if chunk_data is None:
                continue
            chunk = DocumentChunk(**chunk_data)
            results.append((chunk, float(score)))

        return results

    def delete_document(self, doc_id: str) -> int:
        """Remove all chunks belonging to a document and rebuild the index.

        Args:
            doc_id: The document identifier to remove.

        Returns:
            Number of chunks removed.
        """
        ids_to_remove = {
            idx for idx, meta in self._metadata.items()
            if meta.get("metadata", {}).get("doc_id") == doc_id
        }

        if not ids_to_remove:
            return 0

        removed_count = len(ids_to_remove)

        # Rebuild index with remaining chunks
        remaining_metadata: dict[int, dict] = {}
        remaining_vectors: list[np.ndarray] = []
        new_id = 0

        sorted_ids = sorted(self._metadata.keys())
        for old_id in sorted_ids:
            if old_id in ids_to_remove:
                continue
            remaining_metadata[new_id] = self._metadata[old_id]
            remaining_vectors.append(self._vectors[old_id])
            new_id += 1

        self._reset()
        self._next_id = new_id
        self._metadata = remaining_metadata
        self._vectors = remaining_vectors

        if remaining_vectors:
            vectors_array = np.array(remaining_vectors, dtype=np.float32)
            self._index.add(vectors_array)

        self._save()
        logger.info(
            "Deleted %d chunks for doc_id '%s' (remaining: %d)",
            removed_count, doc_id, self._index.ntotal,
        )
        return removed_count

    def list_documents(self) -> list[dict]:
        """Summarize all indexed documents.

        Returns:
            List of dicts with doc_id, source, total_chunks, and file_type.
        """
        doc_stats: dict[str, dict] = {}
        for meta in self._metadata.values():
            chunk_meta = meta.get("metadata", {})
            doc_id = chunk_meta.get("doc_id", "unknown")
            if doc_id not in doc_stats:
                doc_stats[doc_id] = {
                    "doc_id": doc_id,
                    "source": chunk_meta.get("source", "unknown"),
                    "total_chunks": 0,
                    "pages": set(),
                }
            doc_stats[doc_id]["total_chunks"] += 1
            page = chunk_meta.get("page")
            if page is not None:
                doc_stats[doc_id]["pages"].add(page)

        results = []
        for doc in doc_stats.values():
            results.append({
                "doc_id": doc["doc_id"],
                "source": doc["source"],
                "total_chunks": doc["total_chunks"],
                "total_pages": len(doc["pages"]) if doc["pages"] else None,
            })
        return results

    def clear_index(self) -> None:
        """Reset the index completely and remove persisted files."""
        self._reset()
        index_path = self._index_dir / INDEX_FILENAME
        meta_path = self._index_dir / METADATA_FILENAME
        index_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        logger.info("Index cleared and disk files removed from %s", self._index_dir)

    @property
    def total_chunks(self) -> int:
        """Total number of vectors in the index."""
        return self._index.ntotal

    def _save(self) -> None:
        """Persist the FAISS index and metadata to disk."""
        self._index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_dir / INDEX_FILENAME))
        serializable_meta = {str(k): v for k, v in self._metadata.items()}
        with open(self._index_dir / METADATA_FILENAME, "w", encoding="utf-8") as f:
            json.dump(serializable_meta, f, ensure_ascii=False, indent=2)
