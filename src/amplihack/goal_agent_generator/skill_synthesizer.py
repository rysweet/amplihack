"""
Skill Synthesizer - Match existing skills to required capabilities.

For MVP, copies existing skills from .claude/agents directory.
Supports SDK-specific tool mapping for multi-SDK agent generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ExecutionPlan, SDKToolConfig, SkillDefinition


# SDK-native tools available per SDK target
SDK_NATIVE_TOOLS: dict[str, dict[str, dict[str, str]]] = {
    "claude": {
        "bash": {"description": "Execute shell commands", "category": "system"},
        "read_file": {"description": "Read file contents", "category": "file_ops"},
        "write_file": {"description": "Create/overwrite files", "category": "file_ops"},
        "edit_file": {"description": "Modify files", "category": "file_ops"},
        "glob": {"description": "Find files by pattern", "category": "file_ops"},
        "grep": {"description": "Search file contents", "category": "search"},
    },
    "copilot": {
        "file_system": {"description": "File operations", "category": "file_ops"},
        "git": {"description": "Git version control", "category": "vcs"},
        "web_requests": {"description": "HTTP requests", "category": "network"},
    },
    "microsoft": {
        "ai_function": {"description": "Agent Framework AI functions", "category": "ai"},
    },
    "mini": {},  # No native tools beyond learning tools
}

# Mapping from capability categories to SDK tool categories
CAPABILITY_TO_CATEGORY: dict[str, list[str]] = {
    "file_ops": ["read", "write", "edit", "file", "create", "modify", "glob", "find"],
    "system": ["execute", "shell", "command", "run", "bash", "script"],
    "search": ["search", "grep", "find", "scan", "detect", "pattern"],
    "vcs": ["git", "version", "branch", "commit", "merge"],
    "network": ["http", "api", "request", "fetch", "web", "download", "webhook"],
    "ai": ["ai", "llm", "generate", "predict", "classify", "embed"],
}


class SkillSynthesizer:
    """Synthesize skills by matching existing skills to requirements."""

    # Skill matching keywords
    SKILL_KEYWORDS = {
        "data-processor": ["data", "process", "transform", "parse", "extract"],
        "security-analyzer": ["security", "vulnerability", "scan", "audit", "threat"],
        "tester": ["test", "validate", "verify", "check", "qa"],
        "deployer": ["deploy", "release", "publish", "ship"],
        "monitor": ["monitor", "alert", "track", "observe", "log"],
        "documenter": ["document", "report", "readme", "docs"],
        "analyzer": ["analyze", "review", "inspect", "examine"],
        "builder": ["build", "create", "generate", "implement"],
        "optimizer": ["optimize", "improve", "enhance", "performance"],
        "integrator": ["integrate", "connect", "api", "webhook"],
    }

    def __init__(self, skills_directory: Path | None = None):
        """
        Initialize skill synthesizer.

        Args:
            skills_directory: Path to existing skills directory
        """
        self.skills_directory = skills_directory or self._find_skills_directory()

    def synthesize_skills(
        self,
        execution_plan: ExecutionPlan,
        sdk: str = "copilot",
    ) -> list[SkillDefinition]:
        """
        Synthesize skills needed for execution plan.

        Args:
            execution_plan: Plan requiring skills
            sdk: Target SDK (claude, copilot, microsoft, mini)

        Returns:
            List of matched skills with scores
        """
        required_skills = set(execution_plan.required_skills)
        synthesized_skills = []

        for skill_name in required_skills:
            skill = self._find_matching_skill(skill_name)
            if skill:
                synthesized_skills.append(skill)

        # If no skills found, create fallback generic skill
        if not synthesized_skills:
            synthesized_skills.append(self._create_generic_skill())

        return synthesized_skills

    def get_sdk_tools(
        self,
        sdk: str,
        required_capabilities: list[str] | None = None,
    ) -> list[SDKToolConfig]:
        """
        Get SDK-native tools matching required capabilities.

        Maps required capabilities to SDK-native tools. If no capabilities
        are specified, returns all tools for the SDK.

        Args:
            sdk: Target SDK name (claude, copilot, microsoft, mini)
            required_capabilities: List of capability keywords to match

        Returns:
            List of SDKToolConfig for matched tools
        """
        sdk_key = sdk.lower()
        tools_map = SDK_NATIVE_TOOLS.get(sdk_key, {})

        if not tools_map:
            return []

        if not required_capabilities:
            # Return all tools for this SDK
            return [
                SDKToolConfig(
                    name=tool_name,
                    description=tool_info["description"],
                    category=tool_info["category"],
                )
                for tool_name, tool_info in tools_map.items()
            ]

        # Match capabilities to tool categories
        needed_categories = self._capabilities_to_categories(required_capabilities)

        matched_tools: list[SDKToolConfig] = []
        for tool_name, tool_info in tools_map.items():
            if tool_info["category"] in needed_categories:
                matched_tools.append(
                    SDKToolConfig(
                        name=tool_name,
                        description=tool_info["description"],
                        category=tool_info["category"],
                    )
                )

        return matched_tools

    def synthesize_with_sdk_tools(
        self,
        execution_plan: ExecutionPlan,
        sdk: str = "copilot",
    ) -> dict[str, Any]:
        """
        Synthesize skills AND SDK tool configurations together.

        Returns both amplihack skills and SDK-specific tool configs
        so the generated agent can leverage native SDK capabilities.

        Args:
            execution_plan: Plan requiring skills
            sdk: Target SDK name

        Returns:
            Dictionary with 'skills' and 'sdk_tools' keys
        """
        # Get amplihack skills
        skills = self.synthesize_skills(execution_plan, sdk=sdk)

        # Collect all required capabilities from execution plan phases
        all_capabilities: list[str] = []
        for phase in execution_plan.phases:
            all_capabilities.extend(phase.required_capabilities)

        # Get SDK-native tools for those capabilities
        sdk_tools = self.get_sdk_tools(sdk, required_capabilities=all_capabilities)

        return {
            "skills": skills,
            "sdk_tools": sdk_tools,
        }

    def _capabilities_to_categories(self, capabilities: list[str]) -> set[str]:
        """
        Map capability keywords to tool categories.

        Args:
            capabilities: List of capability keywords

        Returns:
            Set of matched tool categories
        """
        categories: set[str] = set()
        for cap in capabilities:
            cap_lower = cap.lower()
            for category, keywords in CAPABILITY_TO_CATEGORY.items():
                if any(kw in cap_lower for kw in keywords):
                    categories.add(category)
        return categories

    def _find_skills_directory(self) -> Path:
        """Find the .claude/agents directory."""
        # Start from current file and traverse up
        current = Path(__file__).resolve()

        for parent in [current] + list(current.parents):
            agents_dir = parent / ".claude" / "agents" / "amplihack"
            if agents_dir.exists() and agents_dir.is_dir():
                return agents_dir

        # Fallback: create temp directory
        return Path.cwd() / ".skills_temp"

    def _find_matching_skill(self, skill_name: str) -> SkillDefinition | None:
        """
        Find existing skill that matches the requirement.

        Args:
            skill_name: Name of required skill

        Returns:
            SkillDefinition if found, None otherwise
        """
        keywords = self.SKILL_KEYWORDS.get(skill_name, [skill_name.lower()])

        # Search for skill files in directory
        if not self.skills_directory.exists():
            return None

        best_match = None
        best_score = 0.0

        for skill_file in self.skills_directory.glob("**/*.md"):
            content = skill_file.read_text()
            content_lower = content.lower()

            # Calculate match score
            score = sum(1 for keyword in keywords if keyword in content_lower)
            score = score / len(keywords) if keywords else 0

            if score > best_score:
                best_score = score
                best_match = skill_file

        if best_match and best_score > 0.3:  # Threshold for acceptable match
            return self._load_skill(best_match, skill_name, best_score)

        return None

    def _load_skill(self, skill_path: Path, skill_name: str, match_score: float) -> SkillDefinition:
        """Load skill from file."""
        content = skill_path.read_text()

        # Extract description from first paragraph
        description = self._extract_description(content)

        # Extract capabilities from content
        capabilities = self._extract_capabilities(content, skill_name)

        # Extract dependencies
        dependencies = self._extract_dependencies(content)

        return SkillDefinition(
            name=skill_name,
            source_path=skill_path,
            capabilities=capabilities,
            description=description,
            content=content,
            dependencies=dependencies,
            match_score=match_score,
        )

    def _extract_description(self, content: str) -> str:
        """Extract description from skill markdown."""
        lines = content.split("\n")
        description_lines = []

        in_description = False
        for line in lines:
            stripped = line.strip()

            # Skip headings
            if stripped.startswith("#"):
                in_description = True
                continue

            # Collect description lines
            if in_description and stripped:
                description_lines.append(stripped)
                if len(description_lines) >= 3:  # First 3 lines
                    break

        return " ".join(description_lines[:200])  # Limit to 200 chars

    def _extract_capabilities(self, content: str, skill_name: str) -> list[str]:
        """Extract capabilities from skill content."""
        # Use keywords as capabilities
        keywords = self.SKILL_KEYWORDS.get(skill_name, [skill_name])

        # Look for additional capabilities in content
        content_lower = content.lower()
        capabilities = list(keywords)

        # Common capability patterns
        capability_words = [
            "analyze",
            "process",
            "transform",
            "validate",
            "generate",
            "deploy",
            "monitor",
            "report",
        ]

        for word in capability_words:
            if word in content_lower and word not in capabilities:
                capabilities.append(word)

        return capabilities[:5]  # Limit to top 5

    def _extract_dependencies(self, content: str) -> list[str]:
        """Extract dependencies from skill content."""
        dependencies = []

        # Look for dependency patterns
        if "requires" in content.lower() or "depends on" in content.lower():
            # Simple extraction - look for other skill names
            for skill_name in self.SKILL_KEYWORDS.keys():
                if skill_name in content.lower():
                    dependencies.append(skill_name)

        return dependencies[:3]  # Limit to top 3

    def _create_generic_skill(self) -> SkillDefinition:
        """Create a generic fallback skill."""
        return SkillDefinition(
            name="generic-executor",
            source_path=Path("builtin"),
            capabilities=["execute", "generic-task"],
            description="Generic skill for executing tasks",
            content="""# Generic Executor

This is a generic skill for executing tasks when no specific skill matches.

## Capabilities

- Execute generic tasks
- Coordinate with other skills
- Report results

## Usage

Use this skill when no other specialized skill is available.
""",
            match_score=0.5,
        )
