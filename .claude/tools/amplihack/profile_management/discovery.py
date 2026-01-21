"""Component discovery from amplihack filesystem structure.

Discovers available commands, context files, agents, and skills from the
amplihack directory structure to enable profile-based filtering.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComponentInventory:
    """Available components discovered from filesystem.

    Attributes:
        commands: Mapping of command name to file path
        context: Mapping of context file name to file path
        agents: Mapping of agent name to file path
        skills: Mapping of skill name to file path
        skill_categories: Mapping of category name to list of skill names
    """

    commands: dict[str, Path]
    context: dict[str, Path]
    agents: dict[str, Path]
    skills: dict[str, Path]
    skill_categories: dict[str, list[str]]


class ComponentDiscovery:
    """Discover available amplihack components from filesystem.

    Scans .claude directory structure to identify all available commands,
    context files, agents, and skills for profile-based filtering.
    """

    def __init__(self, root_dir: Path = None):
        """Initialize with amplihack root directory.

        Args:
            root_dir: Path to .claude directory. Defaults to .claude in cwd.
        """
        self.root_dir = root_dir or Path(".claude")

    def discover_all(self) -> ComponentInventory:
        """Discover all available components.

        Returns:
            ComponentInventory with all discovered components
        """
        return ComponentInventory(
            commands=self._discover_commands(),
            context=self._discover_context(),
            agents=self._discover_agents(),
            skills=self._discover_skills(),
            skill_categories=self._discover_skill_categories(),
        )

    def _discover_commands(self) -> dict[str, Path]:
        """Discover slash commands from .claude/commands/amplihack/.

        Returns:
            Mapping of command name to file path

        Examples:
            ultrathink.md -> "ultrathink"
            ddd/1-plan.md -> "ddd:1-plan"
        """
        commands_dir = self.root_dir / "commands" / "amplihack"
        if not commands_dir.exists():
            return {}

        commands = {}
        for cmd_file in commands_dir.rglob("*.md"):
            # Extract command name
            rel_path = cmd_file.relative_to(commands_dir)

            # For nested commands, use parent:stem format
            if rel_path.parent != Path("."):
                name = f"{rel_path.parent.name}:{cmd_file.stem}"
            else:
                name = cmd_file.stem

            commands[name] = cmd_file

        return commands

    def _discover_context(self) -> dict[str, Path]:
        """Discover context files from .claude/context/.

        Returns:
            Mapping of context file name to file path
        """
        context_dir = self.root_dir / "context"
        if not context_dir.exists():
            return {}

        context = {}
        for ctx_file in context_dir.glob("*.md"):
            context[ctx_file.name] = ctx_file

        return context

    def _discover_agents(self) -> dict[str, Path]:
        """Discover agents from .claude/agents/amplihack/.

        Returns:
            Mapping of agent name to file path

        Examples:
            architect.md -> "architect"
            specialized/cleanup.md -> "cleanup"
        """
        agents_dir = self.root_dir / "agents" / "amplihack"
        if not agents_dir.exists():
            return {}

        agents = {}
        for agent_file in agents_dir.rglob("*.md"):
            # Use stem (filename without extension) as agent name
            agents[agent_file.stem] = agent_file

        return agents

    def _discover_skills(self) -> dict[str, Path]:
        """Discover skills from .claude/skills/.

        Uses skill index if available for performance, otherwise scans
        directories as fallback.

        Returns:
            Mapping of skill name to file path
        """
        skills_dir = self.root_dir / "skills"
        if not skills_dir.exists():
            return {}

        # Try to load from index first (fast path)
        index_file = skills_dir / "_index.json"
        if index_file.exists():
            return self._load_skills_from_index(index_file)

        # Fallback: scan directories (slower but works without index)
        return self._scan_skills_directories(skills_dir)

    def _load_skills_from_index(self, index_file: Path) -> dict[str, Path]:
        """Load skills from index file.

        Args:
            index_file: Path to _index.json

        Returns:
            Mapping of skill name to file path
        """
        try:
            with open(index_file) as f:
                index_data = json.load(f)

            skills = {}
            for skill in index_data.get("skills", []):
                name = skill["name"]
                # Path in index is relative to .claude/
                path = self.root_dir.parent / skill["path"]
                skills[name] = path

            return skills
        except (FileNotFoundError, json.JSONDecodeError, KeyError, PermissionError):
            # If index loading fails, fallback to directory scanning
            return self._scan_skills_directories(index_file.parent)

    def _scan_skills_directories(self, skills_dir: Path) -> dict[str, Path]:
        """Scan skill directories (fallback when no index).

        Args:
            skills_dir: Path to .claude/skills/

        Returns:
            Mapping of skill name to file path
        """
        skills = {}

        # Look for SKILL.md or README.md in each subdirectory
        for skill_dir in skills_dir.rglob("*"):
            if not skill_dir.is_dir():
                continue

            # Check for SKILL.md first, then README.md
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                skill_file = skill_dir / "README.md"

            if skill_file.exists():
                skills[skill_dir.name] = skill_file

        return skills

    def _discover_skill_categories(self) -> dict[str, list[str]]:
        """Discover skill categories from directory structure.

        Returns:
            Mapping of category name to list of skill names
        """
        skills_dir = self.root_dir / "skills"
        if not skills_dir.exists():
            return {}

        # Try to load from index first (fast path)
        index_file = skills_dir / "_index.json"
        if index_file.exists():
            return self._load_categories_from_index(index_file)

        # Fallback: infer from directory structure
        return self._infer_categories_from_structure(skills_dir)

    def _load_categories_from_index(self, index_file: Path) -> dict[str, list[str]]:
        """Load categories from index file.

        Args:
            index_file: Path to _index.json

        Returns:
            Mapping of category name to list of skill names
        """
        try:
            with open(index_file) as f:
                index_data = json.load(f)

            categories = {}
            for skill in index_data.get("skills", []):
                category = skill.get("category", "uncategorized")
                if category not in categories:
                    categories[category] = []
                categories[category].append(skill["name"])

            return categories
        except (FileNotFoundError, json.JSONDecodeError, KeyError, PermissionError):
            return self._infer_categories_from_structure(index_file.parent)

    def _infer_categories_from_structure(self, skills_dir: Path) -> dict[str, list[str]]:
        """Infer categories from directory structure.

        Assumes one level of categorization: skills/category/skill-name/

        Args:
            skills_dir: Path to .claude/skills/

        Returns:
            Mapping of category name to list of skill names
        """
        categories = {}

        # Scan top-level directories as categories
        for category_dir in skills_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            category = category_dir.name
            skills_in_category = []

            # Scan subdirectories as skills
            for skill_dir in category_dir.iterdir():
                if skill_dir.is_dir():
                    skills_in_category.append(skill_dir.name)

            if skills_in_category:
                categories[category] = skills_in_category

        return categories
