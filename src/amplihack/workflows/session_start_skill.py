"""Session start classifier skill.

Integrates classification, execution tier cascade, and session start detection
into a complete workflow orchestration system.
"""

import logging
import time
from typing import Any

from .classifier import WorkflowClassifier
from .execution_tier_cascade import ExecutionTierCascade
from .session_start import SessionStartDetector

logger = logging.getLogger(__name__)


class SessionStartClassifierSkill:
    """Orchestrates session start workflow classification and execution."""

    def __init__(
        self,
        classifier: WorkflowClassifier | None = None,
        cascade: ExecutionTierCascade | None = None,
        detector: SessionStartDetector | None = None,
        recipe_runner=None,
        workflow_skill=None,
    ):
        """Initialize session start classifier skill.

        Args:
            classifier: Optional pre-configured workflow classifier
            cascade: Optional pre-configured execution tier cascade
            detector: Optional pre-configured session start detector
            recipe_runner: Optional recipe runner instance (passed to cascade)
            workflow_skill: Optional workflow skill instance (passed to cascade)
        """
        self._classifier = classifier or WorkflowClassifier()
        self._cascade = cascade or ExecutionTierCascade(
            recipe_runner=recipe_runner,
            workflow_skill=workflow_skill,
        )
        self._detector = detector or SessionStartDetector()

    def process(self, context: dict[str, Any]) -> dict[str, Any]:
        """Process session start: classify → execute → announce.

        Args:
            context: Session context containing:
                - prompt: User's request (or user_request)
                - session_id: Session identifier
                - is_first_message: Whether this is first message
                - is_explicit_command: Whether explicit command was used

        Returns:
            Dict containing:
                - activated: Whether classification was triggered (True/False)
                - should_classify: Whether classification was triggered (synonym)
                - bypassed: Whether classification was bypassed
                - classification: Classification result (if classified)
                - workflow: Classified workflow name (if classified)
                - tier: Execution tier used (if executed)
                - method: Execution method (if executed)
                - status: Execution status (if executed)
                - execution: Full execution result (if executed)
                - announcement: User-facing announcement (if classified)
                - classification_time: Time taken to classify (in seconds)
                - context: Augmented context with classification results
        """
        start_time = time.time()
        result: dict[str, Any] = {
            "activated": False,
            "should_classify": False,
            "bypassed": False,
        }

        # Check if we should bypass classification
        if self._detector.should_bypass_classification(context):
            result["bypassed"] = True
            result["activated"] = False
            # Determine reason for bypass
            user_request = context.get("prompt") or context.get("user_request", "")
            if context.get("is_explicit_command") or (
                user_request and user_request.strip().startswith("/")
            ):
                result["reason"] = "explicit_command"
            else:
                result["reason"] = "follow_up_message"
            return result

        # Check if this is a session start requiring classification
        if not self._detector.is_session_start(context):
            result["activated"] = False
            return result

        # Extract user request (support both 'prompt' and 'user_request')
        user_request = context.get("prompt") or context.get("user_request", "")
        if not user_request:
            logger.warning("No user request provided in context")
            result["activated"] = False
            return result

        # Classify the request
        try:
            classification = self._classifier.classify(user_request, context=context)
            result["activated"] = True
            result["should_classify"] = True
            result["classification"] = classification
            result["workflow"] = classification["workflow"]
            result["reason"] = classification["reason"]  # For convenience
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            result["error"] = str(e)
            result["activated"] = False
            return result

        # Determine if Recipe Runner is available
        recipe_runner_available = self._cascade.is_recipe_runner_available()

        # Format announcement
        announcement = self._classifier.format_announcement(
            classification, recipe_runner_available=recipe_runner_available
        )
        result["announcement"] = announcement

        # Execute workflow via tier cascade (for workflows that have recipes)
        workflow = classification["workflow"]
        if workflow in ["DEFAULT_WORKFLOW", "INVESTIGATION_WORKFLOW"]:
            try:
                execution_result = self._cascade.execute(workflow, context)
                result["execution"] = execution_result
                # Copy execution details to top level for easier access
                result["tier"] = execution_result["tier"]
                result["method"] = execution_result["method"]
                result["status"] = execution_result["status"]
            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                result["execution_error"] = str(e)
        else:
            # Q&A and OPS workflows don't use tier cascade
            # They are handled directly (direct answer or direct execution)
            result["tier"] = None  # Not applicable
            result["method"] = "direct"
            result["status"] = "success"

        # Record classification time
        classification_time = time.time() - start_time
        result["classification_time"] = classification_time

        # Augment context with classification results
        augmented_context = context.copy()
        augmented_context["classification"] = classification
        augmented_context["workflow"] = classification["workflow"]
        augmented_context["classification_time"] = classification_time
        # Add execution tier if available
        if "tier" in result:
            augmented_context["tier"] = result["tier"]
        result["context"] = augmented_context

        return result
