"""Semantic search and relevance scoring for experiences."""

from datetime import datetime

from .experience import Experience, ExperienceType


def calculate_relevance(experience: Experience, query: str) -> float:
    """Calculate relevance score for experience given query.

    Relevance factors:
    - Text similarity (TF-IDF)
    - Experience type weight (PATTERN=1.5x, INSIGHT=1.3x)
    - Confidence boost
    - Recency boost (decay over 90 days)

    Args:
        experience: Experience to score
        query: Search query

    Returns:
        Relevance score (0.0-1.0)
    """
    # Base similarity
    similarity = TFIDFSimilarity().calculate(experience.context, query)

    # Type weighting
    if experience.experience_type == ExperienceType.PATTERN:
        similarity *= 1.5
    elif experience.experience_type == ExperienceType.INSIGHT:
        similarity *= 1.3

    # Confidence boost
    similarity *= 0.5 + experience.confidence * 0.5

    # Recency boost (decay over 90 days)
    age_days = (datetime.now() - experience.timestamp).days
    recency_factor = max(0.7, 1.0 - (age_days / 90.0) * 0.3)  # 30% decay over 90 days, floor at 0.7
    similarity *= recency_factor

    # Cap at 1.0
    return min(similarity, 1.0)


class TFIDFSimilarity:
    """Simple TF-IDF similarity calculator."""

    def calculate(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Uses simple word overlap as approximation.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Normalize and tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union


def retrieve_relevant_experiences(
    experiences: list[Experience],
    current_context: str,
    top_k: int = 10,
    min_similarity: float = 0.0,
) -> list[Experience]:
    """Retrieve most relevant experiences for current context.

    Args:
        experiences: Pool of experiences to search
        current_context: Current context/query
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold

    Returns:
        Top-k most relevant experiences
    """
    # Calculate relevance for each
    scored = []
    for exp in experiences:
        relevance = calculate_relevance(exp, current_context)
        if relevance >= min_similarity:
            scored.append((relevance, exp))

    # Sort by relevance (descending)
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return top-k
    return [exp for _, exp in scored[:top_k]]


class SemanticSearchEngine:
    """Search engine with index for fast similarity search."""

    def __init__(self, experiences: list[Experience]):
        """Initialize search engine with corpus.

        Args:
            experiences: Initial corpus of experiences
        """
        self._experiences = list(experiences)
        self._build_index()

    def _build_index(self):
        """Build search index (simplified - just store experiences)."""
        # In a real implementation, this would build TF-IDF matrix

    @property
    def corpus_size(self) -> int:
        """Get corpus size."""
        return len(self._experiences)

    def is_indexed(self) -> bool:
        """Check if index is built."""
        return True

    def search(self, query: str, top_k: int = 10) -> list[Experience]:
        """Search for relevant experiences.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            Top-k matching experiences
        """
        return retrieve_relevant_experiences(self._experiences, query, top_k=top_k)

    def add_experience(self, experience: Experience) -> None:
        """Add experience to index.

        Args:
            experience: Experience to add
        """
        self._experiences.append(experience)

    def remove_experience(self, experience_id: str) -> None:
        """Remove experience from index.

        Args:
            experience_id: ID of experience to remove
        """
        self._experiences = [e for e in self._experiences if e.experience_id != experience_id]
