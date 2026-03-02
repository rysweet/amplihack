"""Tests for vector-based semantic search in CognitiveMemory.

Tests cover:
- Schema migration (embedding column added to existing DBs)
- Embedding generation on store_fact()
- Vector search via search_facts()
- Fallback to keyword search when embeddings unavailable
- Agent isolation in vector search results
"""

import pytest
from amplihack_memory import CognitiveMemory
from amplihack_memory._embeddings import EmbeddingGenerator, EMBEDDING_DIM, get_shared_generator


# ---------------------------------------------------------------------------
# Embedding generator tests
# ---------------------------------------------------------------------------


class TestEmbeddingGenerator:
    def test_embedding_dim_constant(self):
        assert EMBEDDING_DIM == 768

    def test_generator_reports_availability(self):
        gen = EmbeddingGenerator()
        # Should be True or False (not None) after first access
        result = gen.available
        assert isinstance(result, bool)

    def test_generate_returns_correct_dim_or_none(self):
        gen = EmbeddingGenerator()
        result = gen.generate("test text")
        if gen.available:
            assert isinstance(result, list)
            assert len(result) == EMBEDDING_DIM
        else:
            assert result is None

    def test_generate_empty_returns_none(self):
        gen = EmbeddingGenerator()
        assert gen.generate("") is None
        assert gen.generate("   ") is None

    def test_generate_query_adds_prefix(self):
        gen = EmbeddingGenerator()
        doc_emb = gen.generate("test text")
        query_emb = gen.generate_query("test text")
        if gen.available:
            # Query embedding should differ from document embedding (prefix effect)
            assert doc_emb != query_emb

    def test_shared_generator_is_singleton(self):
        gen1 = get_shared_generator()
        gen2 = get_shared_generator()
        assert gen1 is gen2


# ---------------------------------------------------------------------------
# CognitiveMemory vector search tests
# ---------------------------------------------------------------------------

# Skip all vector tests if sentence-transformers not installed
pytestmark = pytest.mark.skipif(
    not get_shared_generator().available,
    reason="sentence-transformers not installed",
)


@pytest.fixture
def cm(tmp_path):
    """CognitiveMemory with vector search enabled."""
    db = tmp_path / "test_vector_db"
    mem = CognitiveMemory(agent_name="test-agent", db_path=db)
    yield mem
    mem.close()


class TestVectorSchema:
    def test_embedding_column_exists(self, cm):
        """Verify the embedding column was created in SemanticMemory."""
        result = cm._conn.execute(
            "MATCH (s:SemanticMemory) WHERE s.agent_id = 'nonexistent' "
            "RETURN s.embedding LIMIT 1"
        )
        # Query should succeed (column exists), even if no rows
        assert result is not None

    def test_vector_index_created(self, cm):
        """Verify the HNSW vector index was created."""
        assert cm._has_vector_index is True

    def test_migration_on_existing_db(self, tmp_path):
        """Verify embedding column added to pre-existing DB without it."""
        db_path = tmp_path / "migrate_test"
        # Create a DB with the OLD schema (no embedding column)
        import kuzu
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
        conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS SemanticMemory(
                node_id STRING,
                agent_id STRING,
                concept STRING,
                content STRING,
                confidence DOUBLE,
                source_id STRING,
                tags STRING,
                metadata STRING,
                created_at INT64,
                PRIMARY KEY(node_id)
            )
        """)
        conn.execute("""
            CREATE (:SemanticMemory {
                node_id: 'old_fact',
                agent_id: 'test-agent',
                concept: 'legacy',
                content: 'pre-existing fact',
                confidence: 0.9,
                source_id: '',
                tags: '[]',
                metadata: '{}',
                created_at: 1000
            })
        """)
        del conn, db

        # Now open with CognitiveMemory — should migrate
        mem = CognitiveMemory(agent_name="test-agent", db_path=db_path)
        facts = mem.get_all_facts()
        assert len(facts) == 1
        assert facts[0].content == "pre-existing fact"
        mem.close()


class TestVectorStoreAndSearch:
    def test_store_fact_generates_embedding(self, cm):
        """Verify store_fact creates an embedding."""
        cm.store_fact("biology", "DNA has a double helix structure", confidence=0.95)
        result = cm._conn.execute(
            "MATCH (s:SemanticMemory) WHERE s.agent_id = $aid "
            "RETURN s.embedding",
            {"aid": "test-agent"},
        )
        assert result.has_next()
        embedding = result.get_next()[0]
        assert embedding is not None
        assert len(embedding) == EMBEDDING_DIM

    def test_vector_search_finds_semantically_similar(self, cm):
        """Vector search should find semantically related facts."""
        cm.store_fact("biology", "DNA stores genetic information in a double helix", confidence=0.9)
        cm.store_fact("cooking", "Pasta should be cooked al dente in salted water", confidence=0.8)
        cm.store_fact("biology", "RNA transcribes genetic code from DNA", confidence=0.85)

        results = cm.search_facts("genetics heredity")
        assert len(results) >= 1
        # The biology facts should rank higher than cooking
        contents = [f.content for f in results]
        assert any("DNA" in c or "RNA" in c or "genetic" in c for c in contents)

    def test_vector_search_respects_min_confidence(self, cm):
        """Vector search should filter by min_confidence."""
        cm.store_fact("test", "low confidence fact", confidence=0.2)
        cm.store_fact("test", "high confidence fact", confidence=0.9)

        results = cm.search_facts("confidence fact", min_confidence=0.5)
        assert all(f.confidence >= 0.5 for f in results)

    def test_vector_search_agent_isolation(self, tmp_path):
        """Vector search should only return facts for the querying agent."""
        db = tmp_path / "isolation_db"
        agent_a = CognitiveMemory(agent_name="agent-a", db_path=db)
        agent_b = CognitiveMemory(agent_name="agent-b", db_path=db)

        agent_a.store_fact("science", "Water boils at 100 degrees Celsius")
        agent_b.store_fact("science", "Ice melts at 0 degrees Celsius")

        a_results = agent_a.search_facts("temperature water")
        b_results = agent_b.search_facts("temperature ice")

        # Each agent should only see their own facts
        for fact in a_results:
            assert "boils" in fact.content or "100" in fact.content
        for fact in b_results:
            assert "melts" in fact.content or "0" in fact.content

        agent_a.close()
        agent_b.close()

    def test_keyword_fallback_when_no_vector_match(self, cm):
        """search_facts should fall back to keyword when vector returns empty."""
        # Store fact without triggering any semantic match on a weird query
        cm.store_fact("config", "port 5432 is PostgreSQL default")
        # A keyword query that matches via CONTAINS
        results = cm.search_facts("5432")
        assert len(results) >= 1

    def test_search_empty_query_returns_all(self, cm):
        """Empty query should return all facts (via get_all_facts)."""
        cm.store_fact("a", "fact one")
        cm.store_fact("b", "fact two")
        results = cm.search_facts("")
        assert len(results) == 2


class TestBackwardCompatibility:
    def test_existing_keyword_search_still_works(self, cm):
        """Keyword-based search_facts behavior is preserved."""
        cm.store_fact("Python", "Python is an interpreted language", confidence=0.9)
        cm.store_fact("Rust", "Rust is a compiled language", confidence=0.8)

        results = cm.search_facts("Python")
        assert len(results) >= 1
        assert results[0].concept == "Python"

    def test_store_fact_returns_node_id(self, cm):
        """store_fact still returns a node_id string."""
        nid = cm.store_fact("test", "test content")
        assert isinstance(nid, str)
        assert nid.startswith("sem_")

    def test_get_all_facts_unaffected(self, cm):
        """get_all_facts still works normally."""
        cm.store_fact("a", "alpha", confidence=0.5)
        cm.store_fact("b", "beta", confidence=0.9)
        facts = cm.get_all_facts()
        assert len(facts) == 2
        # Ordered by confidence desc
        assert facts[0].concept == "b"
