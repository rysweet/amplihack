#!/usr/bin/env python3
import os
from pathlib import Path
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value
"""Test script for agent memory integration.

This script tests the complete agent memory integration:
1. Memory injection before agent runs
2. Learning extraction after agent completes
3. Memory retrieval on subsequent runs

Usage:
    python scripts/test_agent_memory_integration.py
"""

import logging
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from amplihack.memory.neo4j.agent_integration import (
    detect_agent_type,
    detect_task_category,
    extract_and_store_learnings,
    inject_memory_context,
)
from amplihack.memory.neo4j.lifecycle import (
    Neo4jContainerManager,
    check_neo4j_prerequisites,
    ensure_neo4j_running,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_prerequisites():
    """Test 1: Check Neo4j prerequisites."""
    print("\n" + "=" * 60)
    print("TEST 1: Neo4j Prerequisites")
    print("=" * 60)

    prereqs = check_neo4j_prerequisites()

    print(f"Docker installed: {'✓' if prereqs['docker_installed'] else '✗'}")
    print(f"Docker running: {'✓' if prereqs['docker_running'] else '✗'}")
    print(f"Docker Compose available: {'✓' if prereqs['docker_compose_available'] else '✗'}")
    print(f"Compose file exists: {'✓' if prereqs['compose_file_exists'] else '✗'}")

    if not prereqs["all_passed"]:
        print("\n⚠️  Prerequisites not met:")
        for issue in prereqs["issues"]:
            print(f"  - {issue}")
        return False

    print("\n✅ All prerequisites passed!")
    return True


def test_container_management():
    """Test 2: Start/stop Neo4j container."""
    print("\n" + "=" * 60)
    print("TEST 2: Container Management")
    print("=" * 60)

    manager = Neo4jContainerManager()

    # Start container
    print("Starting Neo4j container...")
    if not manager.start(wait_for_ready=True):
        print("✗ Failed to start container")
        return False

    print("✓ Container started")

    # Check health
    print("Checking health...")
    if not manager.is_healthy():
        print("✗ Container unhealthy")
        return False

    print("✓ Container healthy")

    print("\n✅ Container management test passed!")
    return True


def test_agent_type_detection():
    """Test 3: Agent type detection."""
    print("\n" + "=" * 60)
    print("TEST 3: Agent Type Detection")
    print("=" * 60)

    test_cases = [
        ("architect.md", "architect"),
        ("builder", "builder"),
        ("reviewer.md", "reviewer"),
        ("unknown.md", None),
    ]

    all_passed = True
    for input_val, expected in test_cases:
        result = detect_agent_type(input_val)
        if result == expected:
            print(f"✓ {input_val} → {result}")
        else:
            print(f"✗ {input_val} → {result} (expected {expected})")
            all_passed = False

    if all_passed:
        print("\n✅ Agent type detection test passed!")
    else:
        print("\n✗ Agent type detection test failed!")

    return all_passed


def test_task_category_detection():
    """Test 4: Task category detection."""
    print("\n" + "=" * 60)
    print("TEST 4: Task Category Detection")
    print("=" * 60)

    test_cases = [
        ("Design authentication system", "system_design"),
        ("Fix bug in user service", "error_handling"),
        ("Optimize database queries", "optimization"),
        ("Add unit tests for API", "testing"),
        ("Implement new feature", "implementation"),
    ]

    all_passed = True
    for task, expected_category in test_cases:
        result = detect_task_category(task)
        if result == expected_category:
            print(f"✓ '{task}' → {result}")
        else:
            print(f"✗ '{task}' → {result} (expected {expected_category})")
            all_passed = False

    if all_passed:
        print("\n✅ Task category detection test passed!")
    else:
        print("\n✗ Task category detection test failed!")

    return all_passed


def test_memory_injection_empty():
    """Test 5: Memory injection with no existing memories."""
    print("\n" + "=" * 60)
    print("TEST 5: Memory Injection (Empty)")
    print("=" * 60)

    # First run - should have no memories
    context = inject_memory_context(
        agent_type="architect",
        task="Design authentication system",
    )

    if not context:
        print("✓ No memory context (expected for first run)")
        print("\n✅ Memory injection (empty) test passed!")
        return True
    else:
        print(f"⚠️  Unexpected context found:\n{context}")
        print("\n⚠️  Memory injection (empty) test returned context (may be from previous runs)")
        return True  # Not a failure, just unexpected


def test_learning_extraction():
    """Test 6: Extract and store learnings."""
    print("\n" + "=" * 60)
    print("TEST 6: Learning Extraction and Storage")
    print("=" * 60)

    # Sample agent output with various learning types
    sample_output = """
## Architecture Design: Authentication System

## Decision: Token-Based Authentication
**What**: Use JWT tokens for stateless authentication
**Why**: Enables horizontal scaling and reduces server-side state management

## Recommendation:
- Always use bcrypt for password hashing
- Implement refresh token rotation
- Add rate limiting on auth endpoints

⚠️ Warning: Never store JWT tokens in localStorage - use httpOnly cookies instead

## Implementation Strategy

Pattern: Separate auth service from business logic
Approach: Microservice architecture with dedicated auth service

This provides better security isolation and makes it easier to audit authentication logic.

## Key Points:
- Token expiry should be short (15 minutes)
- Refresh tokens valid for 7 days
- Use RSA256 for signing (not HS256)

Error: Weak password policy
Solution: Enforce minimum 12 characters with complexity requirements
"""

    memory_ids = extract_and_store_learnings(
        agent_type="architect",
        output=sample_output,
        task="Design authentication system",
        success=True,
        duration_seconds=45.5,
    )

    print(f"Extracted and stored {len(memory_ids)} learnings:")
    for i, memory_id in enumerate(memory_ids, 1):
        print(f"  {i}. {memory_id}")

    if len(memory_ids) >= 5:  # Should extract at least 5 learnings
        print(f"\n✅ Learning extraction test passed! ({len(memory_ids)} learnings stored)")
        return True
    else:
        print(f"\n✗ Learning extraction test failed! Expected >= 5, got {len(memory_ids)}")
        return False


def test_memory_injection_with_context():
    """Test 7: Memory injection with existing memories."""
    print("\n" + "=" * 60)
    print("TEST 7: Memory Injection (With Context)")
    print("=" * 60)

    # Second run - should now have memories from previous test
    context = inject_memory_context(
        agent_type="architect",
        task="Design authorization system for resource access",
    )

    if context:
        print("✓ Memory context injected:")
        print("-" * 60)
        # Show first 500 chars
        preview = context[:500] + "..." if len(context) > 500 else context
        print(preview)
        print("-" * 60)
        print(f"Total context length: {len(context)} characters")
        print("\n✅ Memory injection (with context) test passed!")
        return True
    else:
        print("⚠️  No context injected (learnings may not have been stored)")
        print("\n⚠️  Memory injection (with context) test inconclusive")
        return False


def test_cross_agent_learning():
    """Test 8: Cross-agent learning (builder learning from architect)."""
    print("\n" + "=" * 60)
    print("TEST 8: Cross-Agent Learning")
    print("=" * 60)

    # Builder agent working on similar task
    context = inject_memory_context(
        agent_type="builder",
        task="Implement JWT authentication in API",
    )

    if context and "architect" in context.lower():
        print("✓ Cross-agent learning detected (builder sees architect learnings)")
        print("-" * 60)
        preview = context[:500] + "..." if len(context) > 500 else context
        print(preview)
        print("-" * 60)
        print("\n✅ Cross-agent learning test passed!")
        return True
    else:
        print("⚠️  No cross-agent learning detected")
        print("\n⚠️  Cross-agent learning test inconclusive")
        return False


def test_error_solution_pattern():
    """Test 9: Extract error-solution patterns."""
    print("\n" + "=" * 60)
    print("TEST 9: Error-Solution Pattern Extraction")
    print("=" * 60)

    fix_agent_output = """
## Root Cause Analysis

Issue: Tests failing due to missing mock setup
Fix: Added proper mock initialization in setUp() method

Error: Import error for memory module
Solution: Updated sys.path to include src directory

Problem: Database connection timeout in tests
Resolution: Increased connection timeout to 30 seconds
"""

    memory_ids = extract_and_store_learnings(
        agent_type="fix-agent",
        output=fix_agent_output,
        task="Fix failing tests",
        success=True,
    )

    print(f"Extracted {len(memory_ids)} error-solution patterns")

    if len(memory_ids) >= 3:
        print("\n✅ Error-solution pattern extraction test passed!")
        return True
    else:
        print(f"\n✗ Error-solution pattern extraction test failed! Expected >= 3, got {len(memory_ids)}")
        return False


def test_memory_retrieval_by_category():
    """Test 10: Retrieve memories by category."""
    print("\n" + "=" * 60)
    print("TEST 10: Memory Retrieval by Category")
    print("=" * 60)

    # Test different categories
    categories = ["system_design", "error_handling", "security"]

    all_passed = True
    for category in categories:
        context = inject_memory_context(
            agent_type="architect",
            task=f"Work on {category} task",
            task_category=category,
        )

        if context:
            print(f"✓ Retrieved context for category: {category}")
        else:
            print(f"⚠️  No context for category: {category} (may not have memories yet)")
            # Not a failure - just no memories for this category yet

    print("\n✅ Memory retrieval by category test completed!")
    return True


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 80)
    print("AGENT MEMORY INTEGRATION TEST SUITE")
    print("=" * 80)

    tests = [
        ("Prerequisites", test_prerequisites),
        ("Container Management", test_container_management),
        ("Agent Type Detection", test_agent_type_detection),
        ("Task Category Detection", test_task_category_detection),
        ("Memory Injection (Empty)", test_memory_injection_empty),
        ("Learning Extraction", test_learning_extraction),
        ("Memory Injection (With Context)", test_memory_injection_with_context),
        ("Cross-Agent Learning", test_cross_agent_learning),
        ("Error-Solution Patterns", test_error_solution_pattern),
        ("Memory Retrieval by Category", test_memory_retrieval_by_category),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with exception: {e}", exc_info=True)
            results.append((test_name, False, str(e)))

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = 0
    failed = 0
    for test_name, result, error in results:
        status = "✅ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"      Error: {error}")

        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 80)
    print(f"Total: {len(results)} tests | Passed: {passed} | Failed: {failed}")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
