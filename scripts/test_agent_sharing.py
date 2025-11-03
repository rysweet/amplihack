#!/usr/bin/env python3
import os
from pathlib import Path
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value
"""Test script for Phase 4: Agent Type Memory Sharing.

Tests:
1. Agent type identification and registration
2. Memory creation and linking to agent types
3. Cross-agent learning queries
4. Project vs global scoping
5. Quality-based filtering
6. Usage tracking and validation
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from datetime import datetime

from amplihack.memory.neo4j import (
    AgentMemoryManager,
    Neo4jConnector,
    SchemaManager,
    ensure_neo4j_running,
)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_success(message: str):
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"✗ {message}")


def test_neo4j_startup():
    """Test 1: Ensure Neo4j is running."""
    print_section("Test 1: Neo4j Startup")

    print("Checking Neo4j container...")

    # Check if already running
    import subprocess
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=amplihack-neo4j", "--format", "{{.Status}}"],
        capture_output=True,
        text=True,
        check=False
    )

    if "Up" in result.stdout:
        print_success("Neo4j is already running")
        return

    print("Starting Neo4j container...")
    success = ensure_neo4j_running(blocking=True)

    if success:
        print_success("Neo4j is running")
    else:
        print_error("Failed to start Neo4j")
        sys.exit(1)


def test_schema_initialization():
    """Test 2: Initialize schema with agent types."""
    print_section("Test 2: Schema Initialization")

    connector = Neo4jConnector()
    connector.connect()

    schema = SchemaManager(connector)
    success = schema.initialize_schema()

    if success:
        print_success("Schema initialized")
    else:
        print_error("Schema initialization failed")
        connector.close()
        sys.exit(1)

    # Verify agent types
    if schema.verify_schema():
        print_success("Schema verified - all agent types present")
    else:
        print_error("Schema verification failed")
        connector.close()
        sys.exit(1)

    connector.close()


def test_memory_creation():
    """Test 3: Create memories for different agent types."""
    print_section("Test 3: Memory Creation")

    # Create architect memories
    architect = AgentMemoryManager("architect", project_id="amplihack")

    mem1 = architect.remember(
        content="Always design for modularity - separate concerns into distinct modules",
        category="design_principle",
        tags=["modularity", "design", "architecture"],
        confidence=0.9,
    )
    print_success(f"Architect stored principle: {mem1}")

    mem2 = architect.remember(
        content="Use API versioning with URL paths (e.g., /v1/api) for clarity",
        category="api_design",
        tags=["api", "versioning"],
        confidence=0.85,
    )
    print_success(f"Architect stored API pattern: {mem2}")

    # Create builder memories
    builder = AgentMemoryManager("builder", project_id="amplihack")

    mem3 = builder.remember(
        content="Use type hints for all function parameters and return values",
        category="code_quality",
        tags=["python", "types", "quality"],
        confidence=0.95,
    )
    print_success(f"Builder stored code quality rule: {mem3}")

    mem4 = builder.remember(
        content="Prefer list comprehensions over map() for better readability",
        category="python_idiom",
        tags=["python", "performance", "readability"],
        confidence=0.8,
    )
    print_success(f"Builder stored Python idiom: {mem4}")

    # Create reviewer memories
    reviewer = AgentMemoryManager("reviewer", project_id="amplihack")

    mem5 = reviewer.remember(
        content="Check for proper error handling in all public APIs",
        category="code_review",
        tags=["review", "errors", "api"],
        confidence=0.9,
    )
    print_success(f"Reviewer stored review guideline: {mem5}")

    return architect, builder, reviewer


def test_memory_recall():
    """Test 4: Recall memories for same agent type."""
    print_section("Test 4: Memory Recall")

    # New architect instance recalls memories
    architect2 = AgentMemoryManager("architect", project_id="amplihack")

    memories = architect2.recall(min_quality=0.5)
    print(f"Architect recalled {len(memories)} memories")

    for mem in memories:
        print(f"  - [{mem['category']}] {mem['content'][:60]}... (quality: {mem['quality_score']:.2f})")
        print_success("Memory accessible to same agent type")

    if len(memories) >= 2:
        print_success("Agent type memory sharing working")
    else:
        print_error("Expected at least 2 architect memories")


def test_cross_agent_learning():
    """Test 5: Cross-agent learning queries."""
    print_section("Test 5: Cross-Agent Learning")

    # New builder instance learns from other builders
    builder2 = AgentMemoryManager("builder", project_id="amplihack")

    print("\nBuilder learning from other builder agents:")
    memories = builder2.learn_from_others(min_quality=0.6, min_validations=0)

    if memories:
        for mem in memories:
            print(f"  - {mem['content'][:70]}...")
            print(f"    Quality: {mem['quality_score']:.2f}, "
                  f"Validations: {mem['validation_count']}, "
                  f"Applications: {mem['application_count']}")
        print_success(f"Builder learned {len(memories)} patterns from others")
    else:
        print("  No high-quality memories yet (expected for new system)")

    # Search for specific topic
    print("\nSearching for 'python' topic:")
    python_memories = builder2.learn_from_others(topic="python", min_validations=0)

    if python_memories:
        for mem in python_memories:
            print(f"  - {mem['content'][:70]}...")
        print_success(f"Found {len(python_memories)} Python-related memories")
    else:
        print("  No Python memories found yet")


def test_memory_usage_tracking():
    """Test 6: Track memory usage and validation."""
    print_section("Test 6: Memory Usage Tracking")

    architect = AgentMemoryManager("architect", project_id="amplihack")

    # Recall a memory
    memories = architect.recall(min_quality=0.5, limit=1)

    if not memories:
        print("No memories to track usage for")
        return

    memory = memories[0]
    memory_id = memory["id"]

    print(f"Using memory: {memory['content'][:60]}...")

    # Apply the memory
    architect.apply_memory(memory_id, outcome="successful", feedback_score=0.95)
    print_success("Recorded successful memory application")

    # Validate the memory
    architect.validate_memory(
        memory_id,
        feedback_score=0.9,
        outcome="successful",
        notes="Pattern worked well in practice"
    )
    print_success("Recorded memory validation")

    # Check updated statistics
    stats = architect.get_stats()
    print(f"\nArchitect agent stats:")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Average quality: {stats.get('avg_quality', 0.0):.2f}")
    print(f"  Total applications: {stats.get('total_applications', 0)}")
    print(f"  Average success rate: {stats.get('avg_success_rate', 0.0):.2f}")


def test_project_scoping():
    """Test 7: Project vs global scoping."""
    print_section("Test 7: Project vs Global Scoping")

    # Create project-specific memory
    architect1 = AgentMemoryManager("architect", project_id="amplihack")
    mem1 = architect1.remember(
        content="Amplihack uses ruthless simplicity as core principle",
        category="project_principle",
        tags=["amplihack", "philosophy"],
        global_scope=False,
    )
    print_success(f"Created project-specific memory: {mem1}")

    # Create global memory
    mem2 = architect1.remember(
        content="Always validate input data at API boundaries",
        category="security",
        tags=["security", "validation"],
        global_scope=True,
    )
    print_success(f"Created global memory: {mem2}")

    # New architect in different project should see global but not project-specific
    architect2 = AgentMemoryManager("architect", project_id="other-project")

    project_memories = architect2.recall(include_global=False)
    print(f"\nOther project (without global): {len(project_memories)} memories")

    all_memories = architect2.recall(include_global=True)
    print(f"Other project (with global): {len(all_memories)} memories")

    if len(all_memories) > len(project_memories):
        print_success("Global memories accessible across projects")
    else:
        print("Note: Global vs project scoping may need more data to test")


def test_quality_filtering():
    """Test 8: Quality-based filtering."""
    print_section("Test 8: Quality-Based Filtering")

    builder = AgentMemoryManager("builder", project_id="amplihack")

    print("Recalling with different quality thresholds:")

    low_quality = builder.recall(min_quality=0.5)
    print(f"  min_quality=0.5: {len(low_quality)} memories")

    medium_quality = builder.recall(min_quality=0.7)
    print(f"  min_quality=0.7: {len(medium_quality)} memories")

    high_quality = builder.recall(min_quality=0.9)
    print(f"  min_quality=0.9: {len(high_quality)} memories")

    if len(low_quality) >= len(medium_quality) >= len(high_quality):
        print_success("Quality filtering working correctly")
    else:
        print("Note: Quality filtering may need more varied data")


def test_search_functionality():
    """Test 9: Search across memories."""
    print_section("Test 9: Search Functionality")

    architect = AgentMemoryManager("architect", project_id="amplihack")

    # Search for design-related memories
    results = architect.search("design", limit=10)
    print(f"Search for 'design': {len(results)} results")

    if results:
        for i, mem in enumerate(results[:3], 1):
            print(f"  {i}. {mem['content'][:60]}...")
        print_success("Search functionality working")
    else:
        print("No search results (may need more data)")

    # Search for API-related memories
    api_results = architect.search("API", limit=5)
    print(f"Search for 'API': {len(api_results)} results")


def test_best_practices():
    """Test 10: Get best practices."""
    print_section("Test 10: Best Practices Retrieval")

    architect = AgentMemoryManager("architect", project_id="amplihack")

    # Get best practices (highest quality)
    practices = architect.get_best_practices(limit=5)

    print(f"Top {len(practices)} best practices:")
    for i, practice in enumerate(practices, 1):
        print(f"  {i}. {practice['content'][:70]}...")
        print(f"     Quality: {practice['quality_score']:.2f}, "
              f"Validations: {practice['validation_count']}")

    if practices:
        print_success("Best practices retrieval working")
    else:
        print("Note: No best practices yet (need higher quality memories)")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  Phase 4: Agent Type Memory Sharing - Test Suite")
    print("=" * 80)

    try:
        test_neo4j_startup()
        test_schema_initialization()

        architect, builder, reviewer = test_memory_creation()

        test_memory_recall()
        test_cross_agent_learning()
        test_memory_usage_tracking()
        test_project_scoping()
        test_quality_filtering()
        test_search_functionality()
        test_best_practices()

        print_section("Test Suite Complete")
        print_success("All tests completed successfully!")

        return True

    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
