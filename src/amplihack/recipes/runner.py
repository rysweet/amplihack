"""Recipe execution engine.

Runs a parsed Recipe step-by-step through an SDK adapter, managing context
accumulation, conditional execution, template rendering, and fail-fast behavior.

Supports auto-staging of git changes after agent steps to prevent work loss
when subsequent steps fail or sessions crash.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.context import RecipeContext
from amplihack.recipes.discovery import find_recipe
from amplihack.recipes.models import (
    Recipe,
    RecipeResult,
    Step,
    StepExecutionError,
    StepResult,
    StepStatus,
    StepType,
)

MAX_RECIPE_DEPTH = 3

logger = logging.getLogger(__name__)


def _git_stage_all(working_dir: str) -> str | None:
    """Run ``git add -A`` in the given directory.

    Returns:
        A summary string on success, or None if git is not available or the
        directory is not a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Check what was staged
            diff_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            staged_files = diff_result.stdout.strip()
            if staged_files:
                return staged_files
            return None
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


class RecipeRunner:
    """Executes recipes by delegating steps to an SDK adapter.

    The execution loop:
    1. Merges recipe context with optional user context.
    2. For each step: evaluate condition, render templates, execute via adapter.
    3. Stores step output in context for subsequent steps.
    4. After successful agent steps, auto-stages git changes (if enabled).
    5. Stops on first failure (fail-fast).

    Args:
        adapter: An object implementing the SDKAdapter protocol.
        agent_resolver: Optional AgentResolver for looking up agent system prompts.
        working_dir: Default working directory for step execution.
        dry_run: If True, skip actual execution (log only).
        auto_stage: If True (default), run ``git add -A`` after successful agent
            steps to prevent work loss. Individual steps can override via their
            ``auto_stage`` field.
    """

    def __init__(
        self,
        adapter: Any = None,
        agent_resolver: AgentResolver | None = None,
        working_dir: str = ".",
        dry_run: bool = False,
        auto_stage: bool = True,
        _depth: int = 0,
    ) -> None:
        self._adapter = adapter
        self._agent_resolver = agent_resolver or AgentResolver()
        self._working_dir = working_dir
        self._default_dry_run = dry_run
        self._auto_stage = auto_stage
        self._depth = _depth

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

        # Dry run -- skip condition evaluation (no real data to evaluate against)
        # and record step as completed
        if dry_run:
            logger.info("DRY RUN: would execute step '%s'", step.id)

            # For parse_json steps, return valid mock JSON
            if step.parse_json:
                mock_output = json.dumps({"dry_run": True, "step": step.id, "mock_data": {}})
            else:
                mock_output = "[dry run]"

            return StepResult(
                step_id=step.id,
                status=StepStatus.COMPLETED,
                output=mock_output,
            )

        # Evaluate condition -- skip if false, FAIL if condition itself errors
        if step.condition:
            try:
                if not ctx.evaluate(step.condition):
                    logger.info("Skipping step '%s': condition is false", step.id)
                    return StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                    )
            except Exception as exc:
                logger.error(
                    "Condition evaluation FAILED for step '%s': %s. "
                    "This usually means a prior parse_json step returned invalid JSON. "
                    "Fix the upstream step or the condition expression.",
                    step.id,
                    exc,
                )
                return StepResult(
                    step_id=step.id,
                    status=StepStatus.FAILED,
                    error=f"Condition error: {exc}",
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

        # Optionally parse JSON output -- retry once then FAIL
        if step.parse_json and output:
            parsed = self._parse_json_output(output, step.id)
            if parsed is not None:
                output = parsed
            else:
                # Retry: re-execute with explicit JSON instruction
                logger.warning(
                    "Step '%s': parse_json failed on first attempt. Retrying with JSON reminder.",
                    step.id,
                )
                retry_output = self._retry_for_json(step, ctx)
                if retry_output is not None:
                    parsed = self._parse_json_output(retry_output, step.id)
                    if parsed is not None:
                        output = parsed
                        logger.info("Step '%s': parse_json succeeded on retry.", step.id)
                    else:
                        logger.error(
                            "Step '%s': parse_json failed on retry. "
                            "Raw output (first 200 chars): %s",
                            step.id,
                            str(retry_output)[:200],
                        )
                        return StepResult(
                            step_id=step.id,
                            status=StepStatus.FAILED,
                            error="parse_json failed after retry: output is not valid JSON",
                        )
                else:
                    logger.error(
                        "Step '%s': parse_json failed and retry not possible. "
                        "Raw output (first 200 chars): %s",
                        step.id,
                        str(output)[:200],
                    )
                    return StepResult(
                        step_id=step.id,
                        status=StepStatus.FAILED,
                        error="parse_json failed: output is not valid JSON",
                    )

        # Store output in context
        if step.output:
            ctx.set(step.output, output)

        # Auto-stage git changes after successful agent steps to prevent work loss
        if step.step_type == StepType.AGENT:
            self._maybe_auto_stage(step, ctx)

        return StepResult(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            output=json.dumps(output)
            if isinstance(output, (dict, list))
            else (str(output) if output else ""),
        )

    def _maybe_auto_stage(self, step: Step, ctx: RecipeContext) -> None:
        """Auto-stage git changes if enabled for this step.

        The step's ``auto_stage`` field takes precedence over the runner default.
        If staging occurs, a log message is emitted with the staged file list.
        """
        # Determine whether to stage: step override > runner default
        should_stage = step.auto_stage if step.auto_stage is not None else self._auto_stage
        if not should_stage:
            return

        working_dir = step.working_dir or self._working_dir
        staged_files = _git_stage_all(working_dir)
        if staged_files:
            file_count = len(staged_files.splitlines())
            logger.info(
                "Auto-staged %d file(s) after step '%s': %s",
                file_count,
                step.id,
                staged_files,
            )

    def _retry_for_json(self, step: Step, ctx: RecipeContext) -> str | None:
        """Retry an agent step with an explicit JSON-only instruction.

        Only works for agent steps (not bash). Appends a reminder to return
        ONLY valid JSON to the original prompt and re-executes.

        Returns the raw output string from the retry, or None if retry
        is not applicable (bash steps) or fails.
        """
        if step.step_type != StepType.AGENT:
            return None  # Can't retry bash steps with different prompts

        original_prompt = step.prompt or ""
        retry_prompt = (
            original_prompt + "\n\nIMPORTANT: Your previous response was not valid JSON. "
            "Return ONLY a valid JSON object. No markdown fences, no explanation, "
            "no text before or after. Just the raw JSON object starting with { and ending with }."
        )

        working_dir = step.working_dir or self._working_dir
        try:
            return self._adapter.execute_agent_step(
                prompt=ctx.render(retry_prompt),
                working_dir=working_dir,
            )
        except Exception as exc:
            logger.warning("Retry for step '%s' failed: %s", step.id, exc)
            return None

    @staticmethod
    def _parse_json_output(output: str, step_id: str) -> dict | list | None:
        """Try to parse JSON from LLM output using multiple strategies.

        Strategy 1: Direct json.loads
        Strategy 2: Extract from markdown fences (```json ... ```)
        Strategy 3: Find first { ... } or [ ... ] block

        Returns parsed object or None if all strategies fail.
        """
        import re

        text = output.strip()

        # Strategy 1: Direct parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Strategy 2: Extract from markdown fences
        fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                pass

        # Strategy 3: Find first balanced JSON object or array via counting
        for open_ch, close_ch in [("{", "}"), ("[", "]")]:
            start = text.find(open_ch)
            if start == -1:
                continue
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except (json.JSONDecodeError, TypeError):
                            break  # Try next delimiter type
            # If we exit without finding balanced braces, try next type

        logger.warning("All JSON extraction strategies failed for step '%s'", step_id)
        return None

    def _execute_sub_recipe(self, step: Step, ctx: RecipeContext) -> str:
        """Execute a sub-recipe step with context merging and recursion depth guard.

        On failure, an agent recovery step is invoked to assess whether the
        failure is recoverable and attempt to complete the work.  If recovery
        succeeds the recovery output is returned.  If recovery fails or
        reports the failure as unrecoverable, a StepExecutionError is raised
        that includes both the original and recovery context.

        Raises:
            StepExecutionError: If recursion depth exceeds MAX_RECIPE_DEPTH,
                the sub-recipe name is missing/not found, or both the
                sub-recipe and the recovery agent fail.
        """
        from amplihack.recipes.parser import RecipeParser

        if self._depth >= MAX_RECIPE_DEPTH:
            raise StepExecutionError(
                step.id,
                f"Maximum recipe recursion depth ({MAX_RECIPE_DEPTH}) exceeded. "
                "Check for circular recipe references.",
            )

        recipe_name = step.recipe
        if not recipe_name:
            raise StepExecutionError(step.id, "Recipe step is missing the 'recipe' field")

        path = find_recipe(recipe_name)
        if path is None:
            raise StepExecutionError(step.id, f"Sub-recipe '{recipe_name}' not found")

        sub_recipe = RecipeParser().parse_file(path)

        # Merge: current context + step-level sub_context overrides
        merged: dict[str, Any] = dict(ctx.to_dict())
        if step.sub_context:
            merged.update(step.sub_context)

        sub_runner = RecipeRunner(
            adapter=self._adapter,
            agent_resolver=self._agent_resolver,
            working_dir=self._working_dir,
            dry_run=self._default_dry_run,
            auto_stage=self._auto_stage,
            _depth=self._depth + 1,
        )
        sub_result = sub_runner.execute(sub_recipe, user_context=merged)

        if not sub_result.success:
            original_error = f"Sub-recipe '{recipe_name}' failed"

            # Collect failure context from the sub-recipe result
            failed_steps = [
                sr for sr in sub_result.step_results if sr.status == StepStatus.FAILED
            ]
            failed_step_names = ", ".join(sr.step_id for sr in failed_steps)
            partial_outputs = sub_result.output[:500] if sub_result.output else ""
            if sub_result.output and len(sub_result.output) > 500:
                partial_outputs += "... (truncated)"

            logger.warning(
                "Sub-recipe '%s' failed (step '%s'). Attempting agent recovery.",
                recipe_name,
                failed_step_names or "unknown",
            )

            recovery_result = self._attempt_agent_recovery(
                step=step,
                ctx=ctx,
                sub_recipe_name=recipe_name,
                error_message=original_error,
                failed_step_names=failed_step_names,
                partial_outputs=partial_outputs,
            )

            if recovery_result is not None:
                logger.info(
                    "Agent recovery succeeded for sub-recipe '%s' (step '%s')",
                    recipe_name,
                    step.id,
                )
                return recovery_result

            # Recovery failed or reported unrecoverable — raise with full context
            raise StepExecutionError(
                step.id,
                f"{original_error}. Failed steps: [{failed_step_names}]. "
                "Agent recovery also failed or reported unrecoverable.",
            )

        logger.info(
            "Sub-recipe '%s' completed successfully (depth %d)",
            recipe_name,
            self._depth + 1,
        )
        return str(sub_result)

    def _attempt_agent_recovery(
        self,
        step: Step,
        ctx: RecipeContext,
        sub_recipe_name: str,
        error_message: str,
        failed_step_names: str,
        partial_outputs: str,
    ) -> str | None:
        """Invoke an agent to assess and attempt recovery after a sub-recipe failure.

        Builds a recovery prompt that includes failure context and partial
        outputs, then dispatches to the adapter's execute_agent_step.  Returns
        the agent's output string on success, or None if the recovery agent
        cannot be invoked, raises an exception, or its response signals that
        the failure is unrecoverable.

        A response is considered unrecoverable when the agent explicitly
        includes the token ``UNRECOVERABLE`` (case-insensitive) in its reply.
        """
        if self._adapter is None:
            logger.warning("Cannot attempt agent recovery: no adapter configured")
            return None

        recovery_prompt = (
            f"A sub-recipe execution failed and requires your assessment.\n\n"
            f"Sub-recipe: {sub_recipe_name}\n"
            f"Failed steps: {failed_step_names or 'unknown'}\n"
            f"Error: {error_message}\n"
            f"Partial outputs (first 500 chars):\n{partial_outputs}\n\n"
            "Please assess whether this failure is recoverable:\n"
            "1. If you can complete the work that the sub-recipe was supposed to do, "
            "do so now and provide the result.\n"
            "2. If the failure is not recoverable (missing prerequisites, "
            "unresolvable conflicts, etc.), respond with 'UNRECOVERABLE: <reason>'.\n\n"
            "Current context summary:\n"
            f"{self._summarise_context(ctx)}"
        )

        working_dir = step.working_dir or self._working_dir

        try:
            recovery_output = self._adapter.execute_agent_step(
                prompt=recovery_prompt,
                working_dir=working_dir,
            )
        except Exception as exc:
            logger.warning(
                "Agent recovery invocation failed for sub-recipe '%s': %s",
                sub_recipe_name,
                exc,
            )
            return None

        if not recovery_output:
            logger.warning(
                "Agent recovery returned empty output for sub-recipe '%s'",
                sub_recipe_name,
            )
            return None

        if "UNRECOVERABLE" in recovery_output.upper():
            logger.warning(
                "Agent recovery reported unrecoverable failure for sub-recipe '%s': %s",
                sub_recipe_name,
                recovery_output[:200],
            )
            return None

        return recovery_output

    _SENSITIVE_KEY_PATTERNS = frozenset({"token", "secret", "password", "key"})

    @classmethod
    def _summarise_context(cls, ctx: RecipeContext) -> str:
        """Return a short human-readable summary of context keys and value previews.

        Keys whose names contain sensitive patterns (token, secret, password, key)
        are redacted to avoid leaking credentials into recovery prompts.
        """
        items = ctx.to_dict()
        lines = []
        for key, value in list(items.items())[:20]:  # cap at 20 keys
            key_lower = key.lower()
            if any(pat in key_lower for pat in cls._SENSITIVE_KEY_PATTERNS):
                lines.append(f"  {key}: [REDACTED]")
            else:
                preview = str(value)[:80].replace("\n", " ")
                lines.append(f"  {key}: {preview}")
        return "\n".join(lines) if lines else "  (empty)"

    def _dispatch_step(self, step: Step, ctx: RecipeContext) -> str:
        """Route step execution to the correct adapter method."""
        working_dir = step.working_dir or self._working_dir

        if step.step_type == StepType.RECIPE:
            return self._execute_sub_recipe(step, ctx)

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
