#!/usr/bin/env python3
"""Demo script showing ParallelOrchestrator usage.

This demonstrates how to use the parallel orchestrator to coordinate
multiple agents working on sub-issues.
"""

from pathlib import Path
from parallel_task_orchestrator.core import ParallelOrchestrator
from parallel_task_orchestrator.models.orchestration import OrchestrationConfig


def demo_basic_orchestrator():
    """Demonstrate basic orchestrator functionality."""
    print("=" * 60)
    print("ParallelOrchestrator Demo")
    print("=" * 60)

    # Create orchestrator with custom configuration
    worktree_base = Path("./demo_worktrees")
    orchestrator = ParallelOrchestrator(
        worktree_base=worktree_base,
        timeout_minutes=120,
        status_poll_interval=30
    )

    print(f"\n✓ Orchestrator created")
    print(f"  Worktree base: {orchestrator.worktree_base}")
    print(f"  Timeout: {orchestrator.timeout_minutes} minutes")
    print(f"  Poll interval: {orchestrator.status_poll_interval} seconds")

    # Check components initialized
    print(f"\n✓ Components initialized:")
    print(f"  - IssueParser: {type(orchestrator.issue_parser).__name__}")
    print(f"  - AgentDeployer: {type(orchestrator.agent_deployer).__name__}")
    print(f"  - StatusMonitor: {type(orchestrator.status_monitor).__name__}")
    print(f"  - PRCreator: {type(orchestrator.pr_creator).__name__}")

    # Show current status
    status = orchestrator.get_current_status()
    print(f"\n✓ Current status: {status['status']}")

    # Example configuration
    config = OrchestrationConfig(
        parent_issue=1783,
        sub_issues=[101, 102, 103],
        parallel_degree=3,
        timeout_minutes=120,
        recovery_strategy="continue_on_failure"
    )

    print(f"\n✓ Example configuration:")
    print(f"  Parent issue: #{config.parent_issue}")
    print(f"  Sub-issues: {config.sub_issues}")
    print(f"  Parallel degree: {config.parallel_degree}")
    print(f"  Recovery strategy: {config.recovery_strategy}")

    print("\n" + "=" * 60)
    print("To run orchestration (requires GitHub access):")
    print("=" * 60)
    print("""
    # Basic usage
    result = orchestrator.orchestrate(
        parent_issue=1783,
        parallel_degree=3
    )

    # The orchestrator will:
    # 1. Parse parent issue to extract sub-issues
    # 2. Deploy agents to isolated git worktrees
    # 3. Monitor agent progress via status files
    # 4. Create PRs for completed work
    # 5. Generate comprehensive report

    # Result includes:
    print(f"Success: {result['success']}")
    print(f"Completed: {result['completed']}/{result['total_sub_issues']}")
    print(f"Success rate: {result['success_rate']}%")
    print(f"PR links: {result['pr_links']}")
    """)

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    demo_basic_orchestrator()
