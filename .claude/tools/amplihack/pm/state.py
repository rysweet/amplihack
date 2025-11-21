"""PM state management with file-based YAML storage.

This module provides the foundation for PM Architect Phase 1, managing
project configuration, backlog items, and workstream state through
simple YAML files.

Public API:
    - PMConfig: Project configuration
    - BacklogItem: Single backlog item
    - WorkstreamState: Active workstream state
    - PMStateManager: Central state management

Philosophy:
    - File-based state (no database)
    - Ruthless simplicity
    - Python stdlib + pyyaml only
    - Every function works (no stubs)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

try:
    # Try importing from installed package or sys.path first
    from amplihack.session.file_utils import retry_file_operation, FileOperationError
except ImportError:
    # Fallback for direct execution in .claude/tools/
    import sys

    _tools_dir = Path(__file__).parent.parent
    if str(_tools_dir) not in sys.path:
        sys.path.insert(0, str(_tools_dir))
    from session.file_utils import retry_file_operation, FileOperationError


__all__ = [
    "PMConfig",
    "BacklogItem",
    "WorkstreamState",
    "PMStateManager",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PMConfig:
    """PM configuration from .pm/config.yaml"""

    project_name: str
    project_type: str  # cli-tool, web-service, library, other
    primary_goals: List[str]
    quality_bar: str  # strict, balanced, relaxed
    initialized_at: str  # ISO timestamp
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PMConfig":
        """Create from dictionary loaded from YAML."""
        return cls(**data)


@dataclass
class BacklogItem:
    """Single backlog item from .pm/backlog/items.yaml"""

    id: str  # BL-001, BL-002, etc.
    title: str
    description: str = ""
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    estimated_hours: int = 4
    status: str = "READY"  # READY, IN_PROGRESS, DONE, BLOCKED
    created_at: str = ""  # ISO timestamp
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacklogItem":
        """Create from dictionary loaded from YAML."""
        return cls(**data)


@dataclass
class WorkstreamState:
    """Workstream state from .pm/workstreams/ws-*.yaml"""

    id: str  # ws-001, ws-002, etc.
    backlog_id: str  # BL-001
    title: str
    status: str  # RUNNING, PAUSED, COMPLETED, FAILED
    agent: str  # builder, reviewer, etc.
    started_at: str  # ISO timestamp
    completed_at: Optional[str] = None
    process_id: Optional[str] = None  # ClaudeProcess ID
    elapsed_minutes: int = 0
    progress_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkstreamState":
        """Create from dictionary loaded from YAML."""
        # Handle None for lists
        if data.get("progress_notes") is None:
            data["progress_notes"] = []
        return cls(**data)


# =============================================================================
# State Manager
# =============================================================================


class PMStateManager:
    """Manages PM state files with YAML operations.

    Responsibilities:
    - Initialize .pm/ directory structure
    - CRUD operations for config, backlog, workstreams
    - YAML serialization/deserialization
    - File I/O with retries (uses file_utils)
    - State validation

    Usage:
        manager = PMStateManager(project_root=Path.cwd())

        # Initialize new PM
        config = manager.initialize(project_name="my-project", ...)

        # Add backlog item
        item = manager.add_backlog_item(title="Feature X", priority="HIGH")

        # Get all backlog items
        items = manager.get_backlog_items(status="READY")

        # Create workstream
        ws = manager.create_workstream(backlog_id="BL-001", agent="builder")

        # Update workstream
        manager.update_workstream(ws.id, status="COMPLETED")
    """

    def __init__(self, project_root: Path):
        """Initialize state manager.

        Args:
            project_root: Root directory of project (contains .pm/)
        """
        self.project_root = project_root
        self.pm_dir = project_root / ".pm"

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(
        self,
        project_name: str,
        project_type: str,
        primary_goals: List[str],
        quality_bar: str,
    ) -> PMConfig:
        """Initialize PM directory structure and config.

        Creates:
        - .pm/config.yaml
        - .pm/roadmap.md (template)
        - .pm/backlog/items.yaml (empty list)
        - .pm/workstreams/ (empty dir)
        - .pm/context.yaml (project metadata)

        Returns:
            PMConfig object

        Raises:
            FileOperationError: If initialization fails
            ValueError: If .pm/ already exists
        """
        if self.is_initialized():
            raise ValueError(f"PM already initialized at {self.pm_dir}")

        # Create directory structure
        self.pm_dir.mkdir(parents=True, exist_ok=False)
        (self.pm_dir / "backlog").mkdir()
        (self.pm_dir / "workstreams").mkdir()
        (self.pm_dir / "logs").mkdir()

        # Create config
        config = PMConfig(
            project_name=project_name,
            project_type=project_type,
            primary_goals=primary_goals,
            quality_bar=quality_bar,
            initialized_at=datetime.utcnow().isoformat() + "Z",
            version="1.0",
        )
        self._write_yaml(self.pm_dir / "config.yaml", config.to_dict())

        # Create empty backlog
        self._write_yaml(self.pm_dir / "backlog" / "items.yaml", {"items": []})

        # Create roadmap template
        roadmap_template = f"""# {project_name} Roadmap

## Project Overview

**Type**: {project_type}
**Quality Bar**: {quality_bar}

## Primary Goals

"""
        for goal in primary_goals:
            roadmap_template += f"- {goal}\n"

        roadmap_template += """

## Current Focus

(Add current focus areas here)

## Backlog

(Items added via /pm:add will appear in .pm/backlog/items.yaml)

## Completed

(Track completed work here)
"""
        (self.pm_dir / "roadmap.md").write_text(roadmap_template)

        # Create context file
        context = {
            "project_name": project_name,
            "initialized_at": config.initialized_at,
            "version": "1.0",
        }
        self._write_yaml(self.pm_dir / "context.yaml", context)

        return config

    def is_initialized(self) -> bool:
        """Check if PM is initialized (.pm/ exists)."""
        return self.pm_dir.exists() and (self.pm_dir / "config.yaml").exists()

    # =========================================================================
    # Configuration
    # =========================================================================

    def get_config(self) -> PMConfig:
        """Load PM configuration."""
        if not self.is_initialized():
            raise FileOperationError("PM not initialized. Run /pm:init first.")

        data = self._read_yaml(self.pm_dir / "config.yaml")
        return PMConfig.from_dict(data)

    def update_config(self, **updates) -> PMConfig:
        """Update PM configuration."""
        config = self.get_config()
        config_dict = config.to_dict()
        config_dict.update(updates)
        self._write_yaml(self.pm_dir / "config.yaml", config_dict)
        return PMConfig.from_dict(config_dict)

    # =========================================================================
    # Backlog Operations
    # =========================================================================

    def add_backlog_item(
        self,
        title: str,
        priority: str = "MEDIUM",
        description: str = "",
        estimated_hours: int = 4,
        tags: Optional[List[str]] = None,
    ) -> BacklogItem:
        """Add item to backlog.

        Auto-generates ID (BL-001, BL-002, etc.)
        """
        backlog_id = self._generate_backlog_id()
        item = BacklogItem(
            id=backlog_id,
            title=title,
            description=description,
            priority=priority,
            estimated_hours=estimated_hours,
            status="READY",
            created_at=datetime.utcnow().isoformat() + "Z",
            tags=tags or [],
        )

        # Load current backlog
        data = self._read_yaml(self.pm_dir / "backlog" / "items.yaml")
        items = data.get("items", [])
        items.append(item.to_dict())

        # Save updated backlog
        self._write_yaml(self.pm_dir / "backlog" / "items.yaml", {"items": items})

        return item

    def get_backlog_items(self, status: Optional[str] = None) -> List[BacklogItem]:
        """Get all backlog items, optionally filtered by status."""
        data = self._read_yaml(self.pm_dir / "backlog" / "items.yaml")
        items = data.get("items", [])

        backlog_items = [BacklogItem.from_dict(item) for item in items]

        if status:
            backlog_items = [item for item in backlog_items if item.status == status]

        return backlog_items

    def get_backlog_item(self, backlog_id: str) -> Optional[BacklogItem]:
        """Get single backlog item by ID."""
        items = self.get_backlog_items()
        return next((item for item in items if item.id == backlog_id), None)

    def update_backlog_item(self, backlog_id: str, **updates) -> BacklogItem:
        """Update backlog item fields."""
        data = self._read_yaml(self.pm_dir / "backlog" / "items.yaml")
        items = data.get("items", [])

        # Find and update item
        found = False
        for item_dict in items:
            if item_dict["id"] == backlog_id:
                item_dict.update(updates)
                found = True
                break

        if not found:
            raise ValueError(f"Backlog item {backlog_id} not found")

        # Save updated backlog
        self._write_yaml(self.pm_dir / "backlog" / "items.yaml", {"items": items})

        # Return updated item
        return self.get_backlog_item(backlog_id)

    # =========================================================================
    # Workstream Operations
    # =========================================================================

    def create_workstream(
        self,
        backlog_id: str,
        agent: str = "builder",
    ) -> WorkstreamState:
        """Create new workstream from backlog item.

        Auto-generates ID (ws-001, ws-002, etc.)
        Updates backlog item status to IN_PROGRESS
        """
        # Validate backlog item exists
        backlog_item = self.get_backlog_item(backlog_id)
        if not backlog_item:
            raise ValueError(f"Backlog item {backlog_id} not found")

        # Generate workstream ID
        ws_id = self._generate_workstream_id()

        # Create workstream
        workstream = WorkstreamState(
            id=ws_id,
            backlog_id=backlog_id,
            title=backlog_item.title,
            status="RUNNING",
            agent=agent,
            started_at=datetime.utcnow().isoformat() + "Z",
        )

        # Save workstream file
        ws_file = self.pm_dir / "workstreams" / f"{ws_id}.yaml"
        self._write_yaml(ws_file, workstream.to_dict())

        # Update backlog item status
        self.update_backlog_item(backlog_id, status="IN_PROGRESS")

        return workstream

    def get_active_workstream(self) -> Optional[WorkstreamState]:
        """Get currently active workstream (only one allowed in Phase 1)."""
        workstreams_dir = self.pm_dir / "workstreams"
        if not workstreams_dir.exists():
            return None

        for ws_file in workstreams_dir.glob("ws-*.yaml"):
            data = self._read_yaml(ws_file)
            ws = WorkstreamState.from_dict(data)
            if ws.status == "RUNNING":
                return ws

        return None

    def get_workstream(self, ws_id: str) -> Optional[WorkstreamState]:
        """Get workstream by ID."""
        ws_file = self.pm_dir / "workstreams" / f"{ws_id}.yaml"
        if not ws_file.exists():
            return None

        data = self._read_yaml(ws_file)
        return WorkstreamState.from_dict(data)

    def update_workstream(self, ws_id: str, **updates) -> WorkstreamState:
        """Update workstream fields."""
        ws = self.get_workstream(ws_id)
        if ws is None:
            raise ValueError(f"Workstream {ws_id} not found")

        # Update fields
        ws_dict = ws.to_dict()
        ws_dict.update(updates)

        # Save updated workstream
        ws_file = self.pm_dir / "workstreams" / f"{ws_id}.yaml"
        self._write_yaml(ws_file, ws_dict)

        return WorkstreamState.from_dict(ws_dict)

    def complete_workstream(
        self,
        ws_id: str,
        success: bool = True,
    ) -> WorkstreamState:
        """Mark workstream as completed.

        Updates backlog item status to DONE or READY (if failed)
        """
        ws = self.get_workstream(ws_id)
        if ws is None:
            raise ValueError(f"Workstream {ws_id} not found")

        # Update workstream status
        new_status = "COMPLETED" if success else "FAILED"
        completed_at = datetime.utcnow().isoformat() + "Z"
        ws = self.update_workstream(
            ws_id,
            status=new_status,
            completed_at=completed_at,
        )

        # Update backlog item status
        backlog_status = "DONE" if success else "READY"
        self.update_backlog_item(ws.backlog_id, status=backlog_status)

        return ws

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _generate_backlog_id(self) -> str:
        """Generate next backlog ID (BL-001, BL-002, ...)."""
        items = self.get_backlog_items()
        if not items:
            return "BL-001"

        # Extract numeric IDs and find max
        max_id = 0
        for item in items:
            if item.id.startswith("BL-"):
                try:
                    num = int(item.id.split("-")[1])
                    max_id = max(max_id, num)
                except (IndexError, ValueError):
                    pass

        return f"BL-{max_id + 1:03d}"

    def _generate_workstream_id(self) -> str:
        """Generate next workstream ID (ws-001, ws-002, ...)."""
        workstreams_dir = self.pm_dir / "workstreams"
        if not workstreams_dir.exists():
            return "ws-001"

        # Find all existing workstream files
        existing = list(workstreams_dir.glob("ws-*.yaml"))
        if not existing:
            return "ws-001"

        # Extract numeric IDs and find max
        max_id = 0
        for ws_file in existing:
            name = ws_file.stem  # ws-001
            if name.startswith("ws-"):
                try:
                    num = int(name.split("-")[1])
                    max_id = max(max_id, num)
                except (IndexError, ValueError):
                    pass

        return f"ws-{max_id + 1:03d}"

    @retry_file_operation(max_retries=3, delay=0.1)
    def _read_yaml(self, path: Path) -> Dict[str, Any]:
        """Read YAML file with retries."""
        with open(path) as f:
            return yaml.safe_load(f) or {}

    @retry_file_operation(max_retries=3, delay=0.1)
    def _write_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """Write YAML file with retries."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
