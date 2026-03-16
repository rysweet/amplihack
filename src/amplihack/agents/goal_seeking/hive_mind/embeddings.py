"""Vector embeddings for semantic search in the hive mind.

Provides dense vector retrieval using sentence-transformers (BAAI/bge-base-en-v1.5)
with graceful fallback to keyword search when the model is unavailable.

Philosophy:
- Single responsibility: embed text, compute similarity
- Graceful degradation: keyword fallback when sentence-transformers missing
- No global state: each EmbeddingGenerator owns its model instance

Public API (the "studs"):
    EmbeddingGenerator: Embed text and compute cosine similarity
    HAS_SENTENCE_TRANSFORMERS: Feature flag for availability checks
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    HAS_NUMPY = False
    print("WARNING: numpy not available", file=sys.stderr)

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Optional dependency: sentence-transformers
# ---------------------------------------------------------------------------

from amplihack.utils.logging_utils import log_call

from .constants import DEFAULT_EMBEDDING_MODEL

try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]
    HAS_SENTENCE_TRANSFORMERS = False
    print("WARNING: sentence_transformers not available", file=sys.stderr)

# Backward-compatible alias
DEFAULT_MODEL = DEFAULT_EMBEDDING_MODEL


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers.

    Falls back to None embeddings when the library is unavailable,
    letting callers use keyword search instead.

    Args:
        model_name: HuggingFace model identifier.

    Example:
        >>> gen = EmbeddingGenerator()
        >>> if gen.available:
        ...     vec = gen.embed("DNA stores genetic information")
        ...     assert vec.shape == (gen.dimension,)
    """

    @log_call
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._dimension: int = 0

        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self._model = SentenceTransformer(model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info("Loaded embedding model %s (dim=%d)", model_name, self._dimension)
            except Exception:
                logger.warning("Failed to load embedding model %s", model_name, exc_info=True)
                self._model = None

    @property
    @log_call
    def available(self) -> bool:
        """Whether the embedding model is loaded and ready."""
        return self._model is not None

    @property
    @log_call
    def dimension(self) -> int:
        """Embedding vector dimension (0 if unavailable)."""
        return self._dimension

    @log_call
    def embed(self, text: str) -> NDArray[np.float32] | None:
        """Embed a single text string.

        Returns:
            Float32 numpy array of shape (dimension,), or None if unavailable.
        """
        if self._model is None:
            return None
        return self._model.encode(text, normalize_embeddings=True)

    @log_call
    def embed_batch(self, texts: list[str]) -> list[NDArray[np.float32]] | None:
        """Embed multiple texts in a single batch.

        Returns:
            List of float32 numpy arrays, or None if unavailable.
        """
        if self._model is None or not texts:
            return None
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [embeddings[i] for i in range(len(texts))]

    @staticmethod
    @log_call
    def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
        """Compute cosine similarity between two normalized vectors.

        Since embeddings are L2-normalized, cosine similarity = dot product.

        Raises:
            ImportError: If numpy is not installed.
        """
        if not HAS_NUMPY:
            raise ImportError("numpy is required for cosine_similarity")
        return float(np.dot(a, b))

    @staticmethod
    @log_call
    def cosine_similarity_batch(
        query: NDArray[np.float32], candidates: list[NDArray[np.float32]]
    ) -> list[float]:
        """Compute cosine similarity between query and multiple candidates.

        Raises:
            ImportError: If numpy is not installed.
        """
        if not HAS_NUMPY:
            raise ImportError("numpy is required for cosine_similarity_batch")
        if not candidates:
            return []
        matrix = np.stack(candidates)
        scores = matrix @ query
        return scores.tolist()


__all__ = ["EmbeddingGenerator", "HAS_SENTENCE_TRANSFORMERS", "DEFAULT_MODEL"]
