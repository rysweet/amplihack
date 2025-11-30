"""Fallback Cascade orchestrator.

Implements graceful degradation through cascading fallback strategies.
When optimal approaches fail or timeout, system automatically falls back
to simpler, more reliable alternatives.

Based on: .claude/workflow/CASCADE_WORKFLOW.md
"""

from pathlib import Path
from typing import Any

from ..session import OrchestratorSession

# Timeout strategies
TIMEOUT_STRATEGIES = {
    "aggressive": {"primary": 5, "secondary": 2, "tertiary": 1},
    "balanced": {"primary": 30, "secondary": 10, "tertiary": 5},
    "patient": {"primary": 120, "secondary": 30, "tertiary": 10},
}

# Fallback strategy templates
FALLBACK_TEMPLATES = {
    "quality": {
        "primary": "comprehensive and thorough analysis with all details",
        "secondary": "standard analysis covering main points",
        "tertiary": "minimal quick analysis of essential points only",
    },
    "service": {
        "primary": "using optimal external service or API",
        "secondary": "using cached or alternative service",
        "tertiary": "using local defaults or fallback data",
    },
    "freshness": {
        "primary": "with real-time current data",
        "secondary": "with recent cached data (< 1 hour old)",
        "tertiary": "with historical or default data",
    },
    "completeness": {
        "primary": "processing full dataset completely",
        "secondary": "processing representative sample (10-20%)",
        "tertiary": "using precomputed summary statistics",
    },
    "accuracy": {
        "primary": "with precise calculations and exact results",
        "secondary": "with approximate results and estimations",
        "tertiary": "with rough estimates and order-of-magnitude",
    },
}


def run_cascade(
    task_prompt: str,
    fallback_strategy: str = "quality",
    timeout_strategy: str = "balanced",
    models: list[str] | None = None,
    working_dir: Path | None = None,
    notification_level: str = "warning",
    custom_timeouts: dict[str, int] | None = None,
    custom_constraints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute fallback cascade pattern.

    Attempts primary (optimal) approach first, then falls back to secondary
    (acceptable) and tertiary (minimal) if needed.

    Steps:
    1. Attempt primary (optimal) with timeout
    2. If fails, attempt secondary (pragmatic) with shorter timeout
    3. If fails, attempt tertiary (minimal) with very short timeout
    4. Report degradation level

    Args:
        task_prompt: The task to execute with fallback
        fallback_strategy: Type of degradation ("quality", "service", "freshness", "completeness", "accuracy")
        timeout_strategy: Timeout levels ("aggressive", "balanced", "patient")
        models: Optional list of models to try [primary_model, secondary_model, tertiary_model]
        working_dir: Working directory for processes (default: current dir)
        notification_level: How to notify ("silent", "warning", "explicit")
        custom_timeouts: Override timeout strategy with custom values
        custom_constraints: Override fallback templates with custom constraints

    Returns:
        Dict containing:
        - result: ProcessResult - final successful result
        - cascade_level: str - "primary", "secondary", or "tertiary"
        - degradation: str - description of degradation if any
        - attempts: List[ProcessResult] - all attempts made
        - session_id: str - session identifier for logs
        - success: bool - whether any level succeeded

    Example:
        >>> result = run_cascade(
        ...     task_prompt="Generate API documentation",
        ...     timeout_strategy="balanced"
        ... )
        >>> print(f"Succeeded at {result['cascade_level']} level")
        >>> if result['degradation']:
        ...     print(f"Degradation: {result['degradation']}")
    """
    # Setup
    working_dir = working_dir or Path.cwd()

    # Validate strategies
    if fallback_strategy not in FALLBACK_TEMPLATES:
        raise ValueError(
            f"Unknown fallback_strategy '{fallback_strategy}'. Must be one of: {list(FALLBACK_TEMPLATES.keys())}"
        )

    if timeout_strategy not in TIMEOUT_STRATEGIES:
        raise ValueError(
            f"Unknown timeout_strategy '{timeout_strategy}'. Must be one of: {list(TIMEOUT_STRATEGIES.keys())}"
        )

    # Get timeouts
    if custom_timeouts:
        timeouts = custom_timeouts
    else:
        timeouts = TIMEOUT_STRATEGIES[timeout_strategy]

    # Get constraints
    if custom_constraints:
        constraints = custom_constraints
    else:
        constraints = FALLBACK_TEMPLATES[fallback_strategy]

    # Create session
    session = OrchestratorSession(
        pattern_name="cascade",
        working_dir=working_dir,
        model=models[0] if models and len(models) > 0 else None,
    )

    session.log(f"Starting Cascade Workflow with fallback strategy: {fallback_strategy}")
    session.log(f"Timeout strategy: {timeout_strategy}")
    session.log(
        f"Timeouts: Primary={timeouts['primary']}s, Secondary={timeouts['secondary']}s, Tertiary={timeouts['tertiary']}s"
    )
    session.log(f"Notification level: {notification_level}")

    # Track attempts
    attempts = []
    cascade_levels = ["primary", "secondary", "tertiary"]

    # Step 1: Define cascade levels
    session.log("Step 1: Defining cascade levels")

    cascade_prompts = {}
    for level in cascade_levels:
        if level in constraints:
            cascade_prompts[level] = f"""You are executing a task with cascading fallback support.

TASK:
{task_prompt}

CASCADE LEVEL: {level.upper()}
CONSTRAINT: {constraints[level]}

IMPORTANT:
- This is the {level.upper()} attempt in a cascade
- You should aim for {constraints[level]}
- Focus on completing within the time constraint
- {"This is the FINAL fallback - you MUST complete successfully" if level == "tertiary" else "If you cannot complete in time, a fallback will be attempted"}

Execute the task now with the {level} approach.
"""

    # Step 2-4: Attempt each level with fallback
    processes = []
    for i, level in enumerate(cascade_levels):
        model = models[i] if models and i < len(models) else None

        process = session.create_process(
            prompt=cascade_prompts[level],
            process_id=f"cascade_{level}",
            model=model,
            timeout=timeouts[level],
        )
        processes.append(process)

    # Use run_with_fallback to try each level
    session.log("Step 2-4: Attempting cascade levels")

    for i, (level, process) in enumerate(zip(cascade_levels, processes, strict=False)):
        session.log(f"Attempting {level.upper()} level (timeout: {timeouts[level]}s)")

        result = process.run()
        attempts.append(result)

        # Check if succeeded
        if result.exit_code == 0:
            session.log(f"{level.upper()} level succeeded!")

            # Determine degradation message
            degradation = None
            if level == "secondary":
                degradation = f"Degraded from primary to secondary: {constraints['secondary']}"
            elif level == "tertiary":
                degradation = f"Degraded to tertiary (minimal): {constraints['tertiary']}"

            # Step 5: Report degradation
            if degradation and notification_level != "silent":
                session.log(f"Degradation: {degradation}", level="WARNING")

                if notification_level == "explicit":
                    # Generate detailed notification
                    notification = f"""
CASCADE DEGRADATION NOTICE

Task attempted with cascade fallback:
{task_prompt[:200]}{"..." if len(task_prompt) > 200 else ""}

Cascade Path:
- Primary: {"TIMEOUT" if attempts[0].exit_code != 0 else "SUCCESS"}
{"- Secondary: " + ("TIMEOUT" if len(attempts) > 1 and attempts[1].exit_code != 0 else "SUCCESS") if len(attempts) > 1 else ""}
{"- Tertiary: SUCCESS" if level == "tertiary" else ""}

Final Level: {level.upper()}
Degradation: {degradation}

What you're getting:
{constraints[level]}

{f"What's missing compared to optimal: {constraints['primary']}" if level != "primary" else ""}
"""
                    session.log(notification)

            session.log(f"Session logs: {session.log_dir}")

            return {
                "result": result,
                "cascade_level": level,
                "degradation": degradation,
                "attempts": attempts,
                "session_id": session.session_id,
                "success": True,
            }

        # Failed, log and continue to next level
        if result.exit_code == -1:
            session.log(
                f"{level.upper()} level timed out after {timeouts[level]}s", level="WARNING"
            )
        else:
            session.log(
                f"{level.upper()} level failed with exit code {result.exit_code}", level="WARNING"
            )

        # Don't continue if this was the last level
        if i == len(cascade_levels) - 1:
            break

        session.log(f"Falling back to {cascade_levels[i + 1].upper()} level...")

    # All levels failed
    session.log("ERROR: All cascade levels failed", level="ERROR")
    session.log(f"Session logs: {session.log_dir}")

    return {
        "result": attempts[-1],  # Return last attempt
        "cascade_level": "failed",
        "degradation": "All cascade levels failed",
        "attempts": attempts,
        "session_id": session.session_id,
        "success": False,
    }


def create_custom_cascade(
    task_prompt: str,
    levels: list[dict[str, Any]],
    working_dir: Path | None = None,
    notification_level: str = "warning",
) -> dict[str, Any]:
    """Create a custom cascade with explicitly defined levels.

    For cases where predefined strategies don't fit, allows full control
    over each cascade level.

    Args:
        task_prompt: The base task prompt
        levels: List of level definitions, each containing:
            - name: str - level name (e.g., "primary", "secondary", "tertiary")
            - timeout: int - timeout in seconds
            - constraint: str - constraint description for this level
            - model: Optional[str] - model to use for this level
        working_dir: Working directory for processes
        notification_level: How to notify ("silent", "warning", "explicit")

    Returns:
        Same structure as run_cascade()

    Example:
        >>> result = create_custom_cascade(
        ...     task_prompt="Analyze code",
        ...     levels=[
        ...         {"name": "comprehensive", "timeout": 60, "constraint": "full analysis with all details"},
        ...         {"name": "quick", "timeout": 10, "constraint": "quick scan for major issues"},
        ...         {"name": "minimal", "timeout": 2, "constraint": "basic syntax check only"},
        ...     ]
        ... )
    """
    # Extract custom configuration
    models = [level.get("model") for level in levels]

    # Build cascade using run_cascade with custom parameters
    working_dir = working_dir or Path.cwd()

    session = OrchestratorSession(
        pattern_name="cascade-custom",
        working_dir=working_dir,
        model=models[0] if models and models[0] else None,
    )

    session.log(f"Starting Custom Cascade with {len(levels)} levels")

    attempts = []

    for i, level_def in enumerate(levels):
        level_name = level_def["name"]
        timeout = level_def["timeout"]
        constraint = level_def["constraint"]
        model = level_def.get("model")

        session.log(f"Attempting {level_name.upper()} level (timeout: {timeout}s)")

        prompt = f"""You are executing a task with cascading fallback support.

TASK:
{task_prompt}

CASCADE LEVEL: {level_name.upper()}
CONSTRAINT: {constraint}

IMPORTANT:
- This is level {i + 1} of {len(levels)} in the cascade
- You should aim for {constraint}
- Focus on completing within the time constraint
- {"This is the FINAL fallback - you MUST complete successfully" if i == len(levels) - 1 else "If you cannot complete in time, a fallback will be attempted"}

Execute the task now with the {level_name} approach.
"""

        process = session.create_process(
            prompt=prompt,
            process_id=f"cascade_{level_name}",
            model=model,
            timeout=timeout,
        )

        result = process.run()
        attempts.append(result)

        # Check if succeeded
        if result.exit_code == 0:
            session.log(f"{level_name.upper()} level succeeded!")

            # Determine degradation
            degradation = None
            if i > 0:
                degradation = f"Degraded to level {i + 1} ({level_name}): {constraint}"

            if degradation and notification_level != "silent":
                session.log(f"Degradation: {degradation}", level="WARNING")

            session.log(f"Session logs: {session.log_dir}")

            return {
                "result": result,
                "cascade_level": level_name,
                "degradation": degradation,
                "attempts": attempts,
                "session_id": session.session_id,
                "success": True,
            }

        # Failed, log and continue
        if result.exit_code == -1:
            session.log(f"{level_name.upper()} timed out after {timeout}s", level="WARNING")
        else:
            session.log(
                f"{level_name.upper()} failed with exit code {result.exit_code}", level="WARNING"
            )

        if i < len(levels) - 1:
            session.log(f"Falling back to {levels[i + 1]['name'].upper()} level...")

    # All failed
    session.log("ERROR: All cascade levels failed", level="ERROR")
    session.log(f"Session logs: {session.log_dir}")

    return {
        "result": attempts[-1],
        "cascade_level": "failed",
        "degradation": "All cascade levels failed",
        "attempts": attempts,
        "session_id": session.session_id,
        "success": False,
    }
