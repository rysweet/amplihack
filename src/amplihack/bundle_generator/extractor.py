"""
Intent extraction module for Agent Bundle Generator.

Extracts structured intent and requirements from parsed prompts.
"""

import logging
import re
from typing import List, Optional

from .exceptions import ExtractionError
from .models import AgentRequirement, ExtractedIntent, ParsedPrompt
from .parser import PromptParser

logger = logging.getLogger(__name__)


class IntentExtractor:
    """
    Extract structured intent and requirements from parsed prompts.

    Converts natural language understanding into actionable agent specifications.
    """

    # Domain mappings
    DOMAIN_KEYWORDS = {
        "security": ["security", "vulnerability", "threat", "audit", "scan", "protect"],
        "data-processing": ["data", "process", "transform", "pipeline", "etl", "convert"],
        "monitoring": ["monitor", "track", "watch", "observe", "alert", "metric"],
        "validation": ["validate", "check", "verify", "test", "ensure", "confirm"],
        "integration": ["integrate", "connect", "api", "webhook", "sync", "bridge"],
        "automation": ["automate", "workflow", "schedule", "trigger", "orchestrate"],
        "analysis": ["analyze", "examine", "investigate", "review", "assess", "evaluate"],
        "generation": ["generate", "create", "produce", "build", "construct", "make"],
    }

    # Agent type mappings
    TYPE_INDICATORS = {
        "core": ["fundamental", "basic", "essential", "primary", "main"],
        "specialized": ["specific", "dedicated", "focused", "specialized", "custom"],
        "workflow": ["workflow", "pipeline", "orchestrate", "coordinate", "sequence"],
    }

    def __init__(self, parser: Optional[PromptParser] = None):
        """
        Initialize the intent extractor.

        Args:
            parser: Optional PromptParser instance to use
        """
        self.parser = parser or PromptParser()

    def extract(self, parsed: ParsedPrompt) -> ExtractedIntent:
        """
        Extract intent and requirements from parsed prompt.

        Args:
            parsed: ParsedPrompt object

        Returns:
            ExtractedIntent with structured requirements

        Raises:
            ExtractionError: If intent cannot be extracted
        """
        try:
            # Determine action
            action = self._determine_action(parsed)

            # Determine domain
            domain = self._determine_domain(parsed)

            # Extract agent requirements
            agent_requirements = self._extract_agent_requirements(parsed)

            # Determine complexity
            complexity = self._determine_complexity(parsed, agent_requirements)

            # Extract constraints
            constraints = self._extract_constraints(parsed)

            # Extract dependencies
            dependencies = self._extract_dependencies(parsed)

            # Calculate confidence
            confidence = self._calculate_confidence(parsed, action, domain, agent_requirements)

            return ExtractedIntent(
                action=action,
                domain=domain,
                agent_count=len(agent_requirements),
                agent_requirements=agent_requirements,
                complexity=complexity,
                constraints=constraints,
                dependencies=dependencies,
                confidence=confidence,
            )

        except Exception as e:
            logger.exception(
                "Failed to extract intent from parsed prompt",
                extra={
                    "prompt_tokens": len(parsed.tokens) if parsed else 0,
                    "prompt_entities": len(parsed.entities) if parsed else 0,
                },
            )
            raise ExtractionError(
                f"Failed to extract intent: {e!s}",
                confidence_score=0.0,
                extraction_stage="intent_extraction",
            )

    def _determine_action(self, parsed: ParsedPrompt) -> str:
        """Determine the primary action requested."""
        tokens = set(parsed.tokens)

        # Check for explicit action keywords
        if any(word in tokens for word in ["create", "generate", "build", "make"]):
            return "create"
        if any(word in tokens for word in ["modify", "update", "change", "edit"]):
            return "modify"
        if any(word in tokens for word in ["combine", "merge", "integrate", "join"]):
            return "combine"
        if any(word in tokens for word in ["specialize", "customize", "adapt", "tailor"]):
            return "specialize"

        # Default to create
        return "create"

    def _determine_domain(self, parsed: ParsedPrompt) -> str:
        """Determine the problem domain."""
        tokens = set(parsed.tokens)
        domain_scores = {}

        # Score each domain based on keyword matches
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in tokens)
            if score > 0:
                domain_scores[domain] = score

        # Return highest scoring domain
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        # Check entities for clues
        if parsed.entities.get("capabilities"):
            capabilities = parsed.entities["capabilities"]
            if any(cap in ["validate", "check", "verify"] for cap in capabilities):
                return "validation"
            if any(cap in ["analyze", "process", "transform"] for cap in capabilities):
                return "data-processing"

        # Default to general data processing
        return "data-processing"

    def _extract_agent_requirements(self, parsed: ParsedPrompt) -> List[AgentRequirement]:
        """Extract individual agent requirements."""
        requirements = []

        # First, try to extract from numbered lists or bullet points
        list_agents = self._extract_from_lists(parsed)
        if list_agents:
            requirements.extend(list_agents)

        # Then, extract from entity mentions
        entity_agents = self._extract_from_entities(parsed)
        if entity_agents:
            requirements.extend(entity_agents)

        # If no agents found, create a default one
        if not requirements:
            requirements.append(self._create_default_agent(parsed))

        # Assign priorities
        for i, req in enumerate(requirements):
            req.priority = i

        return requirements

    def _extract_from_lists(self, parsed: ParsedPrompt) -> List[AgentRequirement]:
        """Extract agent requirements from numbered/bulleted lists."""
        requirements = []

        # Pattern for list items
        list_pattern = r"(?:(?:\d+\.)|(?:-)|(?:\*)) (.+?)(?=(?:\d+\.)|(?:-)|(?:\*)|$)"

        for match in re.finditer(list_pattern, parsed.raw_prompt):
            item = match.group(1).strip()
            if not item:
                continue

            # Extract agent name and description
            agent_name = self._extract_agent_name(item)
            if agent_name:
                req = AgentRequirement(
                    name=agent_name,
                    role=self._extract_role(item),
                    purpose=item,
                    capabilities=self._extract_capabilities(item),
                    suggested_type=self._suggest_type(item),
                )
                requirements.append(req)

        return requirements

    def _extract_from_entities(self, parsed: ParsedPrompt) -> List[AgentRequirement]:
        """Extract agent requirements from identified entities."""
        requirements = []

        for agent_name in parsed.entities.get("agents", []):
            # Find context around agent mention
            pattern = rf"{agent_name}\s+agent[^.]*\."
            matches = re.findall(pattern, parsed.raw_prompt, re.IGNORECASE)

            purpose = matches[0] if matches else f"{agent_name} agent"

            req = AgentRequirement(
                name=self._sanitize_name(agent_name),
                role=agent_name.title(),
                purpose=purpose,
                capabilities=parsed.entities.get("capabilities", []),
                suggested_type="specialized",
            )
            requirements.append(req)

        return requirements

    def _create_default_agent(self, parsed: ParsedPrompt) -> AgentRequirement:
        """Create a default agent requirement when none are explicitly found."""
        domain = self._determine_domain(parsed)
        capabilities = parsed.entities.get("capabilities", ["process", "analyze"])

        return AgentRequirement(
            name=f"{domain.replace('-', '_')}_agent",
            role=f"{domain.title()} Agent",
            purpose=f"Agent for {domain} tasks",
            capabilities=capabilities,
            suggested_type="specialized",
        )

    def _extract_agent_name(self, text: str) -> Optional[str]:
        """Extract agent name from text."""
        # Look for "X Agent" or "X agent"
        pattern = r"(\w+(?:\s+\w+)?)\s+[Aa]gent"
        match = re.search(pattern, text)
        if match:
            return self._sanitize_name(match.group(1))

        # Look for descriptive names
        words = text.split()[:3]  # Take first few words
        if words:
            return self._sanitize_name("_".join(words))

        return None

    def _sanitize_name(self, name: str) -> str:
        """Sanitize agent name to be valid."""
        # Convert to lowercase and replace spaces with underscores
        sanitized = name.lower().replace(" ", "_")

        # Remove special characters
        sanitized = re.sub(r"[^a-z0-9_-]", "", sanitized)

        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "agent_" + sanitized

        return sanitized or "agent"

    def _extract_role(self, text: str) -> str:
        """Extract agent role from text."""
        # Try to find a descriptive role
        role_pattern = r"(?:for|that|which)\s+(\w+(?:\s+\w+){0,2})"
        match = re.search(role_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).title()

        # Use first significant word as role
        words = [
            w
            for w in text.split()
            if len(w) > 3 and w.lower() not in ["that", "which", "this", "with"]
        ]
        if words:
            return words[0].title()

        return "Agent"

    def _extract_capabilities(self, text: str) -> List[str]:
        """Extract capabilities from text."""
        capabilities = []

        # Look for action verbs
        action_verbs = [
            "analyze",
            "process",
            "validate",
            "scan",
            "monitor",
            "transform",
            "convert",
            "check",
            "verify",
            "generate",
            "create",
            "detect",
            "identify",
            "extract",
            "filter",
        ]

        text_lower = text.lower()
        for verb in action_verbs:
            if verb in text_lower:
                capabilities.append(verb)

        # Look for capability patterns
        cap_pattern = r"(?:can|will|should|must)\s+(\w+)"
        matches = re.findall(cap_pattern, text, re.IGNORECASE)
        capabilities.extend(matches)

        return list(set(capabilities)) or ["process"]

    def _suggest_type(self, text: str) -> str:
        """Suggest agent type based on text."""
        text_lower = text.lower()

        for agent_type, indicators in self.TYPE_INDICATORS.items():
            if any(indicator in text_lower for indicator in indicators):
                return agent_type

        # Default to specialized
        return "specialized"

    def _determine_complexity(
        self, parsed: ParsedPrompt, requirements: List[AgentRequirement]
    ) -> str:
        """Determine overall complexity level."""
        # Use parser's complexity detection
        base_complexity = self.parser.identify_complexity(parsed)

        # Adjust based on agent count and capabilities
        total_capabilities = sum(len(req.capabilities) for req in requirements)
        agent_count = len(requirements)

        if agent_count > 5 or total_capabilities > 15:
            return "advanced"
        if agent_count > 2 or total_capabilities > 8:
            return "standard"
        return base_complexity

    def _extract_constraints(self, parsed: ParsedPrompt) -> List[str]:
        """Extract constraints from parsed prompt."""
        constraints = []

        # Look for constraint patterns
        constraint_patterns = [
            r"must\s+(.+?)(?:\.|$)",
            r"should\s+(.+?)(?:\.|$)",
            r"cannot\s+(.+?)(?:\.|$)",
            r"limit(?:ed)?\s+to\s+(.+?)(?:\.|$)",
            r"maximum\s+(.+?)(?:\.|$)",
            r"minimum\s+(.+?)(?:\.|$)",
        ]

        for pattern in constraint_patterns:
            matches = re.findall(pattern, parsed.raw_prompt, re.IGNORECASE)
            constraints.extend(matches)

        # Add from parsed entities
        constraints.extend(parsed.entities.get("requirements", []))

        return list(set(constraints))

    def _extract_dependencies(self, parsed: ParsedPrompt) -> List[str]:
        """Extract dependencies from parsed prompt."""
        dependencies = []

        # Look for dependency keywords
        dep_patterns = [
            r"requires?\s+(.+?)(?:\.|$)",
            r"depends?\s+on\s+(.+?)(?:\.|$)",
            r"needs?\s+(.+?)(?:\.|$)",
            r"uses?\s+(.+?)(?:\.|$)",
        ]

        for pattern in dep_patterns:
            matches = re.findall(pattern, parsed.raw_prompt, re.IGNORECASE)
            dependencies.extend(matches)

        # Extract technology dependencies
        dependencies.extend(parsed.entities.get("technologies", []))

        return list(set(dependencies))

    def _calculate_confidence(
        self, parsed: ParsedPrompt, action: str, domain: str, requirements: List[AgentRequirement]
    ) -> float:
        """Calculate extraction confidence score."""
        confidence = parsed.confidence  # Start with parsing confidence

        # Boost for clear action
        if action != "create":  # Non-default action
            confidence += 0.1

        # Boost for identified domain
        if domain != "data-processing":  # Non-default domain
            confidence += 0.1

        # Boost for multiple requirements
        if len(requirements) > 1:
            confidence += 0.1

        # Boost for detailed requirements
        if any(len(req.capabilities) > 2 for req in requirements):
            confidence += 0.1

        return min(confidence, 1.0)
