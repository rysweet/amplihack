#!/usr/bin/env python3
"""Manage PM state files - utility for common state operations.

Usage:
    python manage_state.py init --project-name NAME --project-type TYPE --goals "goal1,goal2" --quality-bar LEVEL
    python manage_state.py add-item --title TITLE --priority PRIORITY [--description DESC]
    python manage_state.py update-item ITEM_ID --status STATUS
    python manage_state.py create-workstream ITEM_ID --agent AGENT
    python manage_state.py update-workstream WS_ID --status STATUS
    python manage_state.py list-backlog [--status STATUS]
    python manage_state.py list-workstreams [--status STATUS]
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    """Save YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO8601 format."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def cmd_init(args) -> int:
    """Initialize PM directory structure."""
    pm_dir = args.project_root / ".pm"

    if pm_dir.exists():
        print(f"Error: PM already initialized at {pm_dir}", file=sys.stderr)
        return 1

    # Create directories
    pm_dir.mkdir(parents=True)
    (pm_dir / "backlog").mkdir()
    (pm_dir / "workstreams").mkdir()
    (pm_dir / "logs").mkdir()

    # Parse goals
    goals = [g.strip() for g in args.goals.split(",")]

    # Create config
    config = {
        "project_name": args.project_name,
        "project_type": args.project_type,
        "primary_goals": goals,
        "quality_bar": args.quality_bar,
        "initialized_at": get_timestamp(),
        "version": "1.0",
    }
    save_yaml(pm_dir / "config.yaml", config)

    # Create empty backlog
    save_yaml(pm_dir / "backlog" / "items.yaml", {"items": []})

    # Create roadmap template
    roadmap = f"""# {args.project_name} Roadmap

## Project Overview

**Type**: {args.project_type}
**Quality Bar**: {args.quality_bar}

## Primary Goals

"""
    for goal in goals:
        roadmap += f"- {goal}\n"

    roadmap += """
## Current Focus

(Add current focus areas here)

## Backlog

(Items managed in .pm/backlog/items.yaml)

## Completed

(Track completed work here)
"""
    (pm_dir / "roadmap.md").write_text(roadmap)

    # Create context
    context = {
        "project_name": args.project_name,
        "initialized_at": config["initialized_at"],
        "version": "1.0",
    }
    save_yaml(pm_dir / "context.yaml", context)

    print(f"✓ PM initialized for {args.project_name}")
    return 0


def generate_backlog_id(items: list[dict]) -> str:
    """Generate next backlog ID."""
    if not items:
        return "BL-001"

    max_id = 0
    for item in items:
        item_id = item.get("id", "")
        if item_id.startswith("BL-"):
            try:
                num = int(item_id.split("-")[1])
                max_id = max(max_id, num)
            except (IndexError, ValueError):
                pass

    return f"BL-{max_id + 1:03d}"


def cmd_add_item(args) -> int:
    """Add backlog item."""
    pm_dir = args.project_root / ".pm"
    backlog_file = pm_dir / "backlog" / "items.yaml"

    data = load_yaml(backlog_file)
    items = data.get("items", [])

    item_id = generate_backlog_id(items)
    item = {
        "id": item_id,
        "title": args.title,
        "description": args.description or "",
        "priority": args.priority,
        "estimated_hours": args.estimated_hours,
        "status": "READY",
        "created_at": get_timestamp(),
        "tags": args.tags.split(",") if args.tags else [],
    }

    items.append(item)
    save_yaml(backlog_file, {"items": items})

    print(f"✓ Created {item_id}: {args.title}")
    return 0


def cmd_update_item(args) -> int:
    """Update backlog item."""
    pm_dir = args.project_root / ".pm"
    backlog_file = pm_dir / "backlog" / "items.yaml"

    data = load_yaml(backlog_file)
    items = data.get("items", [])

    found = False
    for item in items:
        if item["id"] == args.item_id:
            if args.status:
                item["status"] = args.status
            if args.priority:
                item["priority"] = args.priority
            if args.description:
                item["description"] = args.description
            found = True
            break

    if not found:
        print(f"Error: Item {args.item_id} not found", file=sys.stderr)
        return 1

    save_yaml(backlog_file, {"items": items})
    print(f"✓ Updated {args.item_id}")
    return 0


def generate_workstream_id(ws_dir: Path) -> str:
    """Generate next workstream ID."""
    existing = list(ws_dir.glob("ws-*.yaml")) if ws_dir.exists() else []

    if not existing:
        return "ws-001"

    max_id = 0
    for ws_file in existing:
        name = ws_file.stem
        if name.startswith("ws-"):
            try:
                num = int(name.split("-")[1])
                max_id = max(max_id, num)
            except (IndexError, ValueError):
                pass

    return f"ws-{max_id + 1:03d}"


def cmd_create_workstream(args) -> int:
    """Create workstream."""
    pm_dir = args.project_root / ".pm"
    backlog_file = pm_dir / "backlog" / "items.yaml"
    ws_dir = pm_dir / "workstreams"

    # Load backlog item
    data = load_yaml(backlog_file)
    items = data.get("items", [])
    item = next((i for i in items if i["id"] == args.item_id), None)

    if not item:
        print(f"Error: Item {args.item_id} not found", file=sys.stderr)
        return 1

    # Generate workstream ID
    ws_id = generate_workstream_id(ws_dir)

    # Create workstream
    ws = {
        "id": ws_id,
        "backlog_id": args.item_id,
        "title": item["title"],
        "status": "RUNNING",
        "agent": args.agent,
        "started_at": get_timestamp(),
        "completed_at": None,
        "process_id": None,
        "elapsed_minutes": 0,
        "progress_notes": [],
        "dependencies": [],
        "last_activity": get_timestamp(),
    }

    save_yaml(ws_dir / f"{ws_id}.yaml", ws)

    # Update backlog item status
    for item in items:
        if item["id"] == args.item_id:
            item["status"] = "IN_PROGRESS"
            break

    save_yaml(backlog_file, {"items": items})

    print(f"✓ Created {ws_id} for {args.item_id}")
    return 0


def cmd_update_workstream(args) -> int:
    """Update workstream."""
    pm_dir = args.project_root / ".pm"
    ws_file = pm_dir / "workstreams" / f"{args.ws_id}.yaml"

    if not ws_file.exists():
        print(f"Error: Workstream {args.ws_id} not found", file=sys.stderr)
        return 1

    ws = load_yaml(ws_file)

    if args.status:
        ws["status"] = args.status
        if args.status in ["COMPLETED", "FAILED"]:
            ws["completed_at"] = get_timestamp()

    if args.note:
        ws.setdefault("progress_notes", []).append(args.note)
        ws["last_activity"] = get_timestamp()

    save_yaml(ws_file, ws)
    print(f"✓ Updated {args.ws_id}")
    return 0


def cmd_list_backlog(args) -> int:
    """List backlog items."""
    pm_dir = args.project_root / ".pm"
    backlog_file = pm_dir / "backlog" / "items.yaml"

    data = load_yaml(backlog_file)
    items = data.get("items", [])

    if args.status:
        items = [i for i in items if i.get("status") == args.status]

    for item in items:
        status = item.get("status", "READY")
        priority = item.get("priority", "MEDIUM")
        print(f"{item['id']} [{status}] [{priority}] {item['title']}")

    print(f"\nTotal: {len(items)} items")
    return 0


def cmd_list_workstreams(args) -> int:
    """List workstreams."""
    pm_dir = args.project_root / ".pm"
    ws_dir = pm_dir / "workstreams"

    if not ws_dir.exists():
        print("No workstreams")
        return 0

    workstreams = []
    for ws_file in ws_dir.glob("ws-*.yaml"):
        ws = load_yaml(ws_file)
        if ws:
            workstreams.append(ws)

    if args.status:
        workstreams = [w for w in workstreams if w.get("status") == args.status]

    for ws in workstreams:
        status = ws.get("status", "RUNNING")
        agent = ws.get("agent", "unknown")
        print(f"{ws['id']} [{status}] [{agent}] {ws['title']}")

    print(f"\nTotal: {len(workstreams)} workstreams")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage PM state files")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize PM")
    init_parser.add_argument("--project-name", required=True)
    init_parser.add_argument("--project-type", required=True)
    init_parser.add_argument("--goals", required=True, help="Comma-separated goals")
    init_parser.add_argument(
        "--quality-bar", required=True, choices=["strict", "balanced", "relaxed"]
    )

    # Add item command
    add_parser = subparsers.add_parser("add-item", help="Add backlog item")
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--priority", default="MEDIUM", choices=["HIGH", "MEDIUM", "LOW"])
    add_parser.add_argument("--description", default="")
    add_parser.add_argument("--estimated-hours", type=int, default=4)
    add_parser.add_argument("--tags", default="")

    # Update item command
    update_parser = subparsers.add_parser("update-item", help="Update backlog item")
    update_parser.add_argument("item_id")
    update_parser.add_argument("--status", choices=["READY", "IN_PROGRESS", "DONE", "BLOCKED"])
    update_parser.add_argument("--priority", choices=["HIGH", "MEDIUM", "LOW"])
    update_parser.add_argument("--description")

    # Create workstream command
    create_ws_parser = subparsers.add_parser("create-workstream", help="Create workstream")
    create_ws_parser.add_argument("item_id")
    create_ws_parser.add_argument("--agent", default="builder")

    # Update workstream command
    update_ws_parser = subparsers.add_parser("update-workstream", help="Update workstream")
    update_ws_parser.add_argument("ws_id")
    update_ws_parser.add_argument("--status", choices=["RUNNING", "PAUSED", "COMPLETED", "FAILED"])
    update_ws_parser.add_argument("--note")

    # List commands
    list_bl_parser = subparsers.add_parser("list-backlog", help="List backlog items")
    list_bl_parser.add_argument("--status", choices=["READY", "IN_PROGRESS", "DONE", "BLOCKED"])

    list_ws_parser = subparsers.add_parser("list-workstreams", help="List workstreams")
    list_ws_parser.add_argument("--status", choices=["RUNNING", "PAUSED", "COMPLETED", "FAILED"])

    args = parser.parse_args()

    # Dispatch to command handler
    handlers = {
        "init": cmd_init,
        "add-item": cmd_add_item,
        "update-item": cmd_update_item,
        "create-workstream": cmd_create_workstream,
        "update-workstream": cmd_update_workstream,
        "list-backlog": cmd_list_backlog,
        "list-workstreams": cmd_list_workstreams,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
