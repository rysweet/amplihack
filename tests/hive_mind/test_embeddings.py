"""Tests for hive_mind.embeddings -- vector embedding generation and similarity.

Tests both the available and unavailable paths for sentence-transformers,
ensuring graceful degradation when the optional dependency is missing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np


class TestEmbeddingGeneratorAvailability:
    """Test availability detection and graceful degradation."""

    def test_has_sentence_transformers_flag_exists(self):
        """HAS_SENTENCE_TRANSFORMERS flag is exported."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import HAS_SENTENCE_TRANSFORMERS

        assert isinstance(HAS_SENTENCE_TRANSFORMERS, bool)

    def test_generator_available_property_false_when_no_model(self):
        """available is False when model fails to load."""
        with patch(
            "amplihack.agents.goal_seeking.hive_mind.embeddings.HAS_SENTENCE_TRANSFORMERS",
            False,
        ):
            from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

            gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
            gen._model = None
            gen._dimension = 0
            gen._model_name = "test"
            assert gen.available is False

    def test_embed_returns_none_when_unavailable(self):
        """embed() returns None when model is not loaded."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._model = None
        gen._dimension = 0
        gen._model_name = "test"
        result = gen.embed("test text")
        assert result is None

    def test_embed_batch_returns_none_when_unavailable(self):
        """embed_batch() returns None when model is not loaded."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._model = None
        gen._dimension = 0
        gen._model_name = "test"
        result = gen.embed_batch(["a", "b"])
        assert result is None

    def test_embed_batch_returns_none_for_empty_list(self):
        """embed_batch() returns None for empty input."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._model = None
        gen._dimension = 0
        gen._model_name = "test"
        result = gen.embed_batch([])
        assert result is None


class TestCossineSimilarity:
    """Test cosine similarity computation (no model needed)."""

    def test_identical_vectors(self):
        """Identical normalized vectors have similarity 1.0."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        v = np.array([0.6, 0.8], dtype=np.float32)
        sim = EmbeddingGenerator.cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-5

    def test_orthogonal_vectors(self):
        """Orthogonal vectors have similarity ~0.0."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        sim = EmbeddingGenerator.cosine_similarity(a, b)
        assert abs(sim) < 1e-5

    def test_opposite_vectors(self):
        """Opposite vectors have similarity -1.0."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        sim = EmbeddingGenerator.cosine_similarity(a, b)
        assert abs(sim - (-1.0)) < 1e-5

    def test_cosine_similarity_batch(self):
        """Batch similarity returns correct scores."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        query = np.array([1.0, 0.0], dtype=np.float32)
        candidates = [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
            np.array([-1.0, 0.0], dtype=np.float32),
        ]
        scores = EmbeddingGenerator.cosine_similarity_batch(query, candidates)
        assert len(scores) == 3
        assert abs(scores[0] - 1.0) < 1e-5
        assert abs(scores[1]) < 1e-5
        assert abs(scores[2] - (-1.0)) < 1e-5

    def test_cosine_similarity_batch_empty(self):
        """Batch similarity returns empty list for empty input."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        query = np.array([1.0, 0.0], dtype=np.float32)
        scores = EmbeddingGenerator.cosine_similarity_batch(query, [])
        assert scores == []


class TestEmbeddingGeneratorWithMockModel:
    """Test EmbeddingGenerator with a mocked sentence-transformers model."""

    def test_embed_with_mock_model(self):
        """embed() delegates to model.encode with normalize_embeddings=True."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        mock_model = MagicMock()
        expected = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        mock_model.encode.return_value = expected
        gen._model = mock_model
        gen._dimension = 3
        gen._model_name = "test"

        result = gen.embed("test text")
        mock_model.encode.assert_called_once_with("test text", normalize_embeddings=True)
        np.testing.assert_array_equal(result, expected)

    def test_embed_batch_with_mock_model(self):
        """embed_batch() delegates to model.encode for batch."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        mock_model = MagicMock()
        embeddings = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        mock_model.encode.return_value = embeddings
        gen._model = mock_model
        gen._dimension = 2
        gen._model_name = "test"

        result = gen.embed_batch(["text1", "text2"])
        assert result is not None
        assert len(result) == 2
        np.testing.assert_array_equal(result[0], embeddings[0])
        np.testing.assert_array_equal(result[1], embeddings[1])

    def test_available_true_when_model_loaded(self):
        """available is True when model is loaded."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._model = MagicMock()
        gen._dimension = 768
        gen._model_name = "test"
        assert gen.available is True

    def test_dimension_reflects_model(self):
        """dimension matches the model's embedding dimension."""
        from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._model = MagicMock()
        gen._dimension = 768
        gen._model_name = "test"
        assert gen.dimension == 768


class TestHiveFactEmbeddingField:
    """Test that HiveFact supports the embedding field."""

    def test_hivefact_has_embedding_field(self):
        """HiveFact has an embedding field defaulting to None."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        fact = HiveFact(fact_id="f1", content="test")
        assert fact.embedding is None

    def test_hivefact_stores_embedding(self):
        """HiveFact can store a numpy array embedding."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        fact = HiveFact(fact_id="f1", content="test", embedding=embedding)
        np.testing.assert_array_equal(fact.embedding, embedding)


class TestVectorSearchInQueryFacts:
    """Test that query_facts uses vector search when embeddings are available."""

    def test_keyword_search_still_works(self):
        """query_facts still returns keyword matches without embeddings."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact(
            "a1", HiveFact(fact_id="f1", content="DNA stores genetic info", concept="biology")
        )
        hive.promote_fact(
            "a1", HiveFact(fact_id="f2", content="Python is a language", concept="programming")
        )

        results = hive.query_facts("DNA genetics")
        assert len(results) >= 1
        assert results[0].fact_id == "f1"

    def test_empty_query_returns_all(self):
        """Empty query returns all facts."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact("a1", HiveFact(fact_id="f1", content="fact one"))
        hive.promote_fact("a1", HiveFact(fact_id="f2", content="fact two"))

        results = hive.query_facts("")
        assert len(results) == 2

    def test_vector_search_with_mock_embedder(self):
        """query_facts uses vector search when embedder is available."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        mock_embedder = MagicMock()
        mock_embedder.available = True
        query_vec = np.array([0.9, 0.1], dtype=np.float32)
        mock_embedder.embed.return_value = query_vec

        hive = InMemoryHiveGraph("test", embedder=mock_embedder)
        hive.register_agent("a1")

        close_embedding = np.array([0.95, 0.05], dtype=np.float32)
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic info",
                concept="biology",
                embedding=close_embedding,
            ),
        )
        hive.promote_fact(
            "a1",
            HiveFact(fact_id="f2", content="Python programming language", concept="tech"),
        )

        results = hive.query_facts("DNA")
        assert len(results) >= 1
        assert results[0].fact_id == "f1"

    def test_vector_search_falls_back_when_embedder_unavailable(self):
        """query_facts falls back to keyword search when embedder is not available."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        mock_embedder = MagicMock()
        mock_embedder.available = False

        hive = InMemoryHiveGraph("test", embedder=mock_embedder)
        hive.register_agent("a1")
        hive.promote_fact(
            "a1", HiveFact(fact_id="f1", content="DNA stores genetic info", concept="biology")
        )

        results = hive.query_facts("DNA")
        assert len(results) == 1
        assert results[0].fact_id == "f1"
        mock_embedder.embed.assert_not_called()

    def test_vector_search_without_embedder(self):
        """query_facts works normally without any embedder (backward compat)."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        hive = InMemoryHiveGraph("test")
        hive.register_agent("a1")
        hive.promote_fact(
            "a1",
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic info",
                concept="biology",
                embedding=np.array([0.5, 0.5], dtype=np.float32),
            ),
        )

        results = hive.query_facts("DNA")
        assert len(results) == 1
        assert results[0].fact_id == "f1"

    def test_vector_search_embedding_exception_graceful(self):
        """query_facts handles embedding failures gracefully."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        mock_embedder = MagicMock()
        mock_embedder.available = True
        mock_embedder.embed.side_effect = RuntimeError("model crashed")

        hive = InMemoryHiveGraph("test", embedder=mock_embedder)
        hive.register_agent("a1")
        hive.promote_fact(
            "a1", HiveFact(fact_id="f1", content="DNA stores genetic info", concept="biology")
        )

        results = hive.query_facts("DNA")
        assert len(results) == 1
        assert results[0].fact_id == "f1"
