#!/usr/bin/env python3
import os
from pathlib import Path

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value
"""Simplified test script for Phase 5-6 features.

Assumes Neo4j is already running (via existing container).
Tests retrieval, consolidation, and monitoring features.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from amplihack.memory.neo4j.connector import Neo4jConnector, CircuitBreaker, CircuitState
from amplihack.memory.neo4j.schema import SchemaManager
from amplihack.memory.neo4j.retrieval import (
    RetrievalContext,
    TemporalRetrieval,
    SimilarityRetrieval,
    GraphTraversal,
    HybridRetrieval,
)
from amplihack.memory.neo4j.consolidation import MemoryConsolidator
from amplihack.memory.neo4j.monitoring import (
    MetricsCollector,
    MonitoredConnector,
    HealthMonitor,
    OperationType,
)


def test_connection():
    """Test basic connection."""
    print("\n[Test] Connection")
    try:
        with Neo4jConnector() as conn:
            result = conn.execute_query("RETURN 1 as num")
            assert result[0]["num"] == 1
            print("✓ Connection successful")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_circuit_breaker():
    """Test circuit breaker."""
    print("\n[Test] Circuit Breaker")
    try:
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=2)

        # Normal operation
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        print("✓ Normal operation works")

        # Test failures
        for _ in range(3):
            try:
                breaker.call(lambda: 1 / 0)
            except Exception:
                pass  # Expected - circuit breaker call fails

        assert breaker.state == CircuitState.OPEN
        print("✓ Circuit opens after failures")

        # Test rejection
        try:
            breaker.call(lambda: "test")
            print("✗ Should have rejected call")
            return False
        except RuntimeError:
            print("✓ Rejects calls when open")

        # Test reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        print("✓ Reset works")

        return True
    except Exception as e:
        print(f"✗ Circuit breaker test failed: {e}")
        return False


def test_monitoring():
    """Test monitoring."""
    print("\n[Test] Monitoring")
    try:
        with Neo4jConnector() as conn:
            metrics = MetricsCollector()
            monitored = MonitoredConnector(conn, metrics)

            # Execute query
            monitored.execute_query("RETURN 1 as num")

            # Check metrics
            stats = metrics.get_statistics(OperationType.QUERY)
            assert stats["total_operations"] > 0
            print(f"✓ Recorded {stats['total_operations']} operations")

            assert stats["success_rate"] > 0
            print(f"✓ Success rate: {stats['success_rate']}")

            return True
    except Exception as e:
        print(f"✗ Monitoring test failed: {e}")
        return False


def test_health_check():
    """Test health monitoring."""
    print("\n[Test] Health Monitoring")
    try:
        with Neo4jConnector() as conn:
            monitor = HealthMonitor(conn)
            health = monitor.check_health()

            assert health.neo4j_available
            print("✓ Neo4j available")

            assert health.response_time_ms > 0
            print(f"✓ Response time: {health.response_time_ms:.2f}ms")

            print(
                f"✓ Memories: {health.total_memories}, Projects: {health.total_projects}, Agents: {health.total_agents}"
            )

            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def setup_test_data(conn):
    """Create minimal test data."""
    print("\n[Setup] Creating test data...")
    try:
        # Create test project and agent
        conn.execute_write("""
            MERGE (p:Project {id: 'test-proj'})
            SET p.name = 'Test Project', p.created_at = timestamp()

            MERGE (at:AgentType {id: 'architect'})
            SET at.name = 'Architect', at.created_at = timestamp()
        """)

        # Create test memories
        now = int(datetime.now().timestamp() * 1000)
        conn.execute_write(
            """
            CREATE (m1:Memory {
                id: 'test-mem-1',
                content: 'Test memory 1',
                memory_type: 'pattern',
                tags: ['test', 'alpha'],
                importance: 8,
                created_at: $now,
                access_count: 5
            })
            CREATE (m2:Memory {
                id: 'test-mem-2',
                content: 'Test memory 2',
                memory_type: 'decision',
                tags: ['test', 'beta'],
                importance: 6,
                created_at: $now - 3600000,
                access_count: 3
            })
            WITH m1, m2
            MATCH (p:Project {id: 'test-proj'})
            MATCH (at:AgentType {id: 'architect'})
            CREATE (m1)-[:BELONGS_TO]->(p)
            CREATE (m1)-[:CREATED_BY]->(at)
            CREATE (m2)-[:BELONGS_TO]->(p)
            CREATE (m2)-[:CREATED_BY]->(at)
            CREATE (m1)-[:RELATED_TO]->(m2)
        """,
            {"now": now},
        )

        print("✓ Test data created")
        return True
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        return False


def cleanup_test_data(conn):
    """Remove test data."""
    print("\n[Cleanup] Removing test data...")
    try:
        conn.execute_write("""
            MATCH (m:Memory) WHERE m.id STARTS WITH 'test-mem-'
            DETACH DELETE m
        """)
        conn.execute_write("""
            MATCH (p:Project {id: 'test-proj'})
            DETACH DELETE p
        """)
        print("✓ Cleanup complete")
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")


def test_temporal_retrieval(conn):
    """Test temporal retrieval."""
    print("\n[Test] Temporal Retrieval")
    try:
        strategy = TemporalRetrieval(conn)
        context = RetrievalContext(
            project_id="test-proj",
            agent_type="architect",
            time_window_hours=24,
        )

        memories = strategy.retrieve(context, limit=10)
        assert len(memories) >= 1
        print(f"✓ Retrieved {len(memories)} memories")

        # Most recent first
        assert memories[0].memory_id == "test-mem-1"
        print("✓ Sorted by recency")

        return True
    except Exception as e:
        print(f"✗ Temporal retrieval failed: {e}")
        return False


def test_similarity_retrieval(conn):
    """Test similarity retrieval."""
    print("\n[Test] Similarity Retrieval")
    try:
        strategy = SimilarityRetrieval(conn)
        context = RetrievalContext(
            project_id="test-proj",
            agent_type="architect",
        )

        memories = strategy.retrieve(context, limit=10, query_tags=["test", "alpha"])
        assert len(memories) >= 1
        print(f"✓ Retrieved {len(memories)} similar memories")

        # Check scoring
        assert memories[0].score > 0.0
        print(f"✓ Relevance score: {memories[0].score:.2f}")

        return True
    except Exception as e:
        print(f"✗ Similarity retrieval failed: {e}")
        return False


def test_graph_traversal(conn):
    """Test graph traversal."""
    print("\n[Test] Graph Traversal")
    try:
        strategy = GraphTraversal(conn)
        context = RetrievalContext(
            project_id="test-proj",
            agent_type="architect",
        )

        memories = strategy.retrieve(context, limit=10, start_memory_id="test-mem-1")
        assert len(memories) >= 1
        print(f"✓ Traversed to {len(memories)} related memories")

        # Should find test-mem-2 via RELATED_TO
        memory_ids = [m.memory_id for m in memories]
        assert "test-mem-2" in memory_ids
        print("✓ Found related memory via relationship")

        return True
    except Exception as e:
        print(f"✗ Graph traversal failed: {e}")
        return False


def test_hybrid_retrieval(conn):
    """Test hybrid retrieval."""
    print("\n[Test] Hybrid Retrieval")
    try:
        strategy = HybridRetrieval(conn)
        context = RetrievalContext(
            project_id="test-proj",
            agent_type="architect",
        )

        memories = strategy.retrieve(
            context,
            limit=10,
            query_tags=["test"],
            start_memory_id="test-mem-1",
        )
        assert len(memories) >= 1
        print(f"✓ Hybrid retrieval found {len(memories)} memories")

        # Check combined scoring
        assert all(0.0 <= m.score <= 1.0 for m in memories)
        print("✓ Combined scoring in valid range")

        return True
    except Exception as e:
        print(f"✗ Hybrid retrieval failed: {e}")
        return False


def test_quality_scoring(conn):
    """Test quality scoring."""
    print("\n[Test] Quality Scoring")
    try:
        consolidator = MemoryConsolidator(conn)

        metrics = consolidator.calculate_quality_scores("test-proj")
        assert len(metrics) >= 1
        print(f"✓ Calculated scores for {len(metrics)} memories")

        # Check score range
        assert all(0.0 <= m.quality_score <= 1.0 for m in metrics)
        print("✓ Quality scores in valid range")

        # Update database
        updated = consolidator.update_quality_scores(metrics)
        assert updated >= 1
        print(f"✓ Updated {updated} quality scores")

        return True
    except Exception as e:
        print(f"✗ Quality scoring failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Neo4j Memory System - Phase 5-6 Simplified Tests")
    print("=" * 70)

    passed = 0
    total = 0

    # Infrastructure tests
    tests = [
        ("Connection", test_connection),
        ("Circuit Breaker", test_circuit_breaker),
        ("Monitoring", test_monitoring),
        ("Health Check", test_health_check),
    ]

    for name, test_func in tests:
        total += 1
        if test_func():
            passed += 1

    # Retrieval tests with data
    try:
        with Neo4jConnector() as conn:
            # Ensure schema
            schema = SchemaManager(conn)
            schema.initialize_schema()

            # Setup test data
            if setup_test_data(conn):
                retrieval_tests = [
                    ("Temporal Retrieval", lambda: test_temporal_retrieval(conn)),
                    ("Similarity Retrieval", lambda: test_similarity_retrieval(conn)),
                    ("Graph Traversal", lambda: test_graph_traversal(conn)),
                    ("Hybrid Retrieval", lambda: test_hybrid_retrieval(conn)),
                    ("Quality Scoring", lambda: test_quality_scoring(conn)),
                ]

                for name, test_func in retrieval_tests:
                    total += 1
                    if test_func():
                        passed += 1

                cleanup_test_data(conn)
            else:
                print("\n✗ Could not setup test data, skipping retrieval tests")

    except Exception as e:
        print(f"\n✗ Test suite error: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Test Results: {passed}/{total} passed")
    print(f"{'=' * 70}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
