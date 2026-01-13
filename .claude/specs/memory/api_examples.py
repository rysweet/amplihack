"""Usage Examples for 5-Type Memory System API.

These examples demonstrate the clean, minimal API contracts for the memory system.
All examples follow the brick & studs philosophy with ruthlessly simple interfaces.
"""

from datetime import datetime, timedelta

from .api_contracts import (
    MemoryCoordinator,
    MemoryType,
    RetrievalQuery,
    StorageRequest,
)


# ============================================================================
# Example 1: Basic Storage and Retrieval
# ============================================================================


def example_basic_usage(coordinator: MemoryCoordinator):
    """Basic memory storage and retrieval flow."""

    # Store a semantic memory (learning)
    request = StorageRequest(
        content="REST APIs should use plural resource names (/users not /user)",
        memory_type=MemoryType.SEMANTIC,
        agent_id="architect",
        importance=8,
        tags=["api-design", "best-practice"],
    )

    memory_id = coordinator.store(request)
    if memory_id:
        print(f"Stored memory: {memory_id}")
    else:
        print("Memory rejected by review (score <4)")

    # Retrieve semantic memories
    query = RetrievalQuery(
        memory_type=MemoryType.SEMANTIC, min_importance=7, limit=5, tags=["api-design"]
    )

    memories = coordinator.retrieve(query)
    for memory in memories:
        print(f"Memory: {memory.content[:50]}...")


# ============================================================================
# Example 2: Episodic Memory - Conversation History
# ============================================================================


def example_episodic_memory(coordinator: MemoryCoordinator):
    """Store and retrieve conversation events."""

    # Store conversation turn
    request = StorageRequest(
        content="User asked about authentication implementation",
        memory_type=MemoryType.EPISODIC,
        agent_id="orchestrator",
        importance=6,
        metadata={
            "timestamp": datetime.now().isoformat(),
            "participants": ["user", "architect", "builder"],
            "topic": "authentication",
        },
    )

    memory_id = coordinator.store(request)

    # Retrieve recent conversations about auth
    query = RetrievalQuery(
        memory_type=MemoryType.EPISODIC,
        search_text="authentication",
        limit=10,
    )

    recent = coordinator.retrieve(query)
    print(f"Found {len(recent)} recent auth discussions")


# ============================================================================
# Example 3: Prospective Memory - TODOs and Reminders
# ============================================================================


def example_prospective_memory(coordinator: MemoryCoordinator):
    """Store and manage future intentions."""

    # Store TODO
    request = StorageRequest(
        content="TODO: Add rate limiting to API endpoints after MVP",
        memory_type=MemoryType.PROSPECTIVE,
        agent_id="architect",
        importance=7,
        metadata={
            "trigger": "after_mvp",
            "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
        },
        tags=["todo", "api", "security"],
    )

    coordinator.store(request)

    # Retrieve pending TODOs
    query = RetrievalQuery(
        memory_type=MemoryType.PROSPECTIVE, min_importance=6, tags=["todo"]
    )

    todos = coordinator.retrieve(query)
    print(f"Pending TODOs: {len(todos)}")
    for todo in todos:
        print(f"  - {todo.content}")


# ============================================================================
# Example 4: Procedural Memory - Workflows
# ============================================================================


def example_procedural_memory(coordinator: MemoryCoordinator):
    """Store and retrieve learned procedures."""

    # Store CI fix procedure
    request = StorageRequest(
        content="""CI Failure Response Procedure:
1. Check logs for error pattern
2. Identify if known pattern (import/config/test/logic)
3. Apply template fix if available
4. Otherwise, use diagnostic mode
5. Verify fix locally before push""",
        memory_type=MemoryType.PROCEDURAL,
        agent_id="ci-diagnostic",
        importance=9,
        metadata={
            "procedure_name": "ci_failure_response",
            "success_rate": 0.85,
            "last_used": datetime.now().isoformat(),
        },
        tags=["ci", "workflow", "diagnostic"],
    )

    coordinator.store(request)

    # Retrieve procedure when needed
    query = RetrievalQuery(
        memory_type=MemoryType.PROCEDURAL, search_text="CI failure", limit=1
    )

    procedures = coordinator.retrieve(query)
    if procedures:
        print(f"Found procedure: {procedures[0].content}")


# ============================================================================
# Example 5: Working Memory - Active Task Context
# ============================================================================


def example_working_memory(coordinator: MemoryCoordinator):
    """Manage temporary task context."""

    # Store current task state
    request = StorageRequest(
        content="Currently implementing authentication: JWT tokens + refresh flow",
        memory_type=MemoryType.WORKING,
        agent_id="builder",
        importance=5,  # Temporary, lower importance
        metadata={
            "task_id": "auth-123",
            "current_step": "jwt_implementation",
            "dependencies": ["user_model", "token_service"],
        },
        tags=["active-task", "auth"],
    )

    coordinator.store(request)

    # Retrieve active task context
    query = RetrievalQuery(
        memory_type=MemoryType.WORKING, agent_id="builder", tags=["active-task"]
    )

    active_tasks = coordinator.retrieve(query)
    print(f"Active tasks: {len(active_tasks)}")

    # Clear working memory after task complete
    count = coordinator.clear_working_memory()
    print(f"Cleared {count} working memory entries")


# ============================================================================
# Example 6: Retrieval with Relevance Scoring
# ============================================================================


def example_smart_retrieval(coordinator: MemoryCoordinator):
    """Use agent review for intelligent retrieval."""

    # Retrieve with relevance scoring
    query = RetrievalQuery(
        memory_type=MemoryType.SEMANTIC, min_importance=6, limit=20  # Broad query
    )

    # Agent reviews score relevance to current context
    context = "Implementing user authentication with JWT tokens and refresh flow"

    relevant = coordinator.retrieve_with_review(query, context)

    # Only memories with relevance score >7 returned
    print(f"Found {len(relevant)} highly relevant memories")
    for memory in relevant:
        print(f"  - {memory.content[:60]}...")


# ============================================================================
# Example 7: Storage with Importance Scoring
# ============================================================================


def example_auto_importance_scoring(coordinator: MemoryCoordinator):
    """Let agents evaluate importance automatically."""

    # Store without importance - agents will score
    request = StorageRequest(
        content="User prefers dark mode in UI",
        memory_type=MemoryType.SEMANTIC,
        agent_id="ui-agent",
        # No importance specified - will be scored by review
        tags=["ui", "preferences"],
    )

    memory_id = coordinator.store(request)

    if memory_id:
        print("Memory stored (agents scored >4)")
    else:
        print("Memory rejected (agents scored <4)")


# ============================================================================
# Example 8: Error Handling
# ============================================================================


def example_error_handling(coordinator: MemoryCoordinator):
    """Graceful error handling patterns."""

    try:
        request = StorageRequest(
            content="Sample memory",
            memory_type=MemoryType.SEMANTIC,
            agent_id="test",
        )
        memory_id = coordinator.store(request)

    except Exception as e:
        # Graceful degradation - continue without memory
        print(f"Memory storage failed: {e}")
        memory_id = None

    # Always check result
    if memory_id:
        print("Memory stored successfully")
    else:
        print("Continuing without memory storage")


# ============================================================================
# Example 9: Cross-Memory-Type Query
# ============================================================================


def example_cross_type_query(coordinator: MemoryCoordinator):
    """Query across multiple memory types."""

    # Search all auth-related memories across types
    queries = [
        RetrievalQuery(
            memory_type=MemoryType.EPISODIC, search_text="auth", limit=5
        ),  # Past discussions
        RetrievalQuery(
            memory_type=MemoryType.SEMANTIC, tags=["auth"], limit=5
        ),  # Learnings
        RetrievalQuery(
            memory_type=MemoryType.PROCEDURAL, tags=["auth"], limit=5
        ),  # Workflows
        RetrievalQuery(
            memory_type=MemoryType.PROSPECTIVE, tags=["auth"], limit=5
        ),  # TODOs
    ]

    all_auth_memories = []
    for query in queries:
        memories = coordinator.retrieve(query)
        all_auth_memories.extend(memories)

    print(f"Total auth-related memories: {len(all_auth_memories)}")


# ============================================================================
# Example 10: Performance-Optimized Retrieval
# ============================================================================


def example_performance_patterns(coordinator: MemoryCoordinator):
    """Patterns for performance-critical paths."""

    # Fast retrieval without agent review (<50ms)
    query = RetrievalQuery(
        memory_type=MemoryType.PROCEDURAL,
        agent_id="ci-agent",
        min_importance=8,
        limit=3,  # Small limit for speed
    )

    memories = coordinator.retrieve(query)  # <50ms

    # Only use agent review when needed
    if len(memories) > 10:  # Too many results
        context = "CI pipeline failure with import errors"
        memories = coordinator.retrieve_with_review(query, context)  # <300ms

    print(f"Retrieved {len(memories)} memories")


# ============================================================================
# Example 11: Batch Operations
# ============================================================================


def example_batch_operations(coordinator: MemoryCoordinator):
    """Efficient batch storage and retrieval."""

    # Store multiple memories
    requests = [
        StorageRequest(
            content=f"Learning {i}: API design pattern",
            memory_type=MemoryType.SEMANTIC,
            agent_id="architect",
            importance=7,
        )
        for i in range(10)
    ]

    memory_ids = []
    for request in requests:
        memory_id = coordinator.store(request)
        if memory_id:
            memory_ids.append(memory_id)

    print(f"Stored {len(memory_ids)} memories")

    # Batch retrieval
    query = RetrievalQuery(memory_type=MemoryType.SEMANTIC, limit=50)

    all_memories = coordinator.retrieve(query)
    print(f"Retrieved {len(all_memories)} memories")


# ============================================================================
# Example 12: Memory Lifecycle Management
# ============================================================================


def example_memory_lifecycle(coordinator: MemoryCoordinator):
    """Managing memory lifecycle with expiration and cleanup."""

    # Store temporary working memory with expiration
    request = StorageRequest(
        content="Debug context: investigating test failure in auth module",
        memory_type=MemoryType.WORKING,
        agent_id="tester",
        importance=5,
        metadata={
            "expires_in_hours": 24,
            "cleanup_after_task": True,
        },
    )

    coordinator.store(request)

    # Clear expired working memories
    count = coordinator.clear_working_memory()
    print(f"Cleared {count} working memories")


# ============================================================================
# Main Demo
# ============================================================================


def main():
    """Run all examples with a mock coordinator."""

    # In real usage, get coordinator from factory:
    # from amplihack.memory.coordinator import get_coordinator
    # coordinator = get_coordinator()

    print("Memory System API Examples")
    print("=" * 60)

    # Note: These examples show API usage patterns.
    # Actual execution requires implementing the coordinator.

    print("\nSee api_contracts.py for complete interface specifications")
    print("See implementation guide for building the coordinator")


if __name__ == "__main__":
    main()
