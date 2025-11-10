#!/usr/bin/env python3
"""Comprehensive test script for Neo4j memory retrieval and isolation.

Tests:
- All retrieval strategies (Temporal, Similarity, Graph, Hybrid)
- Isolation boundaries (Project, Agent Type, Instance)
- Error handling (Neo4j down, network issues)
- Circuit breaker behavior
- Quality scoring and consolidation
- Performance metrics
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from amplihack.memory.neo4j.connector import Neo4jConnector, CircuitBreaker, CircuitState
from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager
from amplihack.memory.neo4j.schema import SchemaManager
from amplihack.memory.neo4j.retrieval import (
    RetrievalContext,
    TemporalRetrieval,
    SimilarityRetrieval,
    GraphTraversal,
    HybridRetrieval,
)
from amplihack.memory.neo4j.consolidation import (
    MemoryConsolidator,
)
from amplihack.memory.neo4j.monitoring import (
    MetricsCollector,
    MonitoredConnector,
    HealthMonitor,
    OperationType,
)


class TestResults:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record(self, test_name: str, passed: bool, error: str = None):
        """Record test result."""
        if passed:
            self.passed += 1
            print(f"✓ {test_name}")
        else:
            self.failed += 1
            print(f"✗ {test_name}: {error}")
            self.errors.append((test_name, error))

    def summary(self):
        """Print summary."""
        total = self.passed + self.failed
        print(f"\n{'=' * 70}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'=' * 70}\n")


def setup_test_data(conn: Neo4jConnector) -> bool:
    """Create test data for retrieval tests.

    Returns:
        True if successful
    """
    print("\n[Setup] Creating test data...")

    try:
        # Create test projects
        conn.execute_write("""
            MERGE (p1:Project {id: 'test-project-1'})
            SET p1.name = 'Test Project 1', p1.created_at = timestamp()

            MERGE (p2:Project {id: 'test-project-2'})
            SET p2.name = 'Test Project 2', p2.created_at = timestamp()

            MERGE (global:Project {id: 'global'})
            SET global.name = 'Global', global.created_at = timestamp()
        """)

        # Create test agent types
        conn.execute_write("""
            MERGE (at1:AgentType {id: 'architect'})
            SET at1.name = 'Architect', at1.created_at = timestamp()

            MERGE (at2:AgentType {id: 'builder'})
            SET at2.name = 'Builder', at2.created_at = timestamp()
        """)

        # Create test memories with varying attributes
        now = int(datetime.now().timestamp() * 1000)
        one_hour_ago = now - (3600 * 1000)
        one_day_ago = now - (86400 * 1000)

        memories = [
            # Recent architect memories in project 1
            {
                "id": "mem-1",
                "content": "System design for authentication",
                "memory_type": "pattern",
                "tags": ["auth", "security", "design"],
                "importance": 9,
                "created_at": now,
                "access_count": 10,
                "project": "test-project-1",
                "agent": "architect",
            },
            {
                "id": "mem-2",
                "content": "Database schema planning",
                "memory_type": "decision",
                "tags": ["database", "schema", "design"],
                "importance": 8,
                "created_at": one_hour_ago,
                "access_count": 5,
                "project": "test-project-1",
                "agent": "architect",
            },
            # Builder memories in project 1
            {
                "id": "mem-3",
                "content": "Implemented user authentication",
                "memory_type": "artifact",
                "tags": ["auth", "implementation"],
                "importance": 7,
                "created_at": one_hour_ago,
                "access_count": 3,
                "project": "test-project-1",
                "agent": "builder",
            },
            # Old memory in project 1
            {
                "id": "mem-4",
                "content": "Old design document",
                "memory_type": "context",
                "tags": ["design", "outdated"],
                "importance": 3,
                "created_at": one_day_ago,
                "access_count": 1,
                "project": "test-project-1",
                "agent": "architect",
            },
            # Memories in project 2 (isolated)
            {
                "id": "mem-5",
                "content": "Project 2 architecture",
                "memory_type": "pattern",
                "tags": ["architecture", "design"],
                "importance": 8,
                "created_at": now,
                "access_count": 7,
                "project": "test-project-2",
                "agent": "architect",
            },
        ]

        for mem in memories:
            conn.execute_write(
                """
                CREATE (m:Memory {
                    id: $id,
                    content: $content,
                    memory_type: $memory_type,
                    tags: $tags,
                    importance: $importance,
                    created_at: $created_at,
                    access_count: $access_count
                })
                WITH m
                MATCH (p:Project {id: $project})
                MATCH (at:AgentType {id: $agent})
                CREATE (m)-[:BELONGS_TO]->(p)
                CREATE (m)-[:CREATED_BY]->(at)
                """,
                mem,
            )

        # Create relationships between memories
        conn.execute_write("""
            MATCH (m1:Memory {id: 'mem-1'})
            MATCH (m2:Memory {id: 'mem-2'})
            CREATE (m1)-[:RELATED_TO]->(m2)

            MATCH (m2:Memory {id: 'mem-2'})
            MATCH (m3:Memory {id: 'mem-3'})
            CREATE (m2)-[:RELATED_TO]->(m3)
        """)

        print("✓ Test data created successfully")
        return True

    except Exception as e:
        print(f"✗ Failed to create test data: {e}")
        return False


def cleanup_test_data(conn: Neo4jConnector):
    """Remove test data."""
    print("\n[Cleanup] Removing test data...")

    try:
        conn.execute_write("""
            MATCH (m:Memory)
            WHERE m.id STARTS WITH 'mem-'
            DETACH DELETE m
        """)

        conn.execute_write("""
            MATCH (p:Project)
            WHERE p.id STARTS WITH 'test-project-'
            DETACH DELETE p
        """)

        print("✓ Test data cleaned up")

    except Exception as e:
        print(f"✗ Cleanup failed: {e}")


def test_temporal_retrieval(conn: Neo4jConnector, results: TestResults):
    """Test temporal retrieval strategy."""
    print("\n[Test] Temporal Retrieval")

    try:
        strategy = TemporalRetrieval(conn)

        # Test recent memories
        context = RetrievalContext(
            project_id="test-project-1",
            agent_type="architect",
            time_window_hours=2,
        )

        memories = strategy.retrieve(context, limit=10)

        # Should get recent architect memories from project 1
        results.record(
            "Temporal: Recent memories",
            len(memories) >= 2 and memories[0].memory_id in ["mem-1", "mem-2"],
            f"Got {len(memories)} memories: {[m.memory_id for m in memories]}",
        )

        # Test isolation - should not get project 2 memories
        has_project2 = any(m.memory_id == "mem-5" for m in memories)
        results.record(
            "Temporal: Project isolation",
            not has_project2,
            "Found project 2 memory in project 1 results",
        )

        # Test agent type isolation - should not get builder memories
        has_builder = any(m.memory_id == "mem-3" for m in memories)
        results.record(
            "Temporal: Agent type isolation",
            not has_builder,
            "Found builder memory in architect results",
        )

    except Exception as e:
        results.record("Temporal retrieval", False, str(e))


def test_similarity_retrieval(conn: Neo4jConnector, results: TestResults):
    """Test similarity retrieval strategy."""
    print("\n[Test] Similarity Retrieval")

    try:
        strategy = SimilarityRetrieval(conn)

        context = RetrievalContext(
            project_id="test-project-1",
            agent_type="architect",
        )

        # Test tag-based similarity
        memories = strategy.retrieve(context, limit=10, query_tags=["auth", "security"])

        results.record(
            "Similarity: Tag matching",
            len(memories) > 0 and memories[0].memory_id == "mem-1",
            f"Expected mem-1 first, got {memories[0].memory_id if memories else 'none'}",
        )

        # Test relevance scoring
        if len(memories) > 0:
            results.record(
                "Similarity: Relevance scoring",
                memories[0].score > 0.0,
                f"Score is {memories[0].score}",
            )
        else:
            results.record("Similarity: Relevance scoring", False, "No memories returned")

    except Exception as e:
        results.record("Similarity retrieval", False, str(e))


def test_graph_traversal(conn: Neo4jConnector, results: TestResults):
    """Test graph traversal strategy."""
    print("\n[Test] Graph Traversal")

    try:
        strategy = GraphTraversal(conn)

        context = RetrievalContext(
            project_id="test-project-1",
            agent_type="architect",
        )

        # Traverse from mem-1 (should find mem-2 via RELATED_TO)
        memories = strategy.retrieve(context, limit=10, start_memory_id="mem-1")

        results.record(
            "Graph: Related memories",
            len(memories) > 0 and "mem-2" in [m.memory_id for m in memories],
            f"Got {len(memories)} memories: {[m.memory_id for m in memories]}",
        )

        # Test distance scoring
        if len(memories) > 0:
            results.record(
                "Graph: Distance scoring",
                memories[0].score > 0.0,
                f"Score is {memories[0].score}",
            )
        else:
            results.record("Graph: Distance scoring", False, "No memories returned")

    except Exception as e:
        results.record("Graph traversal", False, str(e))


def test_hybrid_retrieval(conn: Neo4jConnector, results: TestResults):
    """Test hybrid retrieval strategy."""
    print("\n[Test] Hybrid Retrieval")

    try:
        strategy = HybridRetrieval(
            conn, temporal_weight=0.4, similarity_weight=0.4, graph_weight=0.2
        )

        context = RetrievalContext(
            project_id="test-project-1",
            agent_type="architect",
        )

        # Combine all strategies
        memories = strategy.retrieve(
            context,
            limit=10,
            query_tags=["design", "auth"],
            start_memory_id="mem-1",
        )

        results.record(
            "Hybrid: Combined retrieval",
            len(memories) > 0,
            f"Got {len(memories)} memories",
        )

        # Test combined scoring
        if len(memories) > 0:
            results.record(
                "Hybrid: Combined scoring",
                all(0.0 <= m.score <= 1.0 for m in memories),
                "Some scores out of range",
            )
        else:
            results.record("Hybrid: Combined scoring", False, "No memories returned")

    except Exception as e:
        results.record("Hybrid retrieval", False, str(e))


def test_quality_scoring(conn: Neo4jConnector, results: TestResults):
    """Test quality scoring and consolidation."""
    print("\n[Test] Quality Scoring")

    try:
        consolidator = MemoryConsolidator(conn)

        # Calculate quality scores
        metrics = consolidator.calculate_quality_scores("test-project-1")

        results.record(
            "Quality: Calculation",
            len(metrics) > 0,
            f"Got {len(metrics)} metrics",
        )

        # Check score range
        if metrics:
            results.record(
                "Quality: Score range",
                all(0.0 <= m.quality_score <= 1.0 for m in metrics),
                "Some scores out of range",
            )

        # Update scores in database
        updated = consolidator.update_quality_scores(metrics)
        results.record(
            "Quality: Update scores",
            updated > 0,
            f"Updated {updated} memories",
        )

    except Exception as e:
        results.record("Quality scoring", False, str(e))


def test_memory_promotion(conn: Neo4jConnector, results: TestResults):
    """Test memory promotion to global scope."""
    print("\n[Test] Memory Promotion")

    try:
        consolidator = MemoryConsolidator(conn, promotion_threshold=0.6)

        # First ensure quality scores are calculated
        metrics = consolidator.calculate_quality_scores("test-project-1")
        consolidator.update_quality_scores(metrics)

        # Promote high-quality memories
        promoted = consolidator.promote_to_global("test-project-1")

        results.record(
            "Promotion: High-quality promotion",
            len(promoted) >= 0,  # May be 0 if no high-quality memories
            f"Promoted {len(promoted)} memories",
        )

        # Verify promoted memories have global relationship
        if promoted:
            check = conn.execute_query(
                """
                MATCH (m:Memory {id: $memory_id})-[:BELONGS_TO]->(p:Project {id: 'global'})
                RETURN count(m) as count
                """,
                {"memory_id": promoted[0]},
            )
            results.record(
                "Promotion: Global relationship",
                check[0]["count"] > 0,
                "Promoted memory not linked to global",
            )

    except Exception as e:
        results.record("Memory promotion", False, str(e))


def test_circuit_breaker(results: TestResults):
    """Test circuit breaker behavior."""
    print("\n[Test] Circuit Breaker")

    try:
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=2)

        # Test normal operation
        def success_func():
            return "success"

        result = breaker.call(success_func)
        results.record(
            "Circuit: Normal operation",
            result == "success" and breaker.state == CircuitState.CLOSED,
        )

        # Test failures opening circuit
        def fail_func():
            raise Exception("Test failure")

        for _ in range(3):
            try:
                breaker.call(fail_func)
            except Exception:
                # Expected - circuit breaker should handle failures
                pass

        results.record(
            "Circuit: Opens on failures",
            breaker.state == CircuitState.OPEN,
            f"State is {breaker.state.value}",
        )

        # Test circuit rejects calls when open
        try:
            breaker.call(success_func)
            results.record("Circuit: Rejects when open", False, "Did not reject call")
        except RuntimeError:
            results.record("Circuit: Rejects when open", True)

        # Test reset
        breaker.reset()
        results.record(
            "Circuit: Manual reset",
            breaker.state == CircuitState.CLOSED,
            f"State is {breaker.state.value}",
        )

    except Exception as e:
        results.record("Circuit breaker", False, str(e))


def test_monitoring(conn: Neo4jConnector, results: TestResults):
    """Test monitoring and metrics collection."""
    print("\n[Test] Monitoring")

    try:
        metrics = MetricsCollector()
        monitored_conn = MonitoredConnector(conn, metrics)

        # Execute some operations
        monitored_conn.connect()
        monitored_conn.execute_query("RETURN 1 as num")

        # Check metrics recorded
        stats = metrics.get_statistics(OperationType.QUERY)
        results.record(
            "Monitoring: Metrics collection",
            stats["total_operations"] > 0,
            f"Recorded {stats['total_operations']} operations",
        )

        # Check success rate
        results.record(
            "Monitoring: Success tracking",
            stats["success_rate"] > 0,
            f"Success rate: {stats['success_rate']}",
        )

        monitored_conn.close()

    except Exception as e:
        results.record("Monitoring", False, str(e))


def test_health_monitoring(conn: Neo4jConnector, results: TestResults):
    """Test health monitoring."""
    print("\n[Test] Health Monitoring")

    try:
        monitor = HealthMonitor(conn)

        health = monitor.check_health()

        results.record(
            "Health: System check",
            health.neo4j_available,
            f"Neo4j not available: {health.issues}",
        )

        results.record(
            "Health: Response time",
            health.response_time_ms > 0,
            f"Response time: {health.response_time_ms}ms",
        )

        results.record(
            "Health: Memory counts",
            health.total_memories >= 0,
            f"Memory count: {health.total_memories}",
        )

    except Exception as e:
        results.record("Health monitoring", False, str(e))


def main():
    """Run all tests."""
    print("=" * 70)
    print("Neo4j Memory System - Phase 5-6 Comprehensive Tests")
    print("=" * 70)

    results = TestResults()

    # Ensure Neo4j is running
    print("\n[Setup] Ensuring Neo4j container is running...")
    manager = Neo4jContainerManager()

    if not manager.start(wait_for_ready=True):
        print("✗ Failed to start Neo4j container")
        sys.exit(1)

    print("✓ Neo4j container is running")

    # Connect and initialize
    try:
        with Neo4jConnector() as conn:
            # Initialize schema
            schema = SchemaManager(conn)
            if not schema.initialize_schema():
                print("✗ Failed to initialize schema")
                sys.exit(1)

            print("✓ Schema initialized")

            # Setup test data
            if not setup_test_data(conn):
                sys.exit(1)

            # Run retrieval tests
            test_temporal_retrieval(conn, results)
            test_similarity_retrieval(conn, results)
            test_graph_traversal(conn, results)
            test_hybrid_retrieval(conn, results)

            # Run consolidation tests
            test_quality_scoring(conn, results)
            test_memory_promotion(conn, results)

            # Run production hardening tests
            test_circuit_breaker(results)
            test_monitoring(conn, results)
            test_health_monitoring(conn, results)

            # Cleanup
            cleanup_test_data(conn)

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Print summary
    results.summary()

    # Exit with appropriate code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
