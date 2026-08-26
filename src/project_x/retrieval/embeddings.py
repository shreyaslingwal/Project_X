"""FastEmbed CPU embedding service for document and query vectorization."""

import numpy as np
from fastembed import TextEmbedding

from project_x.core.config import settings


class EmbeddingService:
    """Manages text embedding using FastEmbed on CPU 

    Uses BAAI/bge-small-en-v1.5 by default (384 dimensions, ONNX Runtime).
    All output vectors are L2-normalized for cosine similarity via Inner Product.
    """

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._model: TextEmbedding | None = None

    @property
    def model(self) -> TextEmbedding:
        """Lazy-load the embedding model on first use."""
        if self._model is None:
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension for the loaded model."""
        if not hasattr(self, "_dimension_cache"):
            sample = list(self.model.embed(["dimension probe"]))
            self._dimension_cache = len(sample[0])
        return self._dimension_cache

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Generate L2-normalized embeddings for document chunks.

        Args:
            texts: List of document text chunks.

        Returns:
            numpy array of shape (len(texts), dimension) with unit-norm rows.
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.dimension)

        embeddings = list(self.model.embed(texts))
        vectors = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    def embed_query(self, query: str) -> np.ndarray:
        """Generate L2-normalized embedding for a search query.

        Args:
            query: The search query string.

        Returns:
            numpy array of shape (1, dimension) with unit norm.
        """
        embeddings = list(self.model.query_embed(query))
        vector = np.array(embeddings, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Singleton getter for the embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
