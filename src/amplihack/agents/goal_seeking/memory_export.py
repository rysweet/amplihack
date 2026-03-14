"""Memory export/import utilities for knowledge transfer between agents.

Philosophy:
- Single responsibility: export and import memory data
- Two formats: JSON (portable, human-readable) and Kuzu (fast, raw DB copy)
- Standalone functions usable from CLI, scripts, or agent code
- JSON format preserves full graph structure (nodes + edges)

Public API:
    export_memory: Export an agent's memory to a file
    import_memory: Import memory from a file into an agent
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported export/import formats
SUPPORTED_FORMATS = ("json", "kuzu")


def export_memory(
    agent_name: str,
    storage_path: Path | None = None,
    output_path: Path | str = "exported_memory.json",
    fmt: str = "json",
) -> dict[str, Any]:
    """Export an agent's memory to a portable format.

    Args:
        agent_name: Name of the agent whose memory to export.
        storage_path: Path to the Kuzu database directory. If None, uses
            the default location (~/.amplihack/hierarchical_memory/<agent_name>).
        output_path: Where to write the export. For JSON, a .json file path.
            For kuzu, a directory path (the DB directory is copied there).
        fmt: Export format - "json" or "kuzu".

    Returns:
        Metadata dict with:
            - agent_name: Source agent name
            - format: Export format used
            - output_path: Absolute path to the exported file/directory
            - statistics: Node and edge counts

    Raises:
        ValueError: If format is not supported or agent_name is empty.
        FileNotFoundError: If Kuzu DB does not exist at storage_path (kuzu format).
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {fmt!r}. Use one of: {SUPPORTED_FORMATS}")
    if not agent_name or not agent_name.strip():
        raise ValueError("agent_name cannot be empty")

    output_path = Path(output_path)

    if fmt == "kuzu":
        return _export_kuzu(agent_name, storage_path, output_path)
    return _export_json(agent_name, storage_path, output_path)


def import_memory(
    agent_name: str,
    storage_path: Path | None = None,
    input_path: Path | str = "exported_memory.json",
    fmt: str = "json",
    merge: bool = False,
) -> dict[str, Any]:
    """Import memory from a portable format into an agent.

    Args:
        agent_name: Name of the target agent to import into.
        storage_path: Path to the Kuzu database directory. If None, uses
            the default location.
        input_path: Path to the exported file (JSON) or directory (Kuzu).
        fmt: Import format - "json" or "kuzu".
        merge: If True, adds to existing memory. If False, replaces all
            existing memory for this agent.

    Returns:
        Metadata dict with import statistics.

    Raises:
        ValueError: If format is not supported or agent_name is empty.
        FileNotFoundError: If input_path does not exist.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {fmt!r}. Use one of: {SUPPORTED_FORMATS}")
    if not agent_name or not agent_name.strip():
        raise ValueError("agent_name cannot be empty")

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if fmt == "kuzu":
        return _import_kuzu(agent_name, storage_path, input_path, merge)
    return _import_json(agent_name, storage_path, input_path, merge)


def _export_json(agent_name: str, storage_path: Path | None, output_path: Path) -> dict[str, Any]:
    """Export memory as JSON using HierarchicalMemory.export_to_json()."""
    from .hierarchical_memory import HierarchicalMemory

    mem = HierarchicalMemory(agent_name=agent_name, db_path=storage_path)
    try:
        export_data = mem.export_to_json()

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        file_size = output_path.stat().st_size

        return {
            "agent_name": agent_name,
            "format": "json",
            "output_path": str(output_path.resolve()),
            "file_size_bytes": file_size,
            "statistics": export_data.get("statistics", {}),
        }
    finally:
        mem.close()


def _import_json(
    agent_name: str, storage_path: Path | None, input_path: Path, merge: bool
) -> dict[str, Any]:
    """Import memory from JSON using HierarchicalMemory.import_from_json()."""
    from .hierarchical_memory import HierarchicalMemory

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    mem = HierarchicalMemory(agent_name=agent_name, db_path=storage_path)
    try:
        import_stats = mem.import_from_json(data, merge=merge)

        return {
            "agent_name": agent_name,
            "format": "json",
            "input_path": str(input_path.resolve()),
            "merge": merge,
            "source_agent": data.get("agent_name", "unknown"),
            "statistics": import_stats,
        }
    finally:
        mem.close()


def _export_kuzu(agent_name: str, storage_path: Path | None, output_path: Path) -> dict[str, Any]:
    """Export memory by copying the raw Kuzu DB directory."""
    # Resolve the actual DB path
    if storage_path is None:
        db_path = Path.home() / ".amplihack" / "hierarchical_memory" / agent_name
    else:
        db_path = Path(storage_path)

    # Find the actual kuzu_db directory
    if (db_path / "kuzu_db").is_dir():
        db_path = db_path / "kuzu_db"
    elif not (db_path / "lock").exists() and not db_path.name.endswith("kuzu_db"):
        # Try appending kuzu_db
        candidate = db_path / "kuzu_db"
        if candidate.is_dir():
            db_path = candidate

    if not db_path.exists():
        raise FileNotFoundError(f"Kuzu database not found at: {db_path}")

    # Copy the entire directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        shutil.rmtree(output_path)
    shutil.copytree(db_path, output_path)

    # Calculate size
    total_size = sum(f.stat().st_size for f in output_path.rglob("*") if f.is_file())

    return {
        "agent_name": agent_name,
        "format": "kuzu",
        "output_path": str(output_path.resolve()),
        "source_db_path": str(db_path.resolve()),
        "file_size_bytes": total_size,
        "statistics": {"note": "Raw Kuzu DB copy - use JSON format for node/edge counts"},
    }


def _import_kuzu(
    agent_name: str, storage_path: Path | None, input_path: Path, merge: bool
) -> dict[str, Any]:
    """Import memory by copying a Kuzu DB directory into place.

    Note: merge=True is not supported for kuzu format (raw DB replacement only).
    """
    if merge:
        raise ValueError(
            "Merge mode is not supported for kuzu format. "
            "Use JSON format for merge imports, or set merge=False to replace the DB entirely."
        )

    # Resolve target DB path
    if storage_path is None:
        target_path = Path.home() / ".amplihack" / "hierarchical_memory" / agent_name
    else:
        target_path = Path(storage_path)

    # Determine if we need to target a kuzu_db subdirectory
    if target_path.is_dir() and not (target_path / "lock").exists():
        target_path = target_path / "kuzu_db"

    # Backup and replace
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        backup_path = target_path.with_suffix(".bak")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(str(target_path), str(backup_path))
        logger.info("Backed up existing DB to %s", backup_path)

    shutil.copytree(input_path, target_path)

    total_size = sum(f.stat().st_size for f in target_path.rglob("*") if f.is_file())

    return {
        "agent_name": agent_name,
        "format": "kuzu",
        "input_path": str(input_path.resolve()),
        "target_db_path": str(target_path.resolve()),
        "merge": False,
        "file_size_bytes": total_size,
        "statistics": {"note": "Raw Kuzu DB replaced - restart agent to use new DB"},
    }
