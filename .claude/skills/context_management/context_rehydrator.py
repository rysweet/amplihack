"""Context rehydration brick for restoring snapshots.

This module restores context from snapshots at configurable detail levels,
allowing selective rehydration based on needs (essential, standard, comprehensive).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ContextSnapshot

# Default snapshot storage location
DEFAULT_SNAPSHOT_DIR = ".claude/runtime/context-snapshots"


class ContextRehydrator:
    """Restores context from snapshots at configurable detail levels.

    This brick reads snapshot files and formats them for Claude to process,
    with three levels of detail: essential, standard, and comprehensive.

    Attributes:
        snapshot_dir: Directory where snapshots are stored
        LEVELS: Available detail levels
    """

    LEVELS = ["essential", "standard", "comprehensive"]

    def __init__(self, snapshot_dir: Optional[Path] = None):
        """Initialize context rehydrator.

        Args:
            snapshot_dir: Directory containing snapshots (default: .claude/runtime/context-snapshots)
        """
        if snapshot_dir is None:
            # Try to find project root
            cwd = Path.cwd()
            if (cwd / ".claude").exists():
                self.snapshot_dir = cwd / DEFAULT_SNAPSHOT_DIR
            else:
                self.snapshot_dir = Path(DEFAULT_SNAPSHOT_DIR)
        else:
            self.snapshot_dir = snapshot_dir

    def rehydrate(self, snapshot_path: Path, level: str = "standard") -> str:
        """Rehydrate context from snapshot.

        Args:
            snapshot_path: Path to snapshot file
            level: Detail level ('essential', 'standard', 'comprehensive')

        Returns:
            Formatted context string ready for Claude to process

        Raises:
            FileNotFoundError: If snapshot file doesn't exist
            ValueError: If level is invalid
            json.JSONDecodeError: If snapshot JSON is corrupted

        Example:
            >>> rehydrator = ContextRehydrator()
            >>> context = rehydrator.rehydrate(Path('snapshot.json'), level='essential')
            >>> 'Original Requirements' in context
            True

        Level Behaviors:
        - essential: Original requirements + current state only
        - standard: + key decisions + open items
        - comprehensive: + full decision log + all tools used
        """
        if level not in self.LEVELS:
            raise ValueError(f"Invalid level '{level}'. Must be one of: {self.LEVELS}")

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

        # Load snapshot
        with open(snapshot_path, encoding="utf-8") as f:
            snapshot_data = json.load(f)

        snapshot = ContextSnapshot.from_dict(snapshot_data)

        # Format based on level
        if level == "essential":
            return self._format_essential(snapshot)
        if level == "standard":
            return self._format_standard(snapshot)
        # comprehensive
        return self._format_comprehensive(snapshot)

    def _format_essential(self, snapshot: ContextSnapshot) -> str:
        """Format essential context (requirements + state only)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]
        return "\n".join(lines)

    def _format_standard(self, snapshot: ContextSnapshot) -> str:
        """Format standard context (+ decisions + open items)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]

        # Add key decisions if present
        if snapshot.key_decisions:
            lines.extend(["## Key Decisions", ""])
            for i, decision in enumerate(snapshot.key_decisions, 1):
                lines.append(f"{i}. {decision.get('decision', 'Unknown')}")
                if decision.get("rationale") != "Extracted from conversation":
                    lines.append(f"   - Rationale: {decision.get('rationale', 'N/A')}")
            lines.append("")

        # Add open items if present
        if snapshot.open_items:
            lines.extend(["## Open Items", ""])
            for item in snapshot.open_items:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    def _format_comprehensive(self, snapshot: ContextSnapshot) -> str:
        """Format comprehensive context (everything)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Estimated tokens: {snapshot.token_count}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]

        # Add key decisions with full details
        if snapshot.key_decisions:
            lines.extend(["## Key Decisions", ""])
            for i, decision in enumerate(snapshot.key_decisions, 1):
                lines.append(f"### Decision {i}")
                lines.append(f"**What:** {decision.get('decision', 'Unknown')}")
                lines.append(f"**Why:** {decision.get('rationale', 'N/A')}")
                lines.append(f"**Alternatives:** {decision.get('alternatives', 'N/A')}")
                lines.append("")

        # Add open items
        if snapshot.open_items:
            lines.extend(["## Open Items & Questions", ""])
            for item in snapshot.open_items:
                lines.append(f"- {item}")
            lines.append("")

        # Add tools used
        if snapshot.tools_used:
            lines.extend(["## Tools Used", ""])
            for tool in snapshot.tools_used:
                lines.append(f"- {tool}")
            lines.append("")

        return "\n".join(lines)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available context snapshots.

        Returns:
            List of snapshot metadata dicts with id, name, timestamp, size

        Example:
            >>> rehydrator = ContextRehydrator()
            >>> snapshots = rehydrator.list_snapshots()
            >>> len(snapshots) > 0
            True
        """
        if not self.snapshot_dir.exists():
            return []

        snapshots = []
        for snapshot_file in sorted(self.snapshot_dir.glob("*.json"), reverse=True):
            try:
                with open(snapshot_file, encoding="utf-8") as f:
                    data = json.load(f)

                snapshot = ContextSnapshot.from_dict(data)
                file_size = snapshot_file.stat().st_size

                snapshots.append(
                    {
                        "id": snapshot.snapshot_id,
                        "name": snapshot.name,
                        "timestamp": snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "size": self._format_size(file_size),
                        "token_count": snapshot.token_count,
                        "file_path": str(snapshot_file),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted snapshots
                continue

        return snapshots

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        return f"{size_bytes / (1024 * 1024):.1f}MB"

    def get_snapshot_path(self, snapshot_id: str) -> Optional[Path]:
        """Get path to snapshot by ID.

        Args:
            snapshot_id: Snapshot ID (format: YYYYMMDD_HHMMSS)

        Returns:
            Path to snapshot file, or None if not found
        """
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        return snapshot_file if snapshot_file.exists() else None
