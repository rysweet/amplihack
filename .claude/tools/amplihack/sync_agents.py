#!/usr/bin/env python3
"""
Agent synchronization utility for Copilot CLI.

Syncs agents from .claude/agents/ to .github/agents/ and maintains REGISTRY.json.

Philosophy:
- Fast (< 2 seconds for full sync)
- Preserves file structure
- Generates accurate registry
- Fail-safe error handling
"""

import json
import shutil
from pathlib import Path
from typing import Any


def sync_agents(source_dir: Path, target_dir: Path) -> dict[str, Any]:
    """Sync agents from source to target directory.

    Args:
        source_dir: Source directory (.claude/agents/)
        target_dir: Target directory (.github/agents/)

    Returns:
        Result dict with success status, synced count, and registry path
    """
    try:
        if not source_dir.exists():
            return {
                "success": False,
                "error": f"Source directory not found: {source_dir}",
            }

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Sync all .md files preserving structure
        synced_count = 0
        agent_files = []

        for agent_file in source_dir.rglob("*.md"):
            # Get relative path
            rel_path = agent_file.relative_to(source_dir)
            target_file = target_dir / rel_path

            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(agent_file, target_file)
            synced_count += 1
            agent_files.append(rel_path)

        # Generate REGISTRY.json
        registry_path = target_dir / "REGISTRY.json"
        registry = generate_agent_registry(target_dir)
        registry_path.write_text(json.dumps(registry, indent=2))

        return {
            "success": True,
            "synced_count": synced_count,
            "registry_path": str(registry_path),
            "agent_files": [str(f) for f in agent_files],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_agent_registry(agents_dir: Path) -> dict[str, Any]:
    """Generate agent registry from .github/agents/ directory.

    Args:
        agents_dir: Path to .github/agents/

    Returns:
        Registry dict with agent metadata
    """
    registry = {
        "version": "1.0",
        "generated": "auto",
        "agents": {},
    }

    # Scan all .md files
    for agent_file in agents_dir.rglob("*.md"):
        rel_path = agent_file.relative_to(agents_dir)

        # Extract metadata from frontmatter
        metadata = extract_agent_metadata(agent_file)

        # Add to registry
        agent_id = str(rel_path.with_suffix("")).replace("\\", "/")
        registry["agents"][agent_id] = {
            "path": str(rel_path).replace("\\", "/"),
            "name": metadata.get("name", agent_id),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "invocable_by": metadata.get("invocable_by", []),
        }

    return registry


def extract_agent_metadata(agent_file: Path) -> dict[str, Any]:
    """Extract metadata from agent file frontmatter.

    Args:
        agent_file: Path to agent .md file

    Returns:
        Metadata dict
    """
    try:
        content = agent_file.read_text()

        # Simple frontmatter extraction (between --- markers)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                metadata = parse_yaml_simple(frontmatter)
                return metadata

    except Exception:
        pass

    # Fallback: extract from filename
    return {
        "name": agent_file.stem.replace("-", " ").title(),
        "description": "",
        "tags": [],
        "invocable_by": [],
    }


def parse_yaml_simple(yaml_content: str) -> dict[str, Any]:
    """Simple YAML parser for frontmatter (no external dependencies).

    Args:
        yaml_content: YAML content string

    Returns:
        Parsed dict
    """
    metadata = {}

    for line in yaml_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Handle lists
            if value.startswith("[") and value.endswith("]"):
                # Simple list parsing
                items = value[1:-1].split(",")
                value = [item.strip().strip('"').strip("'") for item in items if item]
            else:
                # Remove quotes
                value = value.strip('"').strip("'")

            metadata[key] = value

    return metadata


def main():
    """CLI entry point for sync-agents."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: sync_agents.py <source_dir> <target_dir>")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    target_dir = Path(sys.argv[2])

    result = sync_agents(source_dir, target_dir)

    if result["success"]:
        print(f"✓ Synced {result['synced_count']} agents")
        print(f"  Registry: {result['registry_path']}")
    else:
        print(f"✗ Sync failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
