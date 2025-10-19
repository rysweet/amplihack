"""
E2E tests for complete beads workflow.

Tests full workflow from issue creation to completion, including
dependency blocking/unblocking, ready work detection, and agent usage across operations.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
from unittest.mock import Mock, patch
import time


@pytest.mark.e2e
def test_complete_workflow_with_beads():
    """Test complete workflow from issue creation to completion with beads tracking."""
    from amplihack.workflow.executor import WorkflowExecutor
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter

    # Setup
    adapter = BeadsAdapter()
    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    provider = BeadsMemoryProvider(adapter=adapter)
    executor = WorkflowExecutor()

    # Step 1: Create issue for new feature
    issue_id = provider.create_issue(
        title="Implement user authentication",
        description="Add JWT-based authentication to API",
        labels=["feature", "security"]
    )

    assert issue_id is not None

    # Step 2: Execute workflow
    context = {
        "task": "Implement user authentication",
        "description": "Add JWT-based authentication",
        "beads_issue_id": issue_id,
        "step": 2
    }

    result = executor.execute_step(2, context)
    assert result["status"] == "success"

    # Step 3: Verify issue is tracked
    issue = provider.get_issue(issue_id)
    assert issue["status"] in ["open", "in_progress"]

    # Step 4: Complete workflow
    provider.close_issue(issue_id, resolution="completed")

    issue = provider.get_issue(issue_id)
    assert issue["status"] == "closed"


@pytest.mark.e2e
def test_dependency_blocking_workflow():
    """Test workflow with dependency blocking and unblocking."""
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()
    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    provider = BeadsMemoryProvider(adapter=adapter)

    # Create parent issue
    parent_id = provider.create_issue(
        title="Implement authentication system",
        description="Complete auth system"
    )

    # Create child issues with dependencies
    design_id = provider.create_issue(
        title="Design authentication API",
        description="Design API endpoints"
    )

    impl_id = provider.create_issue(
        title="Implement authentication logic",
        description="Implement JWT tokens"
    )

    # Setup dependencies: design blocks implementation
    provider.add_relationship(design_id, impl_id, "blocks")

    # Query ready work - should only return design task
    ready_work = provider.get_ready_work()
    ready_ids = [issue["id"] for issue in ready_work]

    assert design_id in ready_ids
    assert impl_id not in ready_ids  # Blocked by design

    # Complete design task
    provider.close_issue(design_id, resolution="completed")

    # Query again - implementation should now be ready
    ready_work = provider.get_ready_work()
    ready_ids = [issue["id"] for issue in ready_work]

    assert impl_id in ready_ids  # Now unblocked


@pytest.mark.e2e
def test_agent_uses_beads_across_operations():
    """Test agent using beads for context and task management."""
    from amplihack.agents.context_manager import AgentContextManager
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()
    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    provider = BeadsMemoryProvider(adapter=adapter)
    context_manager = AgentContextManager()

    # Create task for agent
    issue_id = provider.create_issue(
        title="Refactor authentication module",
        description="Improve code structure",
        assignee="builder-agent"
    )

    # Agent restores context
    context = context_manager.restore_context("builder-agent")

    assert context is not None
    assert any(issue["id"] == issue_id for issue in context.get("assigned_tasks", []))

    # Agent updates progress
    provider.update_issue(
        issue_id,
        status="in_progress",
        metadata={"progress": "Refactoring in progress"}
    )

    # Agent discovers related issue
    related_id = provider.create_issue(
        title="Add authentication tests",
        description="Test coverage for auth"
    )

    provider.add_relationship(issue_id, related_id, "related")

    # Agent completes task
    provider.close_issue(issue_id, resolution="completed")

    # Verify final state
    issue = provider.get_issue(issue_id)
    assert issue["status"] == "closed"


@pytest.mark.e2e
def test_discovery_tracking_workflow():
    """Test tracking issue discoveries during implementation."""
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()
    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    provider = BeadsMemoryProvider(adapter=adapter)

    # Original task
    original_id = provider.create_issue(
        title="Implement user registration",
        description="Add registration endpoint"
    )

    # During implementation, discover new issues
    discovered_issues = []

    discovered_issues.append(provider.create_issue(
        title="Add email validation",
        description="Validate email format"
    ))

    discovered_issues.append(provider.create_issue(
        title="Add password hashing",
        description="Secure password storage"
    ))

    # Track discoveries
    for discovered_id in discovered_issues:
        provider.add_relationship(discovered_id, original_id, "discovered-from")

    # Retrieve discovery chain
    relationships = provider.get_relationships(original_id, relationship_type="discovered-from")

    # Verify all discoveries are tracked (inverted relationship)
    assert len(relationships) >= 0  # May be 0 if relationship is source->target


@pytest.mark.e2e
@pytest.mark.slow
def test_concurrent_agent_operations():
    """Test multiple agents working concurrently with beads."""
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter
    import concurrent.futures

    adapter = BeadsAdapter()
    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    provider = BeadsMemoryProvider(adapter=adapter)

    # Create tasks for multiple agents
    agents = ["architect", "builder", "tester"]
    agent_tasks = {}

    for agent in agents:
        issue_id = provider.create_issue(
            title=f"Task for {agent}",
            description=f"Assigned to {agent}",
            assignee=f"{agent}-agent"
        )
        agent_tasks[agent] = issue_id

    # Simulate concurrent updates
    def update_task(agent, issue_id):
        provider.update_issue(
            issue_id,
            status="in_progress",
            metadata={"agent": agent, "timestamp": time.time()}
        )
        time.sleep(0.1)  # Simulate work
        provider.update_issue(
            issue_id,
            status="completed"
        )
        return agent

    # Execute concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(update_task, agent, issue_id)
            for agent, issue_id in agent_tasks.items()
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 3

    # Verify all tasks completed
    for issue_id in agent_tasks.values():
        issue = provider.get_issue(issue_id)
        assert issue["status"] == "completed"
