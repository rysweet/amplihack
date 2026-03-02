"""Optional embedding generation for semantic vector search.

Wraps sentence-transformers with graceful degradation: if the package
is not installed, all operations return None and callers fall back to
keyword search.

Uses BAAI/bge-base-en-v1.5 (768-dim, retrieval-optimized) following
the same model choice as agent-kgpacks.  BGE models require a special
query prefix for asymmetric retrieval.

Public API:
    EmbeddingGenerator: Lazy-loading embedding generator
    EMBEDDING_DIM: Dimension of the embedding vectors (768)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
_DEFAULT_MODEL = "BAAI/bge-base-en-v1.5"
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingGenerator:
    """Generates embeddings using sentence-transformers.

    Loads the model lazily on first use to avoid import-time overhead.
    If sentence-transformers is not installed, all methods return None.

    Args:
        model_name: HuggingFace model identifier.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model = None
        self._available: bool | None = None  # None = not yet checked

    @property
    def available(self) -> bool:
        """Whether embedding generation is available."""
        if self._available is None:
            self._ensure_model()
        return self._available is True

    def _ensure_model(self) -> None:
        """Load the model on first use."""
        if self._available is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._available = True
            logger.info("Loaded embedding model: %s", self._model_name)
        except ImportError:
            self._available = False
            logger.debug(
                "sentence-transformers not installed; vector search disabled. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as exc:
            self._available = False
            logger.warning("Failed to load embedding model %s: %s", self._model_name, exc)

    def generate(self, text: str) -> list[float] | None:
        """Generate embedding for a document/fact (no query prefix).

        Args:
            text: Text to embed.

        Returns:
            List of floats (768-dim), or None if unavailable.
        """
        self._ensure_model()
        if not self._available or self._model is None:
            return None
        if not text or not text.strip():
            return None
        try:
            embedding = self._model.encode(text, show_progress_bar=False)
            return embedding.tolist()
        except Exception as exc:
            logger.warning("Embedding generation failed: %s", exc)
            return None

    def generate_query(self, query: str) -> list[float] | None:
        """Generate embedding for a search query (with BGE prefix).

        BGE models require a special prefix for queries to enable
        asymmetric retrieval (queries and documents are encoded
        differently for better search quality).

        Args:
            query: Search query text.

        Returns:
            List of floats (768-dim), or None if unavailable.
        """
        if not query or not query.strip():
            return None
        return self.generate(f"{_QUERY_PREFIX}{query}")


# Module-level singleton — shared across all CognitiveMemory instances
# to avoid loading the model multiple times.
_shared_generator: EmbeddingGenerator | None = None


def get_shared_generator() -> EmbeddingGenerator:
    """Get or create the shared embedding generator singleton."""
    global _shared_generator
    if _shared_generator is None:
        _shared_generator = EmbeddingGenerator()
    return _shared_generator


__all__ = ["EmbeddingGenerator", "EMBEDDING_DIM", "get_shared_generator"]
