"""Execution tier cascade for workflow execution.

Implements 3-tier fallback chain:
1. Recipe Runner (Tier 1) - Code-enforced workflow execution
2. Workflow Skills (Tier 2) - LLM-driven with recipe files as prompts
3. Markdown Workflow (Tier 3) - Direct markdown reading (always available)
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def import_recipe_runner():
    """Try to import recipe runner."""
    try:
        from amplihack.recipes import run_recipe_by_name

        return run_recipe_by_name
    except ImportError:
        raise ImportError("Recipe Runner not available")


def import_workflow_skills():
    """Try to import workflow skills.

    Tier 2: LLM-driven workflow execution with recipe files as prompts.

    This tier is a future enhancement for when we want to use Claude directly
    (via Skills API) to execute workflows with recipe files as context.
    It provides a fallback when Recipe Runner is unavailable.

    Currently not implemented as Tier 1 (Recipe Runner) covers the primary use case.
    Will be implemented when we need to:
    - Execute workflows on systems without Recipe Runner installed
    - Use LLM-driven workflow orchestration with recipe files as prompts
    - Support alternative execution strategies beyond code-enforced runners

    Raises:
        ImportError: Always raised as Tier 2 is not yet implemented.
    """
    raise ImportError(
        "Workflow Skills (Tier 2) not yet implemented. "
        "Use Tier 1 (Recipe Runner) or Tier 3 (Markdown) instead."
    )


class ExecutionTierCascade:
    """Manages workflow execution across 3 tiers with fallback."""

    # Workflow to recipe name mapping
    WORKFLOW_RECIPE_MAP = {
        "DEFAULT_WORKFLOW": "default-workflow",
        "INVESTIGATION_WORKFLOW": "investigation-workflow",
        "Q&A_WORKFLOW": None,  # Q&A doesn't use recipes
        "OPS_WORKFLOW": None,  # OPS doesn't use recipes
    }

    def __init__(
        self,
        recipe_runner=None,
        workflow_skill=None,
        tier_priority: list | None = None,
    ):
        """Initialize execution tier cascade.

        Args:
            recipe_runner: Optional pre-configured recipe runner instance
            workflow_skill: Optional pre-configured workflow skill instance
            tier_priority: Optional custom tier priority order (default: [1, 2, 3])
        """
        self._recipe_runner = recipe_runner
        self._workflow_skill = workflow_skill
        self._tier_priority = tier_priority or [1, 2, 3]

    def detect_available_tier(self) -> int:
        """Detect highest available tier.

        Returns:
            Tier number (1=Recipe, 2=Skills, 3=Markdown)
        """
        # Check custom tier priority
        for tier in self._tier_priority:
            if tier == 1 and self.is_recipe_runner_available():
                return 1
            if tier == 2 and self.is_workflow_skills_available():
                return 2
            if tier == 3:
                return 3  # Markdown always available

        # Default to tier 3 (markdown)
        return 3

    def is_recipe_runner_available(self) -> bool:
        """Check if Recipe Runner is available and enabled.

        Returns:
            True if Recipe Runner can be used
        """
        # Check environment variable
        if not self.is_recipe_runner_enabled():
            return False

        # Check if recipe runner instance provided
        if self._recipe_runner is not None:
            return True

        # Try to import
        try:
            import_recipe_runner()
            return True
        except ImportError:
            return False

    def is_recipe_runner_enabled(self) -> bool:
        """Check if Recipe Runner is enabled via environment variable.

        Returns:
            True if AMPLIHACK_USE_RECIPES is not explicitly set to "0"
        """
        env_value = os.environ.get("AMPLIHACK_USE_RECIPES", "1")
        return env_value != "0"

    def is_workflow_skills_available(self) -> bool:
        """Check if Workflow Skills are available.

        Returns:
            True if Workflow Skills can be used
        """
        # Check if workflow skill instance provided
        if self._workflow_skill is not None:
            return True

        # Try to import
        try:
            import_workflow_skills()
            return True
        except ImportError:
            return False

    def is_markdown_available(self) -> bool:
        """Check if Markdown workflow is available.

        Markdown is always available as the final fallback.

        Returns:
            Always True
        """
        return True

    def workflow_to_recipe_name(self, workflow: str) -> str | None:
        """Map workflow name to recipe file name.

        Args:
            workflow: Workflow name (e.g., "DEFAULT_WORKFLOW")

        Returns:
            Recipe name (e.g., "default-workflow") or None if no recipe
        """
        return self.WORKFLOW_RECIPE_MAP.get(workflow)

    def execute(self, workflow: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute workflow via highest available tier with fallback.

        Args:
            workflow: Workflow name to execute
            context: Session context

        Returns:
            Dict containing:
                - tier: Tier used (1, 2, or 3)
                - method: Execution method name
                - status: "success" or "failed"
                - execution_time: Time taken in seconds
                - fallback_count: Number of fallbacks attempted
                - fallback_reason: Reason for fallback (if any)

        Raises:
            ValueError: If workflow name is invalid or empty
        """
        start_time = time.time()

        # Validate inputs
        if not workflow or not workflow.strip():
            raise ValueError("Workflow name cannot be empty")
        if workflow not in self.WORKFLOW_RECIPE_MAP:
            raise ValueError(f"Invalid workflow: {workflow}")

        # Ensure context exists
        if context is None:
            context = {}

        # Try execution with fallback
        fallback_count = 0
        last_error = None

        # Try Tier 1: Recipe Runner
        if self.is_recipe_runner_available():
            try:
                result = self._execute_tier1(workflow, context)
                result["execution_time"] = time.time() - start_time
                result["fallback_count"] = fallback_count
                logger.info(f"Workflow executed via tier {result['tier']} ({result['method']})")
                return result
            except Exception as e:
                logger.warning(f"Tier 1 (Recipe Runner) failed, attempting fallback: {e}")
                last_error = str(e)
                fallback_count += 1

        # Try Tier 2: Workflow Skills
        if self.is_workflow_skills_available():
            try:
                result = self._execute_tier2(workflow, context)
                result["execution_time"] = time.time() - start_time
                result["fallback_count"] = fallback_count
                result["fallback_reason"] = f"Tier 1 failed: {last_error}"
                logger.info(
                    f"Workflow executed via tier {result['tier']} ({result['method']}) after fallback"
                )
                return result
            except Exception as e:
                logger.warning(f"Tier 2 (Workflow Skills) failed, attempting fallback: {e}")
                last_error = str(e)
                fallback_count += 1

        # Tier 3: Markdown (always available)
        try:
            result = self._execute_tier3(workflow, context)
            result["execution_time"] = time.time() - start_time
            result["fallback_count"] = fallback_count
            if fallback_count > 0:
                result["fallback_reason"] = f"Previous tiers failed: {last_error}"
                logger.info(
                    f"Workflow executed via tier {result['tier']} ({result['method']}) after {fallback_count} fallback(s)"
                )
            else:
                logger.info(f"Workflow executed via tier {result['tier']} ({result['method']})")
            return result
        except Exception as e:
            logger.error(f"All tiers failed, including Tier 3 (Markdown): {e}")
            raise

    def _execute_tier1(self, workflow: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute via Tier 1: Recipe Runner.

        Args:
            workflow: Workflow name
            context: Session context

        Returns:
            Execution result dict

        Note:
            This method requires a recipe runner instance. Pass a configured
            recipe runner instance to __init__. This can be a real RecipeRunner
            with adapter, or a mock for testing.
        """
        recipe_name = self.workflow_to_recipe_name(workflow)

        # Q&A and OPS don't use recipes
        if recipe_name is None:
            raise ValueError(f"{workflow} does not have a recipe")

        # Must have recipe runner instance
        if self._recipe_runner is None:
            raise ValueError(
                "Recipe Runner not available. "
                "Pass a configured recipe runner instance to ExecutionTierCascade.__init__"
            )

        # Execute recipe via the runner instance
        # The runner's run_recipe_by_name method accepts context as either:
        # - context= (for mock compatibility in tests)
        # - user_context= (for real RecipeRunner)
        # Since this is already an instance (not the raw function), it handles both
        self._recipe_runner.run_recipe_by_name(recipe_name, context=context)

        return {
            "tier": 1,
            "method": "recipe_runner",
            "status": "success",
            "workflow": workflow,
            "recipe": recipe_name,
        }

    def _execute_tier2(self, workflow: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute via Tier 2: Workflow Skills.

        Args:
            workflow: Workflow name
            context: Session context

        Returns:
            Execution result dict
        """
        # Get or create workflow skill
        if self._workflow_skill is None:
            raise ImportError("Workflow Skills not available")

        # Execute workflow skill
        self._workflow_skill.execute(workflow, context)

        return {
            "tier": 2,
            "method": "workflow_skills",
            "status": "success",
            "workflow": workflow,
        }

    def _execute_tier3(self, workflow: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute via Tier 3: Markdown.

        This is the fallback method that always works.
        It returns success and lets Claude read the markdown workflow file.

        Args:
            workflow: Workflow name
            context: Session context

        Returns:
            Execution result dict
        """
        # Tier 3 always succeeds - Claude reads markdown directly
        return {
            "tier": 3,
            "method": "markdown",
            "status": "success",
            "workflow": workflow,
            "context": context,
        }
