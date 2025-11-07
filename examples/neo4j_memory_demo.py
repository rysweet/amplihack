#!/usr/bin/env python3
"""Demo: Agent Type Memory Sharing with Neo4j

Demonstrates Phase 4 features:
- Memory storage and retrieval
- Cross-agent learning
- Project scoping
- Quality tracking
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from amplihack.memory.neo4j import AgentMemoryManager, ensure_neo4j_running


def demo_basic_usage():
    """Demo 1: Basic memory operations."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Memory Operations")
    print("=" * 70)

    # Initialize architect agent
    architect = AgentMemoryManager("architect", project_id="demo-project")
    print(f"✓ Initialized: {architect}")

    # Store some memories
    print("\nStoring design principles...")
    mem1 = architect.remember(
        content="Prefer composition over inheritance for flexibility",
        category="design_principle",
        tags=["design", "oop", "composition"],
        confidence=0.9,
    )
    print(f"  ✓ Stored: {mem1[:8]}...")

    mem2 = architect.remember(
        content="Keep modules loosely coupled with clear interfaces",
        category="design_principle",
        tags=["design", "modularity", "coupling"],
        confidence=0.85,
    )
    print(f"  ✓ Stored: {mem2[:8]}...")

    # Recall memories
    print("\nRecalling design principles...")
    memories = architect.recall(category="design_principle", min_quality=0.5)
    print(f"  Found {len(memories)} principles:")
    for i, mem in enumerate(memories, 1):
        print(f"    {i}. {mem['content']}")
        print(f"       Quality: {mem['quality_score']:.2f}")


def demo_cross_agent_learning():
    """Demo 2: Cross-agent learning."""
    print("\n" + "=" * 70)
    print("Demo 2: Cross-Agent Learning")
    print("=" * 70)

    # First builder agent stores some patterns
    builder1 = AgentMemoryManager("builder", project_id="demo-project")
    print(f"✓ Builder 1: {builder1.instance_id}")

    print("\nBuilder 1 storing code patterns...")
    builder1.remember(
        content="Use f-strings for string formatting (faster and cleaner)",
        category="python_idiom",
        tags=["python", "performance", "readability"],
        confidence=0.95,
    )
    builder1.remember(
        content="Use context managers for resource cleanup",
        category="python_idiom",
        tags=["python", "resources", "cleanup"],
        confidence=0.9,
    )
    print("  ✓ Stored 2 Python idioms")

    # Second builder agent learns from the first
    builder2 = AgentMemoryManager("builder", project_id="demo-project")
    print(f"\n✓ Builder 2: {builder2.instance_id}")

    print("\nBuilder 2 learning from other builders...")
    patterns = builder2.learn_from_others(topic="python", min_quality=0.6, min_validations=0)
    print(f"  Found {len(patterns)} patterns:")
    for i, pattern in enumerate(patterns, 1):
        print(f"    {i}. {pattern['content']}")

    # Apply a pattern
    if patterns:
        print("\nBuilder 2 applying learned pattern...")
        mem_id = patterns[0]["id"]
        builder2.apply_memory(mem_id, outcome="successful", feedback_score=0.95)
        print("  ✓ Pattern applied successfully")

        # Validate it
        builder2.validate_memory(
            mem_id, feedback_score=0.9, notes="Pattern worked great in production code"
        )
        print("  ✓ Pattern validated")


def demo_project_scoping():
    """Demo 3: Project vs global scoping."""
    print("\n" + "=" * 70)
    print("Demo 3: Project vs Global Scoping")
    print("=" * 70)

    # Architect in project A
    arch_a = AgentMemoryManager("architect", project_id="project-a")
    print(f"✓ Architect in Project A: {arch_a.instance_id}")

    # Store project-specific memory
    print("\nStoring project-specific memory...")
    arch_a.remember(
        content="Project A uses microservices architecture",
        category="architecture_decision",
        tags=["microservices", "project-a"],
        global_scope=False,
    )
    print("  ✓ Stored (project-specific)")

    # Store global memory
    print("\nStoring global memory...")
    arch_a.remember(
        content="Always log errors with stack traces for debugging",
        category="best_practice",
        tags=["logging", "errors", "debugging"],
        global_scope=True,
    )
    print("  ✓ Stored (global)")

    # Architect in project B
    arch_b = AgentMemoryManager("architect", project_id="project-b")
    print(f"\n✓ Architect in Project B: {arch_b.instance_id}")

    # Check what's visible
    print("\nProject B viewing memories...")
    project_only = arch_b.recall(include_global=False)
    print(f"  Project-only: {len(project_only)} memories")

    with_global = arch_b.recall(include_global=True)
    print(f"  With global: {len(with_global)} memories")

    if len(with_global) > len(project_only):
        print("  ✓ Global memories accessible across projects!")


def demo_quality_tracking():
    """Demo 4: Quality tracking and best practices."""
    print("\n" + "=" * 70)
    print("Demo 4: Quality Tracking & Best Practices")
    print("=" * 70)

    # Security agent
    security = AgentMemoryManager("security", project_id="demo-project")
    print(f"✓ Security Agent: {security.instance_id}")

    # Store security patterns with varying confidence
    print("\nStoring security patterns...")
    patterns = [
        ("Always sanitize user input before database queries", 0.95),
        ("Use parameterized queries to prevent SQL injection", 0.98),
        ("Implement rate limiting on public APIs", 0.85),
        ("Hash passwords with bcrypt or argon2", 0.92),
    ]

    for content, confidence in patterns:
        security.remember(
            content=content, category="security_practice", tags=["security"], confidence=confidence
        )
    print(f"  ✓ Stored {len(patterns)} patterns")

    # Get best practices
    print("\nRetrieving best practices...")
    best = security.get_best_practices(category="security_practice", limit=3)
    print(f"  Top {len(best)} practices:")
    for i, practice in enumerate(best, 1):
        print(f"    {i}. {practice['content']}")
        print(f"       Quality: {practice['quality_score']:.2f}")

    # Get statistics
    print("\nSecurity agent statistics:")
    stats = security.get_stats()
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Average quality: {stats.get('avg_quality', 0):.2f}")


def demo_search():
    """Demo 5: Search functionality."""
    print("\n" + "=" * 70)
    print("Demo 5: Search Functionality")
    print("=" * 70)

    # Optimizer agent
    optimizer = AgentMemoryManager("optimizer", project_id="demo-project")
    print(f"✓ Optimizer Agent: {optimizer.instance_id}")

    # Store optimization tips
    print("\nStoring optimization tips...")
    tips = [
        "Use database indexes for frequently queried columns",
        "Cache expensive computations with memoization",
        "Profile before optimizing - measure, don't guess",
        "Use connection pooling for database access",
    ]

    for tip in tips:
        optimizer.remember(
            content=tip,
            category="optimization_tip",
            tags=["performance", "optimization"],
            confidence=0.85,
        )
    print(f"  ✓ Stored {len(tips)} tips")

    # Search for specific topics
    print("\nSearching for 'database' optimization...")
    results = optimizer.search("database", limit=5)
    print(f"  Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"    {i}. {result['content']}")


def main():
    """Run all demos."""
    print("=" * 70)
    print("  Neo4j Agent Memory Sharing - Demo")
    print("=" * 70)

    # Ensure Neo4j is running
    print("\nChecking Neo4j...")
    if not ensure_neo4j_running(blocking=True):
        print("✗ Failed to start Neo4j")
        sys.exit(1)
    print("✓ Neo4j is running")

    try:
        # Run demos
        demo_basic_usage()
        demo_cross_agent_learning()
        demo_project_scoping()
        demo_quality_tracking()
        demo_search()

        print("\n" + "=" * 70)
        print("  All Demos Complete!")
        print("=" * 70)
        print("\nKey takeaways:")
        print("  1. Agents of same type share memories automatically")
        print("  2. Cross-agent learning enables knowledge transfer")
        print("  3. Project scoping controls memory visibility")
        print("  4. Quality tracking identifies best practices")
        print("  5. Search makes memories discoverable")

    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
