#!/usr/bin/env python3
"""Batch process backlog items with resumable state tracking.

Pattern: Amplifier P2 - Iterative Status Tracking for Batch Operations
Handles 100+ items with state persistence and resume capability.

This is a library module providing the BatchProcessor class.
Import and use in your own scripts with a real processor function.

Library Usage:
    from batch_process import BatchProcessor

    def my_processor(item):
        # Your actual processing logic here
        return {"result": process(item)}

    processor = BatchProcessor(Path.cwd(), "my_processor")
    results = processor.process_items(items, my_processor, batch_size=10)

CLI Usage (status/reset only):
    python batch_process.py --status [--processor NAME]
    python batch_process.py --reset --processor NAME
"""

import argparse
import json
import sys
from collections.abc import Callable
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
    """Get current UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class BatchProcessor:
    """Process large collections with state tracking and resumption."""

    def __init__(self, project_root: Path, processor_name: str):
        """Initialize batch processor.

        Args:
            project_root: Project root directory
            processor_name: Name of processing script (e.g., "analyze_backlog")
        """
        self.project_root = project_root
        self.pm_dir = project_root / ".pm"
        self.processor_name = processor_name
        self.status_file = self.pm_dir / f"batch_status_{processor_name}.yaml"
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Load batch processing state."""
        if self.status_file.exists():
            return load_yaml(self.status_file)

        return {
            "processor": self.processor_name,
            "started_at": get_timestamp(),
            "last_run": None,
            "processed": [],
            "failed": [],
            "last_id": None,
            "total_processed": 0,
            "total_failed": 0,
            "completed": False,
        }

    def save_state(self):
        """Persist state after each item (critical for resumption)."""
        self.state["last_run"] = get_timestamp()
        save_yaml(self.status_file, self.state)

    def is_processed(self, item_id: str) -> bool:
        """Check if item already processed."""
        return item_id in self.state["processed"] or item_id in [
            f["id"] for f in self.state["failed"]
        ]

    def mark_processed(self, item_id: str, result: dict = None):
        """Mark item as successfully processed."""
        if item_id not in self.state["processed"]:
            self.state["processed"].append(item_id)
            self.state["last_id"] = item_id
            self.state["total_processed"] += 1
            self.save_state()  # Save after EACH item

    def mark_failed(self, item_id: str, error: str):
        """Mark item as failed with error details."""
        failure = {"id": item_id, "error": error, "timestamp": get_timestamp()}

        # Update or add failure
        existing = next((f for f in self.state["failed"] if f["id"] == item_id), None)
        if existing:
            existing["error"] = error
            existing["timestamp"] = failure["timestamp"]
        else:
            self.state["failed"].append(failure)

        self.state["last_id"] = item_id
        self.state["total_failed"] += 1
        self.save_state()  # Save after EACH failure

    def process_items(
        self, items: list[dict], processor_func: Callable[[dict], dict], batch_size: int = 10
    ) -> dict:
        """Process items in batches with state tracking.

        Args:
            items: List of items to process
            processor_func: Function that processes single item
            batch_size: Number of items per progress report

        Returns:
            Summary of processing results
        """
        results = {"succeeded": [], "failed": [], "skipped": []}

        total = len(items)
        processed_count = 0

        for i, item in enumerate(items):
            item_id = item.get("id", f"item-{i}")

            # Skip already processed
            if self.is_processed(item_id):
                results["skipped"].append(item_id)
                continue

            try:
                # Process single item
                result = processor_func(item)
                self.mark_processed(item_id, result)
                results["succeeded"].append({"id": item_id, "result": result})

                processed_count += 1

                # Progress report every batch_size items
                if processed_count % batch_size == 0:
                    progress = (i + 1) / total * 100
                    print(
                        f"Progress: {i + 1}/{total} ({progress:.1f}%) - "
                        f"{processed_count} processed, {len(results['failed'])} failed",
                        file=sys.stderr,
                    )

            except Exception as e:
                error_msg = str(e)
                self.mark_failed(item_id, error_msg)
                results["failed"].append({"id": item_id, "error": error_msg})

        # Mark as completed
        self.state["completed"] = True
        self.save_state()

        return {
            "total_items": total,
            "processed": len(results["succeeded"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"]),
            "results": results,
            "state_file": str(self.status_file),
        }

    def reset_state(self):
        """Reset batch processing state (for retry)."""
        if self.status_file.exists():
            self.status_file.unlink()
        self.state = self.load_state()

    def get_progress(self) -> dict:
        """Get current progress information."""
        return {
            "processor": self.processor_name,
            "started_at": self.state.get("started_at"),
            "last_run": self.state.get("last_run"),
            "total_processed": self.state["total_processed"],
            "total_failed": self.state["total_failed"],
            "completed": self.state.get("completed", False),
            "last_id": self.state.get("last_id"),
        }


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Batch process items with resumable state tracking"
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument(
        "--processor", required=True, help="Processor name (e.g., 'analyze_backlog')"
    )
    parser.add_argument("--batch-size", type=int, default=10, help="Progress report interval")
    parser.add_argument("--reset", action="store_true", help="Reset state and start fresh")
    parser.add_argument("--status", action="store_true", help="Show current progress")

    args = parser.parse_args()

    try:
        processor = BatchProcessor(args.project_root, args.processor)

        if args.reset:
            processor.reset_state()
            print(json.dumps({"status": "reset", "processor": args.processor}))
            return 0

        if args.status:
            progress = processor.get_progress()
            print(json.dumps(progress, indent=2))
            return 0

        # This script provides the BatchProcessor class for use by other scripts
        # It is not meant to be run directly - import BatchProcessor and provide
        # your own processor function that implements real business logic
        print(
            json.dumps(
                {
                    "error": "batch_process.py is a library module, not a standalone script",
                    "usage": "Import BatchProcessor class and provide your own processor function",
                    "example": "from batch_process import BatchProcessor; processor = BatchProcessor(...)",
                }
            ),
            file=sys.stderr,
        )
        return 1

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
