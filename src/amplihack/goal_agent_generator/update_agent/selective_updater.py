"""
Selective Updater - Apply selected updates to agent.

Applies infrastructure and skill updates while preserving custom code.
"""

import shutil
from pathlib import Path
from typing import List, Optional

from ..models import FileChange, SkillUpdate, UpdateChangeset


class SelectiveUpdater:
    """Apply selective updates to agent directory."""

    def __init__(self, agent_dir: Path, amplihack_root: Optional[Path] = None):
        """
        Initialize selective updater.

        Args:
            agent_dir: Path to agent directory
            amplihack_root: Root of amplihack installation
        """
        self.agent_dir = Path(agent_dir).resolve()
        self.amplihack_root = amplihack_root or self._find_amplihack_root()

    def apply_changeset(
        self,
        changeset: UpdateChangeset,
        selected_infrastructure: Optional[List[str]] = None,
        selected_skills: Optional[List[str]] = None,
    ) -> dict:
        """
        Apply selected updates from changeset.

        Args:
            changeset: Changeset to apply
            selected_infrastructure: List of infrastructure file paths to update
                (None = all safe updates)
            selected_skills: List of skill names to update (None = all)

        Returns:
            Dictionary with results:
                {
                    'infrastructure_updated': int,
                    'skills_updated': int,
                    'errors': List[str],
                }
        """
        results = {
            "infrastructure_updated": 0,
            "skills_updated": 0,
            "errors": [],
        }

        # Apply infrastructure updates
        for change in changeset.infrastructure_updates:
            # Skip if not selected
            if selected_infrastructure is not None:
                if str(change.file_path) not in selected_infrastructure:
                    continue

            # Skip breaking changes unless explicitly selected
            if change.safety == "breaking" and selected_infrastructure is None:
                continue

            # Apply update
            try:
                self._apply_file_change(change)
                results["infrastructure_updated"] += 1
            except Exception as e:
                results["errors"].append(
                    f"Failed to update {change.file_path}: {e}"
                )

        # Apply skill updates
        for skill_update in changeset.skill_updates:
            # Skip if not selected
            if selected_skills is not None:
                if skill_update.skill_name not in selected_skills:
                    continue

            # Apply skill update
            try:
                self._apply_skill_update(skill_update)
                results["skills_updated"] += 1
            except Exception as e:
                results["errors"].append(
                    f"Failed to update skill {skill_update.skill_name}: {e}"
                )

        # Update version file
        try:
            self._update_version(changeset.target_version)
        except Exception as e:
            results["errors"].append(f"Failed to update version: {e}")

        return results

    def validate_agent(self) -> tuple[bool, List[str]]:
        """
        Validate agent after update.

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

        # Check for required files
        required_files = ["main.py", "agent_config.json"]
        for file_name in required_files:
            file_path = self.agent_dir / file_name
            if not file_path.exists():
                issues.append(f"Missing required file: {file_name}")

        # Check Python syntax
        try:
            import py_compile

            for py_file in self.agent_dir.glob("*.py"):
                try:
                    py_compile.compile(str(py_file), doraise=True)
                except py_compile.PyCompileError as e:
                    issues.append(f"Syntax error in {py_file.name}: {e}")
        except ImportError:
            # py_compile not available, skip syntax check
            pass

        # Check JSON validity
        import json

        for json_file in self.agent_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in {json_file.name}: {e}")

        return len(issues) == 0, issues

    def _apply_file_change(self, change: FileChange) -> None:
        """Apply a single file change."""
        # Validate path is within agent_dir
        target_path = (self.agent_dir / change.file_path).resolve()
        agent_dir_resolved = self.agent_dir.resolve()

        if not str(target_path).startswith(str(agent_dir_resolved)):
            raise ValueError(f"Path traversal detected: {change.file_path}")

        # Blacklist sensitive paths
        forbidden = ['.ssh', '.env', 'credentials', 'secrets', 'private']
        if any(part in str(change.file_path).lower() for part in forbidden):
            raise ValueError(f"Forbidden path: {change.file_path}")

        if change.change_type == "add":
            # Add new file
            self._copy_template_file(change.file_path, target_path)

        elif change.change_type == "modify":
            # Modify existing file
            # For MVP, just overwrite (3-way merge would be better)
            self._copy_template_file(change.file_path, target_path)

        elif change.change_type == "delete":
            # Delete file
            if target_path.exists():
                target_path.unlink()

    def _apply_skill_update(self, skill_update: SkillUpdate) -> None:
        """Apply a skill update."""
        # Find skill source
        skills_dir = (
            self.amplihack_root / "src" / "amplihack" / ".claude" / "agents" / "amplihack"
        )
        if not skills_dir.exists():
            skills_dir = self.amplihack_root / ".claude" / "agents" / "amplihack"

        skill_source = skills_dir / f"{skill_update.skill_name}.md"
        if not skill_source.exists():
            raise FileNotFoundError(f"Skill not found: {skill_update.skill_name}")

        # Copy to agent skills directory
        agent_skills_dir = self.agent_dir / "skills"
        agent_skills_dir.mkdir(exist_ok=True)

        skill_target = agent_skills_dir / f"{skill_update.skill_name}.md"
        shutil.copy2(skill_source, skill_target)

    def _copy_template_file(self, template_path: Path, target_path: Path) -> None:
        """Copy template file to target."""
        # Find template in phase directories
        for phase in ["phase4", "phase3", "phase2", "phase1"]:
            phase_dir = (
                self.amplihack_root
                / "src"
                / "amplihack"
                / "goal_agent_generator"
                / phase
                / "templates"
            )
            template_file = phase_dir / template_path
            if template_file.exists():
                # Ensure parent directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                # Copy file
                shutil.copy2(template_file, target_path)
                return

        # Try general templates
        general_dir = (
            self.amplihack_root
            / "src"
            / "amplihack"
            / "goal_agent_generator"
            / "templates"
        )
        template_file = general_dir / template_path
        if template_file.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template_file, target_path)
            return

        raise FileNotFoundError(f"Template not found: {template_path}")

    def _update_version(self, version: str) -> None:
        """Update version file."""
        version_file = self.agent_dir / ".amplihack_version"
        version_file.write_text(version)

    def _find_amplihack_root(self) -> Path:
        """Find amplihack installation root."""
        try:
            import amplihack

            return Path(amplihack.__file__).parent.parent.parent
        except ImportError:
            return Path.cwd()
