"""
Changeset Generator - Generate update changesets for agents.

Analyzes differences between current and target versions.
"""

import difflib
from pathlib import Path
from typing import List, Optional

from ..models import (
    AgentVersionInfo,
    FileChange,
    SkillUpdate,
    UpdateChangeset,
)


class ChangesetGenerator:
    """Generate update changesets comparing versions."""

    def __init__(self, amplihack_root: Optional[Path] = None):
        """
        Initialize changeset generator.

        Args:
            amplihack_root: Root of amplihack installation (auto-detect if None)
        """
        self.amplihack_root = amplihack_root or self._find_amplihack_root()

    def generate(
        self,
        current_version: AgentVersionInfo,
        target_version: str = "latest",
    ) -> UpdateChangeset:
        """
        Generate changeset for updating agent.

        Args:
            current_version: Current agent version info
            target_version: Target version to update to

        Returns:
            UpdateChangeset describing available updates
        """
        # Find infrastructure updates based on phase
        infrastructure_updates = self._find_infrastructure_updates(
            current_version.agent_dir,
            current_version.infrastructure_phase,
        )

        # Find skill updates
        skill_updates = self._find_skill_updates(
            current_version.installed_skills,
        )

        # Classify changes
        breaking_changes = self._identify_breaking_changes(infrastructure_updates)
        bug_fixes = self._identify_bug_fixes(target_version)
        enhancements = self._identify_enhancements(infrastructure_updates, skill_updates)

        # Calculate totals
        total_changes = (
            len(infrastructure_updates) + len(skill_updates) + len(breaking_changes)
        )

        # Estimate time
        estimated_time = self._estimate_time(total_changes)

        return UpdateChangeset(
            current_version=current_version.version,
            target_version=target_version,
            infrastructure_updates=infrastructure_updates,
            skill_updates=skill_updates,
            breaking_changes=breaking_changes,
            bug_fixes=bug_fixes,
            enhancements=enhancements,
            total_changes=total_changes,
            estimated_time=estimated_time,
        )

    def _find_amplihack_root(self) -> Path:
        """Find amplihack installation root."""
        # Try to find it from module location
        try:
            import amplihack

            return Path(amplihack.__file__).parent.parent.parent
        except ImportError:
            # Fall back to current directory
            return Path.cwd()

    def _find_infrastructure_updates(
        self,
        agent_dir: Path,
        current_phase: str,
    ) -> List[FileChange]:
        """Find infrastructure file updates."""
        updates = []

        # Infrastructure files by phase
        phase_files = {
            "phase1": ["main.py", "agent_config.json"],
            "phase2": ["main.py", "agent_config.json", "skill_generator.py"],
            "phase3": [
                "main.py",
                "agent_config.json",
                "skill_generator.py",
                "coordinator.py",
            ],
            "phase4": [
                "main.py",
                "agent_config.json",
                "skill_generator.py",
                "coordinator.py",
                "learning/execution_tracker.py",
            ],
        }

        # Get files for current phase
        files_to_check = phase_files.get(current_phase, phase_files["phase1"])

        # Check each file
        for file_name in files_to_check:
            file_path = Path(file_name)
            agent_file = agent_dir / file_path
            template_file = self._find_template_file(file_path, current_phase)

            if template_file and template_file.exists():
                # Check if file exists in agent
                if not agent_file.exists():
                    # New file to add
                    updates.append(
                        FileChange(
                            file_path=file_path,
                            change_type="add",
                            category="infrastructure",
                            safety="safe",
                        )
                    )
                else:
                    # Check if modified
                    diff = self._compute_diff(agent_file, template_file)
                    if diff:
                        # Determine safety
                        safety = "safe" if self._is_safe_update(diff) else "review"
                        updates.append(
                            FileChange(
                                file_path=file_path,
                                change_type="modify",
                                category="infrastructure",
                                diff=diff,
                                safety=safety,
                            )
                        )

        return updates

    def _find_skill_updates(self, current_skills: List[str]) -> List[SkillUpdate]:
        """Find available skill updates."""
        updates = []

        # Find available skills in amplihack
        skills_dir = self.amplihack_root / "src" / "amplihack" / ".claude" / "agents" / "amplihack"
        if not skills_dir.exists():
            # Try alternative location
            skills_dir = (
                self.amplihack_root / ".claude" / "agents" / "amplihack"
            )

        if skills_dir.exists():
            available_skills = {f.stem for f in skills_dir.glob("*.md")}

            # Find new skills
            new_skills = available_skills - set(current_skills)
            for skill_name in sorted(new_skills):
                updates.append(
                    SkillUpdate(
                        skill_name=skill_name,
                        current_version=None,
                        new_version="latest",
                        change_type="new",
                        changes=["New skill available"],
                    )
                )

            # Find updated skills - only report if actually changed
            for skill_name in current_skills:
                if skill_name in available_skills:
                    # Check if skill file actually changed
                    current_skill_path = agent_dir / ".claude" / "agents" / f"{skill_name}.md"
                    available_skill_path = (
                        self.amplihack_root / ".claude" / "agents" / "amplihack" / f"{skill_name}.md"
                    )

                    if self._skill_content_changed(current_skill_path, available_skill_path):
                        updates.append(
                            SkillUpdate(
                                skill_name=skill_name,
                                current_version=None,  # Version tracking not implemented yet
                                new_version=None,
                                change_type="update",
                                changes=["Skill content updated"],
                            )
                        )

        return updates

    def _find_template_file(self, file_path: Path, phase: str) -> Optional[Path]:
        """Find template file in amplihack for given phase."""
        # Try phase-specific directory
        phase_dir = (
            self.amplihack_root
            / "src"
            / "amplihack"
            / "goal_agent_generator"
            / phase
            / "templates"
        )
        template = phase_dir / file_path
        if template.exists():
            return template

        # Try general templates
        general_dir = (
            self.amplihack_root
            / "src"
            / "amplihack"
            / "goal_agent_generator"
            / "templates"
        )
        template = general_dir / file_path
        if template.exists():
            return template

        return None

    def _compute_diff(self, file1: Path, file2: Path) -> Optional[str]:
        """Compute unified diff between two files."""
        try:
            with open(file1, "r") as f1, open(file2, "r") as f2:
                lines1 = f1.readlines()
                lines2 = f2.readlines()

            diff = list(
                difflib.unified_diff(
                    lines1,
                    lines2,
                    fromfile=str(file1),
                    tofile=str(file2),
                    lineterm="",
                )
            )

            if diff:
                return "\n".join(diff)
            return None
        except IOError:
            return None

    def _is_safe_update(self, diff: str) -> bool:
        """Determine if diff is safe to auto-apply."""
        # Simple heuristics for safety
        lines = diff.split("\n")

        # Check for risky patterns
        risky_patterns = [
            "import ",  # Import changes
            "def ",  # Function signature changes
            "class ",  # Class definition changes
            "TODO",  # Incomplete changes
            "FIXME",  # Known issues
        ]

        added_lines = [line for line in lines if line.startswith("+")]

        for line in added_lines:
            if any(pattern in line for pattern in risky_patterns):
                return False

        # Safe if only comments or docstrings
        return True

    def _identify_breaking_changes(
        self, infrastructure_updates: List[FileChange]
    ) -> List[str]:
        """Identify breaking changes in updates."""
        breaking = []

        for change in infrastructure_updates:
            if change.change_type == "delete":
                breaking.append(f"Removes {change.file_path}")
            elif change.safety == "breaking":
                breaking.append(f"Breaking change in {change.file_path}")

        return breaking

    def _identify_bug_fixes(self, target_version: str) -> List[str]:
        """Identify bug fixes in target version by reading CHANGELOG.md.

        Returns:
            List of bug fix descriptions, or empty list if no changelog
        """
        changelog_path = self.amplihack_root / "CHANGELOG.md"
        if not changelog_path.exists():
            return []  # No changelog available

        try:
            changelog_content = changelog_path.read_text()
            return self._parse_changelog_section(changelog_content, target_version, "Fixed")
        except (IOError, UnicodeDecodeError):
            return []  # Failed to read changelog

    def _identify_enhancements(
        self,
        infrastructure_updates: List[FileChange],
        skill_updates: List[SkillUpdate],
    ) -> List[str]:
        """Identify enhancements in updates."""
        enhancements = []

        # Infrastructure enhancements
        for change in infrastructure_updates:
            if change.change_type == "add":
                enhancements.append(f"Adds new {change.file_path}")

        # Skill enhancements
        new_skills = [s for s in skill_updates if s.change_type == "new"]
        if new_skills:
            enhancements.append(f"Adds {len(new_skills)} new skills")

        return enhancements

    def _parse_changelog_section(
        self, changelog_content: str, version: str, section_name: str
    ) -> List[str]:
        """Parse specific section from changelog for a version.

        Args:
            changelog_content: Full changelog text
            version: Version to find (e.g., "2.0.0")
            section_name: Section to extract (e.g., "Fixed", "Added", "Changed")

        Returns:
            List of items from that section
        """
        items = []
        in_version = False
        in_section = False

        for line in changelog_content.split("\n"):
            line = line.strip()

            # Check if entering version section (e.g., "## [2.0.0]" or "# Version 2.0.0")
            if version in line and line.startswith("#"):
                in_version = True
                continue

            # Check if leaving version section (next version header at same or higher level)
            if in_version and line.startswith("##") and "[" in line and version not in line:
                break

            # Check if entering target section
            if in_version and section_name in line and line.startswith("###"):
                in_section = True
                continue

            # Check if leaving section (next section header at same level)
            if in_section and line.startswith("###"):
                in_section = False
                continue

            # Extract items from section (lines starting with -, *, or bullets)
            if in_section and (line.startswith("-") or line.startswith("*")):
                # Remove bullet point and clean up
                item = line.lstrip("-*").strip()
                if item:
                    items.append(item)

        return items

    def _skill_content_changed(self, current_path: Path, available_path: Path) -> bool:
        """Check if skill file content has changed.

        Args:
            current_path: Path to current skill file
            available_path: Path to available skill file

        Returns:
            True if content differs, False if same or error
        """
        try:
            # Check if both files exist
            if not current_path.exists() or not available_path.exists():
                return False

            # Compare file content
            current_content = current_path.read_text()
            available_content = available_path.read_text()

            return current_content != available_content

        except (IOError, UnicodeDecodeError):
            # If we can't read files, assume no change
            return False

    def _estimate_time(self, total_changes: int) -> str:
        """Estimate time for update."""
        if total_changes == 0:
            return "0 seconds"
        elif total_changes <= 5:
            return "1-2 minutes"
        elif total_changes <= 10:
            return "3-5 minutes"
        elif total_changes <= 20:
            return "5-10 minutes"
        else:
            return "10+ minutes"
