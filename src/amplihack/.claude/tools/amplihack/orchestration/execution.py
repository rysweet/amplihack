"""Execution helpers for orchestrating multiple Claude processes.

Provides utilities for running processes in parallel, sequential, or with fallback
strategies. Handles coordination, error handling, and result collection.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .claude_process import ClaudeProcess, ProcessResult


def run_parallel(
    processes: list[ClaudeProcess],
    max_workers: int | None = None,
) -> list[ProcessResult]:
    """Run multiple Claude processes in parallel.

    Executes processes concurrently using ThreadPoolExecutor. Returns results
    in completion order (not submission order). Handles exceptions gracefully
    by converting them to failed ProcessResults.

    Args:
        processes: List of ClaudeProcess instances to run
        max_workers: Maximum number of concurrent workers (default: None = unlimited)

    Returns:
        List of ProcessResult in completion order

    Example:
        >>> processes = [
        ...     ClaudeProcess("task1", "p1", cwd, log_dir),
        ...     ClaudeProcess("task2", "p2", cwd, log_dir),
        ...     ClaudeProcess("task3", "p3", cwd, log_dir),
        ... ]
        >>> results = run_parallel(processes, max_workers=2)
        >>> successful = [r for r in results if r.exit_code == 0]
        >>> print(f"Completed {len(successful)}/{len(results)} successfully")
    """
    if not processes:
        return []

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all processes
        future_to_process = {executor.submit(process.run): process for process in processes}

        # Collect results as they complete
        for future in as_completed(future_to_process):
            process = future_to_process[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Convert exception to failed ProcessResult
                error_result = ProcessResult(
                    exit_code=-1,
                    output="",
                    stderr=f"Parallel execution exception: {e}",
                    duration=0.0,
                    process_id=process.process_id,
                )
                results.append(error_result)

    return results


def run_sequential(
    processes: list[ClaudeProcess],
    pass_output: bool = False,
    stop_on_failure: bool = False,
) -> list[ProcessResult]:
    """Run Claude processes sequentially.

    Executes processes one at a time in order. Optionally passes output from
    each process to the next, and can stop on first failure.

    Args:
        processes: List of ClaudeProcess instances to run in order
        pass_output: If True, append previous output to next prompt (default: False)
        stop_on_failure: If True, stop on first non-zero exit code (default: False)

    Returns:
        List of ProcessResult in execution order

    Example:
        >>> processes = [
        ...     ClaudeProcess("analyze code", "p1", cwd, log_dir),
        ...     ClaudeProcess("suggest improvements", "p2", cwd, log_dir),
        ...     ClaudeProcess("implement changes", "p3", cwd, log_dir),
        ... ]
        >>> results = run_sequential(processes, pass_output=True)
        >>> for i, result in enumerate(results):
        ...     print(f"Step {i+1}: exit_code={result.exit_code}")
    """
    if not processes:
        return []

    results = []
    accumulated_output = ""

    for i, process in enumerate(processes):
        # Pass accumulated output to next process if enabled
        if pass_output and i > 0 and accumulated_output:
            context = f"\n\n--- Previous output ---\n{accumulated_output}\n\n--- New task ---\n"
            process.prompt = context + process.prompt

        # Run process
        result = process.run()
        results.append(result)

        # Update accumulated output
        if pass_output:
            accumulated_output += result.output

        # Stop on failure if requested
        if stop_on_failure and result.exit_code != 0:
            process.log(
                f"Stopping sequential execution due to failure (exit_code={result.exit_code})",
                level="WARNING",
            )
            break

    return results


def run_with_fallback(
    processes: list[ClaudeProcess],
    timeout: int | None = None,
) -> ProcessResult:
    """Run processes with fallback strategy.

    Tries each process in order until one succeeds. Applies timeout to each
    attempt. Returns first success or final failure.

    Useful for trying different approaches or models when one might fail.

    Args:
        processes: List of ClaudeProcess instances to try in order
        timeout: Timeout per process in seconds (default: None = no timeout)

    Returns:
        First successful ProcessResult, or last failure if all fail

    Example:
        >>> # Try with different models or prompts
        >>> processes = [
        ...     ClaudeProcess("task", "primary", cwd, log_dir, model="claude-3-opus"),
        ...     ClaudeProcess("task", "fallback", cwd, log_dir, model="claude-3-sonnet"),
        ... ]
        >>> result = run_with_fallback(processes, timeout=300)
        >>> print(f"Used: {result.process_id}, exit_code={result.exit_code}")
    """
    if not processes:
        raise ValueError("run_with_fallback requires at least one process")

    last_result = None

    for process in processes:
        # Apply timeout if specified
        if timeout:
            process.timeout = timeout

        process.log("Attempting process (fallback strategy)")
        result = process.run()

        # Return on success
        if result.exit_code == 0:
            process.log("Process succeeded, skipping remaining fallbacks")
            return result

        # Store last result
        last_result = result
        process.log(
            f"Process failed (exit_code={result.exit_code}), trying next fallback",
            level="WARNING",
        )

    # All failed, return last result
    if last_result:
        last_result.stderr = (
            f"All {len(processes)} fallback attempts failed. Last error: {last_result.stderr}"
        )

    return last_result


def run_batched(
    processes: list[ClaudeProcess],
    batch_size: int,
    pass_output: bool = False,
) -> list[ProcessResult]:
    """Run processes in batches with parallel execution within each batch.

    Useful when you want some parallelism but need to control resource usage
    or when later batches depend on earlier ones.

    Args:
        processes: List of ClaudeProcess instances
        batch_size: Number of processes to run in parallel per batch
        pass_output: If True, pass outputs from previous batch to next (default: False)

    Returns:
        List of ProcessResult in batch completion order

    Example:
        >>> # Run 10 processes in batches of 3
        >>> processes = [ClaudeProcess(f"task {i}", f"p{i}", cwd, log_dir)
        ...              for i in range(10)]
        >>> results = run_batched(processes, batch_size=3)
        >>> # Runs: [p0,p1,p2] then [p3,p4,p5] then [p6,p7,p8] then [p9]
    """
    if not processes:
        return []

    all_results = []
    accumulated_output = ""

    # Process in batches
    for i in range(0, len(processes), batch_size):
        batch = processes[i : i + batch_size]

        # Pass accumulated output to batch if enabled
        if pass_output and accumulated_output:
            for process in batch:
                context = (
                    f"\n\n--- Previous batch output ---\n{accumulated_output}\n\n--- New task ---\n"
                )
                process.prompt = context + process.prompt

        # Run batch in parallel
        batch_results = run_parallel(batch)
        all_results.extend(batch_results)

        # Update accumulated output
        if pass_output:
            batch_output = "\n\n".join(r.output for r in batch_results if r.exit_code == 0)
            accumulated_output += batch_output

    return all_results
