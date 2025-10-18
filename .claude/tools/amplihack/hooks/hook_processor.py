#!/usr/bin/env python3
"""
Unified hook processor for Claude Code hooks.
Provides common functionality for all hook scripts.
"""

import json
import sys
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class HookProcessor(ABC):
    """Base class for Claude Code hook processors.

    Handles common operations:
    - JSON input/output from stdin/stdout
    - Logging to runtime directory
    - Error handling and graceful fallback
    - Clean import structure
    """

    def __init__(self, hook_name: str):
        """Initialize the hook processor.

        Args:
            hook_name: Name of the hook (used for logging)
        """
        self.hook_name = hook_name

        # Use clean import path resolution
        try:
            # Import after ensuring path is set up
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from paths import get_project_root

            self.project_root = get_project_root()
        except ImportError:
            # Fallback: try to find project root by looking for .claude marker
            current = Path(__file__).resolve().parent
            found_root: Optional[Path] = None

            for _ in range(10):  # Max 10 levels up
                # Check old location (repo root)
                if (current / ".claude").exists():
                    found_root = current
                    break
                # Check new location (package)
                if (current / "src" / "amplihack" / ".claude").exists():
                    found_root = current
                    break
                if current == current.parent:
                    break
                current = current.parent

            if found_root is None:
                raise ValueError("Could not find project root with .claude marker")

            self.project_root = found_root

        # Find .claude directory (could be at root or in package)
        claude_dir = self.project_root / ".claude"
        if not claude_dir.exists():
            claude_dir = self.project_root / "src" / "amplihack" / ".claude"
            if not claude_dir.exists():
                raise ValueError("Could not find .claude directory in expected locations")

        # Setup directories using found location
        self.log_dir = claude_dir / "runtime" / "logs"
        self.metrics_dir = claude_dir / "runtime" / "metrics"
        self.analysis_dir = claude_dir / "runtime" / "analysis"

        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

        # Setup log file
        self.log_file = self.log_dir / f"{hook_name}.log"

    def validate_path_containment(self, path: Path) -> Path:
        """Validate that path stays within project boundaries.

        Args:
            path: Path to validate

        Returns:
            Resolved path if valid

        Raises:
            ValueError: If path escapes project root
        """
        resolved = path.resolve()
        try:
            # Check if path is within project root
            resolved.relative_to(self.project_root)
            return resolved
        except ValueError:
            raise ValueError(f"Path escapes project root: {path}")

    def log(self, message: str, level: str = "INFO"):
        """Log a message to the hook's log file.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().isoformat()
        try:
            # Check log file size and rotate if needed (10MB limit)
            if self.log_file.exists() and self.log_file.stat().st_size > 10 * 1024 * 1024:
                # Rotate log file
                backup = self.log_file.with_suffix(
                    f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                )
                self.log_file.rename(backup)

            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] {level}: {message}\n")
        except Exception as e:
            # If we can't log, at least try stderr
            print(f"Logging error: {e}", file=sys.stderr)

    def read_input(self) -> Dict[str, Any]:
        """Read and parse JSON input from stdin.

        Returns:
            Parsed JSON data as dictionary

        Raises:
            json.JSONDecodeError: If input is not valid JSON
        """
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            return {}
        return json.loads(raw_input)

    def write_output(self, output: Dict[str, Any]):
        """Write JSON output to stdout.

        Args:
            output: Dictionary to write as JSON
        """
        json.dump(output, sys.stdout)

    def save_metric(self, metric_name: str, value: Any, metadata: Optional[Dict] = None):
        """Save a metric to the metrics directory.

        Args:
            metric_name: Name of the metric
            value: Metric value
            metadata: Optional additional metadata
        """
        metrics_file = self.metrics_dir / f"{self.hook_name}_metrics.jsonl"

        metric = {
            "timestamp": datetime.now().isoformat(),
            "metric": metric_name,
            "value": value,
            "hook": self.hook_name,
        }

        if metadata:
            metric["metadata"] = metadata

        try:
            with open(metrics_file, "a") as f:
                f.write(json.dumps(metric) + "\n")
        except Exception as e:
            self.log(f"Failed to save metric: {e}", "WARNING")

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the hook input and return output.

        This method must be implemented by subclasses.

        Args:
            input_data: Input data from Claude Code

        Returns:
            Output data to return to Claude Code
        """

    def run(self):
        """Main entry point for the hook processor.

        Handles the full lifecycle:
        1. Read input from stdin
        2. Process the input
        3. Write output to stdout
        4. Handle any errors gracefully
        """
        try:
            # Log start
            self.log(f"{self.hook_name} hook starting")

            # Read input
            input_data = self.read_input()
            self.log(f"Received input with keys: {list(input_data.keys())}")

            # Process
            output = self.process(input_data)

            # Ensure output is a dict
            if output is None:
                output = {}
            elif not isinstance(output, dict):
                self.log(f"Warning: process() returned non-dict: {type(output)}", "WARNING")
                output = {"result": output}

            # Write output
            self.write_output(output)
            self.log(f"{self.hook_name} hook completed successfully")

        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON input: {e}", "ERROR")
            self.write_output({"error": "Invalid JSON input"})

        except Exception as e:
            # Log full traceback for debugging
            self.log(f"Error in {self.hook_name}: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")

            # Also log to stderr for visibility
            print(f"Hook error in {self.hook_name}: {e}", file=sys.stderr)

            # Return error indicator instead of empty dict
            error_response = {
                "error": f"Hook {self.hook_name} encountered an error",
                "details": str(e)[:200],  # Truncate for safety
            }
            self.write_output(error_response)

    def get_session_id(self) -> str:
        """Generate or retrieve a session ID.

        Returns:
            Session ID based on timestamp
        """
        # Include microseconds to prevent collisions
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def save_session_data(self, filename: str, data: Any):
        """Save data to a session-specific file with path validation.

        Args:
            filename: Name of the file (without path)
            data: Data to save (will be JSON serialized if dict/list)
        """
        # Validate filename to prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            self.log(f"Invalid filename attempted: {filename}", "WARNING")
            raise ValueError("Invalid filename - no path separators allowed")

        session_dir = self.log_dir / self.get_session_id()
        session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Restrict permissions

        file_path = session_dir / filename

        try:
            if isinstance(data, (dict, list)):
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
            else:
                with open(file_path, "w") as f:
                    f.write(str(data))

            self.log(f"Saved session data to {filename}")
        except Exception as e:
            self.log(f"Failed to save session data: {e}", "WARNING")
