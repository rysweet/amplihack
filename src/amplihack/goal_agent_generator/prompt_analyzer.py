"""
Prompt Analyzer - Extract goals, domain, and constraints from natural language.

Analyzes prompt.md files to extract structured goal definitions.
"""

import re
from pathlib import Path
from typing import Literal

from .models import GoalDefinition


class PromptAnalyzer:
    """Analyze natural language prompts to extract goal definitions."""

    # Domain keywords for classification
    DOMAIN_KEYWORDS = {
        "data-processing": ["data", "process", "transform", "analyze", "parse", "extract"],
        "security-analysis": ["security", "vulnerab", "audit", "scan", "threat", "exploit"],
        "automation": ["automate", "schedule", "workflow", "trigger", "monitor"],
        "testing": ["test", "validate", "verify", "check", "qa", "quality"],
        "deployment": ["deploy", "release", "ship", "publish", "distribute"],
        "monitoring": ["monitor", "alert", "track", "observe", "log"],
        "integration": ["integrate", "connect", "api", "webhook", "sync"],
        "reporting": ["report", "dashboard", "metric", "visualize", "summary"],
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "simple": ["single", "one", "simple", "basic", "quick"],
        "moderate": ["multiple", "several", "coordinate", "orchestrate"],
        "complex": ["complex", "distributed", "multi-stage", "advanced", "sophisticated"],
    }

    def analyze(self, prompt_path: Path) -> GoalDefinition:
        """
        Analyze a prompt file and extract goal definition.

        Args:
            prompt_path: Path to prompt.md file

        Returns:
            GoalDefinition with extracted information

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt cannot be analyzed
        """
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        raw_prompt = prompt_path.read_text()
        return self.analyze_text(raw_prompt)

    def analyze_text(self, prompt: str) -> GoalDefinition:
        """
        Analyze prompt text directly.

        Args:
            prompt: Natural language prompt text

        Returns:
            GoalDefinition with extracted information
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Extract primary goal (first sentence or heading)
        goal = self._extract_goal(prompt)

        # Classify domain
        domain = self._classify_domain(prompt)

        # Extract constraints
        constraints = self._extract_constraints(prompt)

        # Extract success criteria
        success_criteria = self._extract_success_criteria(prompt)

        # Determine complexity
        complexity = self._determine_complexity(prompt)

        # Extract additional context
        context = self._extract_context(prompt)

        return GoalDefinition(
            raw_prompt=prompt,
            goal=goal,
            domain=domain,
            constraints=constraints,
            success_criteria=success_criteria,
            complexity=complexity,
            context=context,
        )

    def _extract_goal(self, prompt: str) -> str:
        """Extract the primary goal from prompt."""
        # Look for explicit goal markers
        goal_patterns = [
            r"(?i)(?:goal|objective|aim|purpose):\s*(.+?)(?:\n|$)",
            r"(?i)^#\s+(.+?)$",  # Markdown heading
            r"^(.+?)[.!?]",  # First sentence
        ]

        for pattern in goal_patterns:
            match = re.search(pattern, prompt, re.MULTILINE)
            if match:
                goal = match.group(1).strip()
                if len(goal) > 10:  # Reasonable goal length
                    return goal

        # Fallback: first non-empty line
        lines = [line.strip() for line in prompt.split("\n") if line.strip()]
        return lines[0] if lines else prompt[:100]

    def _classify_domain(self, prompt: str) -> str:
        """Classify the domain based on keywords."""
        prompt_lower = prompt.lower()
        domain_scores = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            if score > 0:
                domain_scores[domain] = score

        if not domain_scores:
            return "general"

        # Return domain with highest score
        return max(domain_scores.items(), key=lambda x: x[1])[0]

    def _extract_constraints(self, prompt: str) -> list[str]:
        """Extract technical or operational constraints."""
        constraints = []

        # Look for constraint markers
        constraint_patterns = [
            r"(?i)(?:constraint|requirement|must|requirement):\s*(.+?)(?:\n|$)",
            r"(?i)(?:should not|cannot|must not|don't)\s+(.+?)(?:\n|$)",
            r"(?i)(?:within|under|less than)\s+(\d+\s*(?:minutes?|hours?|days?))",
        ]

        for pattern in constraint_patterns:
            matches = re.finditer(pattern, prompt, re.MULTILINE)
            for match in matches:
                constraint = match.group(1).strip()
                if constraint and len(constraint) > 5:
                    constraints.append(constraint)

        return constraints[:5]  # Limit to top 5 constraints

    def _extract_success_criteria(self, prompt: str) -> list[str]:
        """Extract success criteria or completion indicators."""
        criteria = []

        # Look for success/completion markers
        criteria_patterns = [
            r"(?i)(?:success|complete|done|finished)\s+(?:when|if|criteria):\s*(.+?)(?:\n|$)",
            r"(?i)(?:should|must|will)\s+(?:result in|produce|generate|create)\s+(.+?)(?:\n|$)",
            r"(?i)(?:output|result|outcome):\s*(.+?)(?:\n|$)",
        ]

        for pattern in criteria_patterns:
            matches = re.finditer(pattern, prompt, re.MULTILINE)
            for match in matches:
                criterion = match.group(1).strip()
                if criterion and len(criterion) > 5:
                    criteria.append(criterion)

        # If no explicit criteria, infer from goal
        if not criteria:
            criteria.append(f"Goal '{self._extract_goal(prompt)[:50]}...' is achieved")

        return criteria[:5]  # Limit to top 5 criteria

    def _determine_complexity(self, prompt: str) -> Literal["simple", "moderate", "complex"]:
        """Determine complexity level based on indicators."""
        prompt_lower = prompt.lower()
        complexity_scores = {"simple": 0, "moderate": 0, "complex": 0}

        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            score = sum(1 for indicator in indicators if indicator in prompt_lower)
            complexity_scores[level] = score

        # Additional heuristics
        word_count = len(prompt_lower.split())
        if word_count < 50:
            complexity_scores["simple"] += 2
        elif word_count < 150:
            complexity_scores["moderate"] += 2
        else:
            complexity_scores["complex"] += 2

        # Check for multiple phases/steps
        if re.search(r"(?i)\b(?:step|phase|stage)\s+\d", prompt):
            complexity_scores["complex"] += 1

        # Return highest scoring complexity
        max_score = max(complexity_scores.values())
        if max_score == 0:
            return "moderate"  # Default

        result = max(complexity_scores.items(), key=lambda x: x[1])[0]
        # Type assertion for return type safety
        return result  # type: ignore[return-value]

    def _extract_context(self, prompt: str) -> dict:
        """Extract additional contextual information."""
        context = {}

        # Extract timeframes
        time_match = re.search(
            r"(?i)(?:within|in|under)\s+(\d+)\s*(minute|hour|day|week)s?", prompt
        )
        if time_match:
            context["timeframe"] = f"{time_match.group(1)} {time_match.group(2)}s"

        # Extract priorities
        if re.search(r"(?i)\b(?:urgent|asap|immediately|critical)\b", prompt):
            context["priority"] = "high"
        elif re.search(r"(?i)\b(?:when possible|eventually|someday)\b", prompt):
            context["priority"] = "low"
        else:
            context["priority"] = "normal"

        # Extract scale/scope
        if re.search(r"(?i)\b(?:large|massive|enterprise|production)\b", prompt):
            context["scale"] = "large"
        elif re.search(r"(?i)\b(?:small|tiny|minimal|simple)\b", prompt):
            context["scale"] = "small"
        else:
            context["scale"] = "medium"

        return context
