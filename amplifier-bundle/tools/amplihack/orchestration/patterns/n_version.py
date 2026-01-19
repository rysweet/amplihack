"""N-Version Programming orchestrator.

Implements N-version programming pattern for critical decisions where multiple
independent implementations are generated and compared to select the best solution.

Based on: .claude/workflow/N_VERSION_WORKFLOW.md
"""

from pathlib import Path
from typing import Any

from ..execution import run_parallel
from ..session import OrchestratorSession

# Default diversity profiles for N implementations
DEFAULT_PROFILES = [
    {
        "name": "conservative",
        "description": "Focus on proven patterns and safety",
        "traits": "Use proven design patterns, comprehensive error handling, defensive programming",
    },
    {
        "name": "pragmatic",
        "description": "Balance trade-offs for practical solutions",
        "traits": "Balance simplicity and robustness, standard library solutions, practical trade-offs",
    },
    {
        "name": "minimalist",
        "description": "Prioritize ruthless simplicity",
        "traits": "Ruthless simplification, minimal dependencies, direct implementation",
    },
    {
        "name": "innovative",
        "description": "Explore novel approaches and optimizations",
        "traits": "Explore novel approaches, consider optimizations, creative solutions",
    },
    {
        "name": "performance_focused",
        "description": "Optimize for speed and efficiency",
        "traits": "Optimize for speed and efficiency, consider resource usage, benchmark-driven",
    },
]

# Default selection criteria in priority order
DEFAULT_CRITERIA = [
    "correctness",
    "security",
    "simplicity",
    "philosophy_compliance",
    "performance",
]


def run_n_version(
    task_prompt: str,
    n: int = 3,
    model: str | None = None,
    working_dir: Path | None = None,
    selection_criteria: list[str] | None = None,
    diversity_profiles: list[dict[str, str]] | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Execute N-version programming pattern.

    Generates N independent implementations in parallel, compares them using
    a reviewer agent, and selects the best implementation based on criteria.

    Steps:
    1. Create N independent implementations in parallel
    2. Spawn reviewer subprocess to compare outputs
    3. Select best or synthesize hybrid
    4. Return selected implementation with rationale

    Args:
        task_prompt: The task specification to implement
        n: Number of independent implementations to generate (default: 3)
        model: Claude model to use for all processes (default: None = CLI default)
        working_dir: Working directory for processes (default: current dir)
        selection_criteria: Criteria for selecting best version (default: DEFAULT_CRITERIA)
        diversity_profiles: Profiles for implementation diversity (default: DEFAULT_PROFILES)
        timeout: Timeout per implementation in seconds (default: None = no timeout)

    Returns:
        Dict containing:
        - versions: List[ProcessResult] - all N implementation outputs
        - comparison: ProcessResult - reviewer analysis
        - selected: str - chosen implementation or "hybrid"
        - rationale: str - why this was selected
        - session_id: str - session identifier for logs
        - success: bool - whether operation completed successfully

    Example:
        >>> result = run_n_version(
        ...     task_prompt="Implement password hashing function",
        ...     n=3,
        ...     selection_criteria=["security", "best_practices"]
        ... )
        >>> print(f"Selected: {result['selected']}")
        >>> print(f"Rationale: {result['rationale']}")
    """
    # Setup
    working_dir = working_dir or Path.cwd()
    selection_criteria = selection_criteria or DEFAULT_CRITERIA
    diversity_profiles = diversity_profiles or DEFAULT_PROFILES

    # Create session
    session = OrchestratorSession(
        pattern_name="n-version",
        working_dir=working_dir,
        model=model,
    )

    session.log(f"Starting N-Version Programming with N={n}")
    session.log(f"Selection criteria: {', '.join(selection_criteria)}")

    # Step 1: Prepare common context (clear specification)
    session.log("Step 1: Preparing common context")

    # Step 2: Generate N independent implementations in parallel
    session.log(f"Step 2: Generating {n} independent implementations in parallel")

    processes = []
    for i in range(n):
        profile = diversity_profiles[i % len(diversity_profiles)]

        # Build prompt with profile-specific guidance
        impl_prompt = f"""You are implementing a task using the N-Version Programming pattern.

TASK SPECIFICATION:
{task_prompt}

CRITICAL REQUIREMENTS:
1. You are one of {n} independent implementations (Version {i + 1})
2. DO NOT consult or share context with other implementations
3. Produce a COMPLETE, WORKING implementation
4. Include tests that verify correctness
5. Document your approach and design decisions
6. Follow project philosophy: ruthless simplicity, zero-BS implementation

Your implementation approach should follow the "{profile["name"]}" profile:
{profile["traits"]}

Deliver a complete implementation with:
- All code files needed
- Test files proving correctness
- Brief explanation of your approach

Begin implementation now.
"""

        process = session.create_process(
            prompt=impl_prompt,
            process_id=f"version_{i + 1}_{profile['name']}",
            timeout=timeout,
        )
        processes.append(process)

    # Execute all implementations in parallel
    session.log(f"Executing {n} implementations in parallel...")
    version_results = run_parallel(processes)

    # Log results
    successful_versions = [v for v in version_results if v.exit_code == 0]
    session.log(f"Completed {len(successful_versions)}/{n} implementations successfully")

    if len(successful_versions) == 0:
        session.log("ERROR: All implementations failed", level="ERROR")
        return {
            "versions": version_results,
            "comparison": None,
            "selected": None,
            "rationale": "All implementations failed to complete",
            "session_id": session.session_id,
            "success": False,
        }

    # Step 3: Collect and compare implementations
    session.log("Step 3: Comparing implementations with reviewer agent")

    # Build comparison prompt
    versions_summary = []
    for i, result in enumerate(version_results):
        profile = diversity_profiles[i % len(diversity_profiles)]
        status = "SUCCESS" if result.exit_code == 0 else "FAILED"
        versions_summary.append(
            f"Version {i + 1} ({profile['name']}): {status}\n"
            f"Duration: {result.duration:.1f}s\n"
            f"Output length: {len(result.output)} chars\n"
        )

    comparison_prompt = f"""You are a reviewer agent analyzing multiple implementations from N-Version Programming.

ORIGINAL TASK:
{task_prompt}

SELECTION CRITERIA (in priority order):
{chr(10).join(f"{i + 1}. {criterion}" for i, criterion in enumerate(selection_criteria))}

IMPLEMENTATIONS GENERATED:
{chr(10).join(versions_summary)}

FULL OUTPUTS:
"""

    for i, result in enumerate(version_results):
        profile = diversity_profiles[i % len(diversity_profiles)]
        comparison_prompt += f"""

{"=" * 80}
VERSION {i + 1} ({profile["name"]}) - Exit Code: {result.exit_code}
{"=" * 80}

{result.output[:5000]}  {"...(truncated)" if len(result.output) > 5000 else ""}
"""

    comparison_prompt += f"""

{"=" * 80}
YOUR TASK:
{"=" * 80}

Analyze all implementations according to the selection criteria:

1. **Correctness** - Does it meet all requirements? Are there bugs?
2. **Security** - Any vulnerabilities or security anti-patterns?
3. **Simplicity** - How simple and clear is the implementation?
4. **Philosophy Compliance** - Does it follow project principles?
5. **Performance** - Efficiency and resource usage considerations?

Provide:

1. **Comparison Matrix** - Score each version on each criterion
2. **Analysis** - Detailed evaluation of each implementation
3. **Selection** - Which version to use (or "HYBRID" if synthesizing best parts)
4. **Rationale** - Clear explanation of why this selection
5. **Implementation Path** - If hybrid, explain what to take from each version

Format your response as:

## Comparison Matrix
| Version | Correctness | Security | Simplicity | Philosophy | Performance |
|---------|-------------|----------|------------|------------|-------------|
| v1      | PASS/FAIL   | score    | score      | score      | score       |
...

## Analysis
[Detailed evaluation of each version]

## Selection
[Version number or "HYBRID"]

## Rationale
[Clear explanation of selection decision]

## Implementation Path
[If hybrid: specific guidance on what to combine]
"""

    # Run reviewer comparison
    reviewer_process = session.create_process(
        prompt=comparison_prompt,
        process_id="reviewer_comparison",
        timeout=timeout,
    )

    session.log("Running reviewer comparison...")
    comparison_result = reviewer_process.run()

    if comparison_result.exit_code != 0:
        session.log(
            "WARNING: Reviewer comparison failed, selecting first successful version",
            level="WARNING",
        )
        # Fallback: select first successful version
        selected_idx = next(i for i, v in enumerate(version_results) if v.exit_code == 0)
        return {
            "versions": version_results,
            "comparison": comparison_result,
            "selected": f"version_{selected_idx + 1}",
            "rationale": "Reviewer failed, selected first successful implementation",
            "session_id": session.session_id,
            "success": True,
        }

    # Step 4: Extract selection from reviewer output
    session.log("Step 4: Processing selection decision")

    # Parse reviewer output to extract selection
    reviewer_output = comparison_result.output.lower()
    selected = None
    rationale = ""

    # Try to find selection in reviewer output
    if "hybrid" in reviewer_output:
        selected = "hybrid"
    else:
        # Look for explicit version selection
        for i in range(n):
            if f"version {i + 1}" in reviewer_output or f"v{i + 1}" in reviewer_output:
                # Check if this is mentioned as the selection
                if any(
                    keyword in reviewer_output
                    for keyword in ["select", "chosen", "best", "recommend"]
                ):
                    selected = f"version_{i + 1}"
                    break

    # Extract rationale section
    if "## rationale" in reviewer_output:
        rationale_start = reviewer_output.find("## rationale")
        rationale_section = comparison_result.output[rationale_start : rationale_start + 1000]
        rationale = rationale_section
    else:
        rationale = "See comparison output for full rationale"

    # Fallback if we couldn't parse selection
    if selected is None:
        session.log(
            "WARNING: Could not parse selection from reviewer, selecting first successful version",
            level="WARNING",
        )
        selected_idx = next(i for i, v in enumerate(version_results) if v.exit_code == 0)
        selected = f"version_{selected_idx + 1}"

    session.log(f"Selected: {selected}")
    session.log(f"Session logs: {session.log_dir}")

    return {
        "versions": version_results,
        "comparison": comparison_result,
        "selected": selected,
        "rationale": rationale,
        "session_id": session.session_id,
        "success": True,
    }
