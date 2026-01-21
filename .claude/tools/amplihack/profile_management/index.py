"""Skill index building for fast component filtering.

Builds and maintains an index of skills for fast filtering. Basic version
for Phase 2, with scale optimization planned for Phase 6.
"""

import json
from datetime import datetime
from pathlib import Path


class SkillIndexBuilder:
    """Build and maintain index of skills for fast filtering.

    Scans skill directories and creates a JSON index for faster discovery
    than recursive filesystem scanning.
    """

    def __init__(self, skills_dir: Path = None):
        """Initialize with skills directory.

        Args:
            skills_dir: Path to .claude/skills/. Defaults to .claude/skills in cwd.
        """
        self.skills_dir = skills_dir or Path(".claude/skills")
        self.index_file = self.skills_dir / "_index.json"

    def build_index(self, force_rebuild: bool = False) -> dict:
        """Build skill index from directory structure.

        Args:
            force_rebuild: Rebuild even if index exists and is recent

        Returns:
            Index data dictionary

        Example:
            >>> builder = SkillIndexBuilder()
            >>> index = builder.build_index()
            >>> len(index["skills"])
            12
        """
        # Check if index exists and is recent
        if not force_rebuild and self.index_file.exists():
            # For Phase 2, just return existing index
            # Phase 6 will add incremental updates based on mtime
            return self._load_index()

        # Build new index
        index_data = {
            "version": "1.0",
            "generated": datetime.utcnow().isoformat() + "Z",
            "skills": [],
        }

        # Scan skills directory
        if not self.skills_dir.exists():
            return index_data

        for category_dir in self.skills_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            category = category_dir.name

            for skill_dir in category_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_name = skill_dir.name
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    skill_file = skill_dir / "README.md"

                if skill_file.exists():
                    skill_info = {
                        "name": skill_name,
                        "category": category,
                        "path": str(skill_file.relative_to(self.skills_dir.parent)),
                        "description": self._extract_description(skill_file),
                    }
                    index_data["skills"].append(skill_info)

        # Add metadata
        index_data["total_skills"] = len(index_data["skills"])

        # Save index
        self._save_index(index_data)

        return index_data

    def _extract_description(self, skill_file: Path) -> str:
        """Generate description from skill directory name.

        Args:
            skill_file: Path to SKILL.md or README.md

        Returns:
            Description string in format "Skill: {directory_name}"
        """
        return f"Skill: {skill_file.parent.name}"

    def _load_index(self) -> dict:
        """Load existing index from file.

        Returns:
            Index data dictionary, or empty index if loading fails
        """
        try:
            with open(self.index_file) as f:
                return json.load(f)
        except Exception:
            return {
                "version": "1.0",
                "generated": datetime.utcnow().isoformat() + "Z",
                "skills": [],
                "total_skills": 0,
            }

    def _save_index(self, index_data: dict):
        """Save index to file.

        Args:
            index_data: Index data dictionary to save
        """
        # Ensure directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        with open(self.index_file, "w") as f:
            json.dump(index_data, f, indent=2)

    def refresh_index(self) -> dict:
        """Force rebuild of skill index.

        Convenience method for rebuilding index.

        Returns:
            Updated index data dictionary
        """
        return self.build_index(force_rebuild=True)
