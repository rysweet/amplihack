"""
Version Detector - Detect agent version and infrastructure phase.

Analyzes an agent directory to determine current version and setup.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from ..models import AgentVersionInfo


class VersionDetector:
    """Detect agent version and infrastructure details."""

    def detect(self, agent_dir: Path) -> AgentVersionInfo:
        """
        Detect version information for an agent.

        Args:
            agent_dir: Path to agent directory

        Returns:
            AgentVersionInfo with detected details

        Raises:
            ValueError: If directory is invalid or not an agent
        """
        agent_dir = Path(agent_dir).resolve()

        if not agent_dir.exists():
            raise ValueError(f"Agent directory does not exist: {agent_dir}")

        if not agent_dir.is_dir():
            raise ValueError(f"Path is not a directory: {agent_dir}")

        # Detect agent name
        agent_name = self._detect_name(agent_dir)

        # Detect version
        version = self._detect_version(agent_dir)

        # Detect infrastructure phase
        phase = self._detect_phase(agent_dir)

        # Detect installed skills
        skills = self._detect_skills(agent_dir)

        # Detect custom files
        custom_files = self._detect_custom_files(agent_dir)

        # Get last updated time
        last_updated = self._get_last_updated(agent_dir)

        return AgentVersionInfo(
            agent_dir=agent_dir,
            agent_name=agent_name,
            version=version,
            infrastructure_phase=phase,
            installed_skills=skills,
            custom_files=custom_files,
            last_updated=last_updated,
        )

    def _detect_name(self, agent_dir: Path) -> str:
        """Detect agent name from directory or config."""
        # Try agent_config.json first
        config_file = agent_dir / "agent_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    if "name" in config:
                        return config["name"]
            except (json.JSONDecodeError, IOError):
                pass

        # Try bundle metadata
        metadata_file = agent_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    if "bundle_name" in metadata:
                        return metadata["bundle_name"]
            except (json.JSONDecodeError, IOError):
                pass

        # Fall back to directory name
        return agent_dir.name

    def _detect_version(self, agent_dir: Path) -> str:
        """Detect agent version."""
        # Try .amplihack_version file
        version_file = agent_dir / ".amplihack_version"
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except IOError:
                pass

        # Try agent_config.json
        config_file = agent_dir / "agent_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    if "version" in config:
                        return config["version"]
            except (json.JSONDecodeError, IOError):
                pass

        # Try metadata.json
        metadata_file = agent_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    if "version" in metadata:
                        return metadata["version"]
            except (json.JSONDecodeError, IOError):
                pass

        # Default to unknown
        return "1.0.0"

    def _detect_phase(self, agent_dir: Path) -> Literal["phase1", "phase2", "phase3", "phase4"]:
        """Detect infrastructure phase."""
        # Check for phase indicators
        has_coordinator = (agent_dir / "coordinator.py").exists()
        has_learning = (agent_dir / "learning" / "execution_tracker.py").exists()
        has_skill_generator = (agent_dir / "skill_generator.py").exists()

        # Phase 4: Learning and adaptation
        if has_learning:
            return "phase4"

        # Phase 3: Multi-agent coordination
        if has_coordinator:
            return "phase3"

        # Phase 2: Custom skill generation
        if has_skill_generator:
            return "phase2"

        # Phase 1: Basic infrastructure
        return "phase1"

    def _detect_skills(self, agent_dir: Path) -> List[str]:
        """Detect installed skills."""
        skills = []

        # Check skills directory
        skills_dir = agent_dir / "skills"
        if skills_dir.exists() and skills_dir.is_dir():
            for skill_file in skills_dir.glob("*.md"):
                skills.append(skill_file.stem)

        # Check .claude/agents directory
        claude_skills_dir = agent_dir / ".claude" / "agents" / "amplihack"
        if claude_skills_dir.exists() and claude_skills_dir.is_dir():
            for skill_file in claude_skills_dir.glob("*.md"):
                skill_name = skill_file.stem
                if skill_name not in skills:
                    skills.append(skill_name)

        return sorted(skills)

    def _detect_custom_files(self, agent_dir: Path) -> List[Path]:
        """Detect custom user files (non-infrastructure)."""
        custom_files = []

        # Infrastructure patterns to exclude
        infrastructure_patterns = [
            "main.py",
            "coordinator.py",
            "skill_generator.py",
            "agent_config.json",
            "metadata.json",
            ".amplihack_version",
            "README.md",
            ".backups/",
            "skills/",
            ".claude/",
            "learning/",
            "__pycache__/",
            "*.pyc",
        ]

        # Find all files
        for file_path in agent_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if it's infrastructure
            relative = file_path.relative_to(agent_dir)
            is_infrastructure = any(
                relative.match(pattern) for pattern in infrastructure_patterns
            )

            if not is_infrastructure:
                custom_files.append(relative)

        return sorted(custom_files)

    def _get_last_updated(self, agent_dir: Path) -> Optional[datetime]:
        """Get last update time from agent directory."""
        # Try version file
        version_file = agent_dir / ".amplihack_version"
        if version_file.exists():
            try:
                stat = version_file.stat()
                return datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                pass

        # Try config file
        config_file = agent_dir / "agent_config.json"
        if config_file.exists():
            try:
                stat = config_file.stat()
                return datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                pass

        return None
