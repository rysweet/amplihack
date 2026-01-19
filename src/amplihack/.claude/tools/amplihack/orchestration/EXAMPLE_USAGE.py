"""Example usage of the orchestration infrastructure.

This file demonstrates how to use the orchestration infrastructure
for common patterns. It's meant as documentation and testing.
"""

from pathlib import Path

from orchestration import (
    OrchestratorSession,
    run_batched,
    run_parallel,
    run_sequential,
    run_with_fallback,
)


def example_parallel_execution():
    """Example: Run multiple agents in parallel."""
    print("\n=== Example: Parallel Execution ===\n")

    # Create session
    session = OrchestratorSession(
        pattern_name="parallel-agents",
        working_dir=Path.cwd(),
    )

    # Create multiple processes
    processes = [
        session.create_process(
            prompt="Analyze the security aspects of this codebase",
            process_id="security-agent",
        ),
        session.create_process(
            prompt="Analyze the performance characteristics of this codebase",
            process_id="performance-agent",
        ),
        session.create_process(
            prompt="Analyze the maintainability of this codebase",
            process_id="maintainability-agent",
        ),
    ]

    # Run in parallel
    session.log("Starting parallel execution")
    results = run_parallel(processes, max_workers=3)

    # Report results
    successful = [r for r in results if r.exit_code == 0]
    session.log(f"Completed {len(successful)}/{len(results)} successfully")

    for result in results:
        session.log(
            f"{result.process_id}: exit_code={result.exit_code}, duration={result.duration:.1f}s"
        )

    return results


def example_sequential_pipeline():
    """Example: Sequential execution with output passing."""
    print("\n=== Example: Sequential Pipeline ===\n")

    # Create session
    session = OrchestratorSession(
        pattern_name="sequential-pipeline",
        working_dir=Path.cwd(),
    )

    # Create pipeline stages
    processes = [
        session.create_process(
            prompt="Analyze the codebase and identify improvement areas",
            process_id="stage1-analyze",
        ),
        session.create_process(
            prompt="Based on the analysis, create a detailed improvement plan",
            process_id="stage2-plan",
        ),
        session.create_process(
            prompt="Implement the highest priority improvements from the plan",
            process_id="stage3-implement",
        ),
    ]

    # Run sequentially with output passing
    session.log("Starting sequential pipeline")
    results = run_sequential(processes, pass_output=True, stop_on_failure=True)

    # Report results
    session.log(f"Pipeline completed {len(results)} stages")

    for i, result in enumerate(results, 1):
        session.log(f"Stage {i}: exit_code={result.exit_code}, duration={result.duration:.1f}s")

    return results


def example_fallback_strategy():
    """Example: Fallback execution strategy."""
    print("\n=== Example: Fallback Strategy ===\n")

    # Create session
    session = OrchestratorSession(
        pattern_name="fallback-strategy",
        working_dir=Path.cwd(),
    )

    # Create fallback chain (try different approaches)
    processes = [
        session.create_process(
            prompt="Use advanced analysis techniques to solve this problem",
            process_id="approach-1-advanced",
            timeout=300,
        ),
        session.create_process(
            prompt="Use standard analysis techniques to solve this problem",
            process_id="approach-2-standard",
            timeout=300,
        ),
        session.create_process(
            prompt="Use basic analysis techniques to solve this problem",
            process_id="approach-3-basic",
            timeout=300,
        ),
    ]

    # Run with fallback
    session.log("Starting fallback strategy")
    result = run_with_fallback(processes, timeout=300)

    # Report result
    session.log(
        f"Fallback completed using {result.process_id}: "
        f"exit_code={result.exit_code}, duration={result.duration:.1f}s"
    )

    return result


def example_batched_execution():
    """Example: Batched parallel execution."""
    print("\n=== Example: Batched Execution ===\n")

    # Create session
    session = OrchestratorSession(
        pattern_name="batched-execution",
        working_dir=Path.cwd(),
    )

    # Create many processes
    processes = [
        session.create_process(
            prompt=f"Analyze module {i}",
            process_id=f"analyze-module-{i:02d}",
        )
        for i in range(10)
    ]

    # Run in batches
    session.log("Starting batched execution (batch_size=3)")
    results = run_batched(processes, batch_size=3)

    # Report results
    successful = [r for r in results if r.exit_code == 0]
    session.log(f"Completed {len(successful)}/{len(results)} successfully")

    return results


def main():
    """Run all examples (commented out by default)."""
    print("Orchestration Infrastructure Examples")
    print("=" * 80)
    print("\nThis file contains example code demonstrating usage.")
    print("Uncomment the examples you want to run.\n")

    # Uncomment to run examples:
    # example_parallel_execution()
    # example_sequential_pipeline()
    # example_fallback_strategy()
    # example_batched_execution()

    print("\nExamples completed. Check .claude/runtime/logs/ for output.")


if __name__ == "__main__":
    main()
