"""Recipe execution engine.

Runs a parsed Recipe step-by-step through an SDK adapter, managing context
accumulation, conditional execution, template rendering, and fail-fast behavior.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.context import RecipeContext
from amplihack.recipes.models import (
    Recipe,
    RecipeResult,
    Step,
    StepExecutionError,
    StepResult,
    StepStatus,
    StepType,
)

logger = logging.getLogger(__name__)


class RecipeRunner:
    """Executes recipes by delegating steps to an SDK adapter.

    The execution loop:
    1. Merges recipe context with optional user context.
    2. For each step: evaluate condition, render templates, execute via adapter.
    3. Stores step output in context for subsequent steps.
    4. Stops on first failure (fail-fast).

    Args:
        adapter: An object implementing the SDKAdapter protocol.
        agent_resolver: Optional AgentResolver for looking up agent system prompts.
        working_dir: Default working directory for step execution.
        dry_run: If True, skip actual execution (log only).
    """

    def __init__(
        self,
        adapter: Any = None,
        agent_resolver: AgentResolver | None = None,
        working_dir: str = ".",
        dry_run: bool = False,
    ) -> None:
        self._adapter = adapter
        self._agent_resolver = agent_resolver or AgentResolver()
        self._working_dir = working_dir
        self._default_dry_run = dry_run

    def execute(
        self,
        recipe: Recipe,
        user_context: dict[str, Any] | None = None,
        dry_run: bool | None = None,
    ) -> RecipeResult:
        """Execute a recipe and return the result.

        Args:
            recipe: A parsed Recipe object.
            user_context: Optional extra context values merged on top of recipe defaults.
            dry_run: Override the instance-level dry_run setting.

        Returns:
            RecipeResult with success status and per-step results.
        """
        is_dry_run = dry_run if dry_run is not None else self._default_dry_run

        if not is_dry_run and self._adapter is None:
            raise ValueError("adapter is required for non-dry-run execution")

        # Build initial context from recipe defaults + user overrides
        initial = dict(recipe.context or {})
        if user_context:
            initial.update(user_context)
        ctx = RecipeContext(initial)

        step_results: list[StepResult] = []
        success = True

        for step in recipe.steps:
            result = self._execute_step(step, ctx, is_dry_run)
            step_results.append(result)

            if result.status == StepStatus.FAILED:
                success = False
                break

        return RecipeResult(
            recipe_name=recipe.name,
            success=success,
            step_results=step_results,
            context=ctx.to_dict(),
        )

    def _execute_step(self, step: Step, ctx: RecipeContext, dry_run: bool) -> StepResult:
        """Execute a single step, handling conditions, templates, and errors."""

        # Evaluate condition -- skip if false
        if step.condition:
            try:
                if not ctx.evaluate(step.condition):
                    logger.info("Skipping step '%s': condition is false", step.id)
                    return StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                    )
            except (ValueError, NameError) as exc:
                logger.warning(
                    "Condition evaluation failed for step '%s', skipping: %s", step.id, exc
                )
                return StepResult(
                    step_id=step.id,
                    status=StepStatus.SKIPPED,
                )

        # Dry run -- record but do not execute
        if dry_run:
            logger.info("DRY RUN: would execute step '%s'", step.id)
            return StepResult(
                step_id=step.id,
                status=StepStatus.COMPLETED,
                output="[dry run]",
            )

        # Execute the step via the adapter
        try:
            output = self._dispatch_step(step, ctx)
        except Exception as exc:
            logger.error("Step '%s' failed: %s", step.id, exc)
            return StepResult(
                step_id=step.id,
                status=StepStatus.FAILED,
                error=str(exc),
            )

        # Optionally parse JSON output
        if step.parse_json and output:
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Step '%s': parse_json is true but output is not valid JSON",
                    step.id,
                )

        # Store output in context
        if step.output:
            ctx.set(step.output, output)

        return StepResult(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            output=json.dumps(output)
            if isinstance(output, (dict, list))
            else (str(output) if output else ""),
        )

    def _dispatch_step(self, step: Step, ctx: RecipeContext) -> str:
        """Route step execution to the correct adapter method."""
        working_dir = step.working_dir or self._working_dir

        if step.step_type == StepType.BASH:
            # Use shell-safe rendering to prevent injection via template values.
            # shlex.quote() wraps each interpolated value so shell metacharacters
            # in step outputs cannot escape the intended argument boundaries.
            rendered_command = ctx.render_shell(step.command or "")
            return self._adapter.execute_bash_step(
                rendered_command,
                working_dir=working_dir,
                timeout=step.timeout,
            )

        if step.step_type == StepType.AGENT:
            rendered_prompt = ctx.render(step.prompt or "")

            # Resolve agent system prompt if agent reference is provided
            agent_name = None
            agent_system_prompt = None
            if step.agent:
                try:
                    agent_name = step.agent
                    agent_system_prompt = self._agent_resolver.resolve(step.agent)
                except (AgentNotFoundError, ValueError):
                    logger.warning(
                        "Could not resolve agent '%s', proceeding without system prompt",
                        step.agent,
                    )

            return self._adapter.execute_agent_step(
                prompt=rendered_prompt,
                agent_name=agent_name,
                agent_system_prompt=agent_system_prompt,
                mode=step.mode,
                working_dir=working_dir,
            )

        raise StepExecutionError(step.id, f"Unknown step type: {step.step_type}")
