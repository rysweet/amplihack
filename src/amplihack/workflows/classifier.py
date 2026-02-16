"""Workflow classifier for routing requests to appropriate workflows.

Classifies user requests into 4 workflows:
- Q&A_WORKFLOW: Simple questions, single-turn answers
- OPS_WORKFLOW: Operations, commands, admin tasks
- INVESTIGATION_WORKFLOW: Code understanding, research
- DEFAULT_WORKFLOW: Development tasks, features, bugs
"""

from typing import Any


class WorkflowClassifier:
    """Classifies user requests into appropriate workflows."""

    # Keyword mappings for each workflow type
    DEFAULT_KEYWORD_MAP = {
        "Q&A_WORKFLOW": [
            "what is",
            "explain briefly",
            "quick question",
            "how do i run",
            "what does",
            "can you explain",
        ],
        "OPS_WORKFLOW": [
            "run command",
            "disk cleanup",
            "repo management",
            "git operations",
            "delete files",
            "cleanup",
            "organize",
            "clean up",
            "manage",
        ],
        "INVESTIGATION_WORKFLOW": [
            "investigate",
            "understand",
            "analyze",
            "research",
            "explore",
            "how does",
            "how it works",
        ],
        "DEFAULT_WORKFLOW": [
            "implement",
            "add",
            "fix",
            "create",
            "refactor",
            "update",
            "build",
            "develop",
            "remove",
            "delete",
            "modify",
        ],
    }

    def __init__(self, custom_keywords: dict[str, list[str]] | None = None):
        """Initialize workflow classifier.

        Args:
            custom_keywords: Optional custom keyword mappings to extend or override defaults
        """
        self._keyword_map = self.DEFAULT_KEYWORD_MAP.copy()
        if custom_keywords:
            for workflow, keywords in custom_keywords.items():
                if workflow in self._keyword_map:
                    self._keyword_map[workflow].extend(keywords)
                else:
                    self._keyword_map[workflow] = keywords

    def classify(self, request: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Classify a user request into appropriate workflow.

        Args:
            request: The user's request text
            context: Optional session context (session_id, is_first_message, etc.)

        Returns:
            Dict containing:
                - workflow: The classified workflow name
                - reason: Explanation of why this workflow was chosen
                - confidence: Confidence score (0.0 to 1.0)
                - keywords: List of matched keywords
                - context: Session context if provided

        Raises:
            ValueError: If request is empty
            TypeError: If request is not a string
        """
        # Input validation
        if request is None:
            raise TypeError("Request cannot be None")
        if not isinstance(request, str):
            raise TypeError(f"Request must be a string, got {type(request)}")
        if not request or not request.strip():
            raise ValueError("Request cannot be empty")

        # Extract keywords from request
        keywords = self._extract_keywords(request)

        # Classify based on keywords
        workflow, reason, confidence = self._classify_by_keywords(keywords, request)

        # Build result
        result = {
            "workflow": workflow,
            "reason": reason,
            "confidence": confidence,
            "keywords": keywords,
        }

        # Include context if provided
        if context:
            result["context"] = context

        return result

    def _extract_keywords(self, request: str) -> list[str]:
        """Extract classification keywords from request.

        Args:
            request: The user's request text

        Returns:
            List of matched keywords (case-insensitive)
        """
        request_lower = request.lower()
        matched_keywords = []

        # Check all keyword patterns
        for workflow_type, keywords in self._keyword_map.items():
            for keyword in keywords:
                if keyword in request_lower:
                    matched_keywords.append(keyword)

        return matched_keywords

    def _classify_by_keywords(self, keywords: list[str], request: str) -> tuple[str, str, float]:
        """Classify request based on matched keywords.

        Priority order: DEFAULT > INVESTIGATION > OPS > Q&A
        This ensures development tasks take precedence over other workflows.

        Args:
            keywords: List of matched keywords
            request: Original request text

        Returns:
            Tuple of (workflow_name, reason, confidence)
        """
        # Priority order for workflows
        workflow_priority = [
            "DEFAULT_WORKFLOW",
            "INVESTIGATION_WORKFLOW",
            "OPS_WORKFLOW",
            "Q&A_WORKFLOW",
        ]

        # Find first workflow with matching keywords
        for workflow in workflow_priority:
            workflow_keywords = self._keyword_map[workflow]
            matched = [kw for kw in keywords if kw in workflow_keywords]
            if matched:
                # High confidence for clear keyword match
                confidence = 0.9 if len(matched) >= 1 else 0.7
                reason = f"keyword '{matched[0]}'"
                return workflow, reason, confidence

        # No keywords matched - default to DEFAULT_WORKFLOW with low confidence
        return "DEFAULT_WORKFLOW", "ambiguous request, defaulting to default workflow", 0.5

    def format_announcement(
        self, result: dict[str, Any], recipe_runner_available: bool = False
    ) -> str:
        """Format classification announcement for user.

        Args:
            result: Classification result from classify()
            recipe_runner_available: Whether Recipe Runner is available

        Returns:
            Formatted announcement string
        """
        workflow = result["workflow"]
        reason = result["reason"]

        # Shorten workflow name for display
        display_name = workflow.replace("_WORKFLOW", "")

        announcement = f"""WORKFLOW: {display_name}
Reason: {reason}
Following: .claude/workflow/{workflow}.md"""

        # Add Recipe Runner info if available
        if recipe_runner_available and workflow in ["DEFAULT_WORKFLOW", "INVESTIGATION_WORKFLOW"]:
            recipe_name = workflow.lower().replace("_", "-")
            announcement += f"\nExecution: Recipe Runner (tier 1) - {recipe_name}"

        return announcement
