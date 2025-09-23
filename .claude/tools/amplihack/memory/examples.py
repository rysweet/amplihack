"""Example usage patterns for the Agent Memory System integration.

This module demonstrates common integration patterns and best practices
for using the Agent Memory System in Claude workflows.
"""

import json
import sys
from pathlib import Path

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from paths import get_project_root

    project_root = get_project_root()
    sys.path.insert(0, str(project_root / "src"))
except ImportError:
    # Fallback for standalone execution
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))

from amplihack.memory import MemoryManager, MemoryType


def example_agent_memory_integration():
    """Example: Basic agent memory integration."""
    print("Example 1: Basic Agent Memory Integration")
    print("=" * 50)

    # Initialize memory manager
    memory = MemoryManager(session_id="demo_session")

    # Store architectural decision
    decision_id = memory.store(
        agent_id="architect",
        title="Database Selection: PostgreSQL",
        content="Selected PostgreSQL for ACID compliance and complex queries",
        memory_type=MemoryType.DECISION,
        importance=9,
        tags=["database", "postgresql", "architecture"],
        metadata={"impact": "high", "alternatives": ["MySQL", "MongoDB"]},
    )
    print(f"✓ Stored decision: {decision_id}")

    # Store learned pattern
    pattern_id = memory.store(
        agent_id="architect",
        title="Repository Pattern Implementation",
        content=json.dumps(
            {
                "pattern": "Repository Pattern",
                "description": "Encapsulates data access logic",
                "benefits": ["Testability", "Maintainability", "Separation of concerns"],
                "implementation": "Use abstract base repository with specific implementations",
            },
            indent=2,
        ),
        memory_type=MemoryType.PATTERN,
        importance=7,
        tags=["pattern", "repository", "data-access"],
    )
    print(f"✓ Stored pattern: {pattern_id}")

    # Retrieve recent decisions
    decisions = memory.retrieve(
        agent_id="architect", memory_type=MemoryType.DECISION, min_importance=8, limit=5
    )
    print(f"✓ Retrieved {len(decisions)} high-importance decisions")

    # Search for database-related memories
    db_memories = memory.search("database", agent_id="architect")
    print(f"✓ Found {len(db_memories)} database-related memories")

    print("Example 1 completed successfully!\n")
    return memory


def example_context_preservation():
    """Example: Context preservation across workflow steps."""
    print("Example 2: Context Preservation")
    print("=" * 40)

    from context_preservation import ContextPreserver

    preserver = ContextPreserver(session_id="workflow_session")

    # Preserve conversation context
    context_id = preserver.preserve_conversation_context(
        agent_id="orchestrator",
        conversation_summary="Implementing user authentication system with JWT tokens",
        key_decisions=[
            "Use JWT for stateless authentication",
            "PostgreSQL for user data storage",
            "bcrypt for password hashing",
        ],
        active_tasks=[
            "Design user model schema",
            "Implement JWT token service",
            "Create login/logout endpoints",
            "Add password reset functionality",
        ],
        metadata={"project": "AuthSystem", "priority": "high", "deadline": "2025-10-15"},
    )
    print(f"✓ Preserved conversation context: {context_id}")

    # Preserve workflow state
    workflow_id = preserver.preserve_workflow_state(
        workflow_name="AuthSystem_Implementation",
        current_step="implement_jwt_service",
        completed_steps=["design_user_model", "setup_database"],
        pending_steps=["create_endpoints", "add_password_reset", "write_tests"],
        step_results={
            "design_user_model": {
                "tables": ["users", "user_sessions"],
                "fields": 8,
                "constraints": 5,
            },
            "setup_database": {"migrations": 3, "indexes": 4, "status": "completed"},
        },
        workflow_metadata={"estimated_total_time": "6 hours", "complexity": "medium"},
    )
    print(f"✓ Preserved workflow state: {workflow_id}")

    # Record a decision with full reasoning
    decision_id = preserver.preserve_agent_decisions(
        agent_id="security_specialist",
        decision_title="Password Security: bcrypt with salt rounds",
        decision_description="Use bcrypt with 12 salt rounds for password hashing",
        reasoning="bcrypt is slow by design, making brute force attacks difficult. 12 rounds provides good security vs performance balance.",
        alternatives_considered=[
            "argon2 - newer but less widely supported",
            "scrypt - memory-hard but more complex",
            "PBKDF2 - older standard, less secure",
        ],
        impact_assessment="Medium performance impact on login, high security improvement",
        related_decisions=["jwt_token_decision"],
    )
    print(f"✓ Preserved security decision: {decision_id}")

    # Restore context
    restored_context = preserver.restore_conversation_context("orchestrator")
    if restored_context:
        print(f"✓ Restored context: {len(restored_context['active_tasks'])} active tasks")

    # Restore workflow state
    workflow_state = preserver.restore_workflow_state("AuthSystem_Implementation")
    if workflow_state:
        progress = workflow_state.get("progress_percentage", 0)
        print(f"✓ Restored workflow: {progress:.1f}% complete")

    print("Example 2 completed successfully!\n")
    return preserver


def example_agent_collaboration():
    """Example: Multi-agent collaboration with shared memory."""
    print("Example 3: Agent Collaboration")
    print("=" * 35)

    memory = MemoryManager(session_id="collaboration_session")

    # Architect shares design decisions
    arch_decision = memory.store(
        agent_id="architect",
        title="API Design: RESTful endpoints with OpenAPI spec",
        content=json.dumps(
            {
                "design_approach": "RESTful API",
                "specification": "OpenAPI 3.0",
                "endpoints": [
                    "POST /auth/login",
                    "POST /auth/logout",
                    "POST /auth/refresh",
                    "POST /auth/reset-password",
                ],
                "shared_with": ["backend_dev", "frontend_dev", "tester"],
            },
            indent=2,
        ),
        memory_type=MemoryType.DECISION,
        importance=8,
        tags=["api", "design", "collaboration", "shared"],
        metadata={"recipients": ["backend_dev", "frontend_dev", "tester"]},
    )
    print(f"✓ Architect shared API design: {arch_decision}")

    # Backend developer acknowledges and adds implementation details
    backend_response = memory.store(
        agent_id="backend_dev",
        title="API Implementation: Node.js with Express framework",
        content=json.dumps(
            {
                "framework": "Express.js",
                "middleware": ["cors", "helmet", "rate-limiting"],
                "validation": "joi schema validation",
                "database_layer": "Prisma ORM",
                "response_to": arch_decision,
            },
            indent=2,
        ),
        memory_type=MemoryType.CONTEXT,
        importance=7,
        tags=["implementation", "backend", "collaboration"],
        metadata={"references": arch_decision},
    )
    print(f"✓ Backend dev added implementation details: {backend_response}")

    # Security specialist adds security requirements
    security_requirements = memory.store(
        agent_id="security_specialist",
        title="Security Requirements: Authentication & Authorization",
        content=json.dumps(
            {
                "requirements": [
                    "JWT tokens must expire within 1 hour",
                    "Refresh tokens valid for 7 days maximum",
                    "Rate limiting: 5 login attempts per minute",
                    "HTTPS only for all auth endpoints",
                    "Input validation on all parameters",
                ],
                "compliance": ["OWASP Top 10", "GDPR"],
                "applies_to": arch_decision,
            },
            indent=2,
        ),
        memory_type=MemoryType.CONTEXT,
        importance=9,
        tags=["security", "requirements", "compliance"],
        metadata={"security_level": "high", "references": arch_decision},
    )
    print(f"✓ Security specialist added requirements: {security_requirements}")

    # Retrieve collaboration history
    collaboration_memories = memory.retrieve(tags=["collaboration"], limit=10)
    print(f"✓ Retrieved {len(collaboration_memories)} collaboration memories")

    # Get shared context for a specific agent
    backend_context = memory.retrieve(memory_type=MemoryType.CONTEXT, tags=["backend"], limit=5)
    print(f"✓ Backend context: {len(backend_context)} relevant memories")

    print("Example 3 completed successfully!\n")
    return memory


def example_performance_optimization():
    """Example: Performance-optimized memory operations."""
    print("Example 4: Performance Optimization")
    print("=" * 40)

    import time

    memory = MemoryManager(session_id="performance_test")

    # Batch memory storage for efficiency
    print("Testing batch storage performance...")
    batch_memories = []
    for i in range(50):
        batch_memories.append(
            {
                "agent_id": f"agent_{i % 5}",
                "title": f"Batch Memory {i}",
                "content": f"Content for memory {i} - performance testing",
                "memory_type": MemoryType.CONTEXT,
                "importance": (i % 10) + 1,
                "tags": [f"batch_{i // 10}", "performance", "test"],
            }
        )

    start_time = time.time()
    memory_ids = memory.store_batch(batch_memories)
    batch_time = (time.time() - start_time) * 1000

    print(f"✓ Stored {len(memory_ids)} memories in {batch_time:.2f}ms")
    print(f"✓ Average: {batch_time / len(memory_ids):.2f}ms per memory")

    # Efficient retrieval with filters
    start_time = time.time()
    filtered_memories = memory.retrieve(
        agent_id="agent_1",
        memory_type=MemoryType.CONTEXT,
        min_importance=5,
        tags=["performance"],
        limit=10,
    )
    retrieval_time = (time.time() - start_time) * 1000

    print(f"✓ Retrieved {len(filtered_memories)} memories in {retrieval_time:.2f}ms")

    # Search performance
    start_time = time.time()
    search_results = memory.search("performance testing", limit=20)
    search_time = (time.time() - start_time) * 1000

    print(f"✓ Search completed in {search_time:.2f}ms, found {len(search_results)} results")

    # Performance summary
    all_times = [batch_time / len(memory_ids), retrieval_time, search_time]
    max_time = max(all_times)
    avg_time = sum(all_times) / len(all_times)

    print("✓ Performance summary:")
    print(f"  - Maximum operation time: {max_time:.2f}ms")
    print(f"  - Average operation time: {avg_time:.2f}ms")
    print(f"  - Target <50ms: {'PASS' if max_time < 50 else 'FAIL'}")

    print("Example 4 completed successfully!\n")
    return memory


def example_error_handling():
    """Example: Graceful error handling and fallback patterns."""
    print("Example 5: Error Handling & Graceful Degradation")
    print("=" * 55)

    # Test graceful degradation with invalid database path
    try:
        memory = MemoryManager(db_path="/invalid/path/memory.db")
        print("✗ Should have failed with invalid path")
    except Exception as e:
        print(f"✓ Properly handled invalid database path: {type(e).__name__}")

    # Test with valid memory manager
    memory = MemoryManager(session_id="error_test")

    # Test safe memory operations
    def safe_store(agent_id, title, content):
        """Safe memory storage with fallback."""
        try:
            return memory.store(
                agent_id=agent_id, title=title, content=content, memory_type=MemoryType.CONTEXT
            )
        except Exception as e:
            print(f"Memory storage failed: {e}")
            return None

    # Test successful operation
    memory_id = safe_store("test_agent", "Test Memory", "Test content")
    if memory_id:
        print(f"✓ Safe storage successful: {memory_id}")

    # Test safe retrieval
    def safe_retrieve(agent_id, fallback_data=None):
        """Safe memory retrieval with fallback."""
        try:
            memories = memory.retrieve(agent_id=agent_id, limit=5)
            return memories if memories else (fallback_data or [])
        except Exception as e:
            print(f"Memory retrieval failed: {e}")
            return fallback_data or []

    # Test retrieval
    memories = safe_retrieve("test_agent", fallback_data=[])
    print(f"✓ Safe retrieval returned {len(memories)} memories")

    # Test memory validation
    def validate_memory_content(content):
        """Validate memory content before storage."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Memory content cannot be empty")
        if len(content) > 10000:  # Example limit
            raise ValueError("Memory content too large")
        return True

    # Test validation
    try:
        validate_memory_content("Valid content")
        print("✓ Content validation passed")
    except ValueError as e:
        print(f"✗ Content validation failed: {e}")

    try:
        validate_memory_content("")
        print("✗ Should have failed empty content validation")
    except ValueError:
        print("✓ Empty content validation properly rejected")

    print("Example 5 completed successfully!\n")


def run_all_examples():
    """Run all integration examples."""
    print("Agent Memory System - Integration Examples")
    print("=" * 50)
    print()

    # Run examples
    example_agent_memory_integration()
    example_context_preservation()
    example_agent_collaboration()
    example_performance_optimization()
    example_error_handling()

    print("=" * 50)
    print("All examples completed successfully!")
    print()
    print("Summary:")
    print("✓ Basic agent memory integration")
    print("✓ Context preservation across workflows")
    print("✓ Multi-agent collaboration patterns")
    print("✓ Performance optimization techniques")
    print("✓ Error handling and graceful degradation")
    print()
    print("The Agent Memory System is ready for production use!")


if __name__ == "__main__":
    run_all_examples()
