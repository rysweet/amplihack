#!/usr/bin/env python3
"""
Claude Code hook for automatic formatting after Edit tool usage.
Detects when Edit tool is used and runs appropriate formatters.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from paths import get_project_root

    project_root = get_project_root()
except ImportError:
    # Fallback for standalone execution
    project_root = Path(__file__).parent.parent.parent.parent.parent

# Configuration
AUTO_FORMAT_ENV = "CLAUDE_AUTO_FORMAT"
LOG_DIR = project_root / ".claude" / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Language-specific formatters in order of preference
FORMATTERS = {
    ".py": [
        ("black", ["black", "--quiet", "{file}"]),
        ("ruff", ["ruff", "format", "--quiet", "{file}"]),
        ("autopep8", ["autopep8", "--in-place", "{file}"]),
    ],
    ".js": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("eslint", ["eslint", "--fix", "--quiet", "{file}"]),
    ],
    ".jsx": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("eslint", ["eslint", "--fix", "--quiet", "{file}"]),
    ],
    ".ts": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("eslint", ["eslint", "--fix", "--quiet", "{file}"]),
    ],
    ".tsx": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("eslint", ["eslint", "--fix", "--quiet", "{file}"]),
    ],
    ".json": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("jq", ["jq", ".", "{file}", "-M", "--indent", "2"]),
    ],
    ".md": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
        ("mdformat", ["mdformat", "{file}"]),
    ],
    ".yaml": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
    ".yml": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
    ".css": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
    ".scss": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
    ".html": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
    ".xml": [
        ("prettier", ["prettier", "--write", "--loglevel", "error", "{file}"]),
    ],
}

# Per-language configuration (can be extended via environment variables)
LANGUAGE_CONFIG = {
    ".py": os.environ.get("CLAUDE_FORMAT_PYTHON", "true").lower() == "true",
    ".js": os.environ.get("CLAUDE_FORMAT_JS", "true").lower() == "true",
    ".ts": os.environ.get("CLAUDE_FORMAT_TS", "true").lower() == "true",
    ".json": os.environ.get("CLAUDE_FORMAT_JSON", "true").lower() == "true",
    ".md": os.environ.get("CLAUDE_FORMAT_MD", "true").lower() == "true",
}


def log(message: str, level: str = "INFO"):
    """Simple logging to file"""
    timestamp = datetime.now().isoformat()
    log_file = LOG_DIR / "post_edit_format.log"

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {level}: {message}\n")


def is_formatting_enabled() -> bool:
    """Check if auto-formatting is enabled globally"""
    return os.environ.get(AUTO_FORMAT_ENV, "true").lower() != "false"


def is_language_enabled(extension: str) -> bool:
    """Check if formatting is enabled for a specific language"""
    return LANGUAGE_CONFIG.get(extension, True)


def command_exists(command: str) -> bool:
    """Check if a command exists in PATH"""
    try:
        subprocess.run(
            ["which", command],
            capture_output=True,
            check=False,
            timeout=1,
        )
        return (
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=False,
                timeout=1,
            ).returncode
            == 0
        )
    except (subprocess.SubprocessError, OSError):
        return False


def get_file_hash(file_path: Path) -> Optional[str]:
    """Get hash of file content for change detection"""
    try:
        import hashlib

        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def format_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Format a file with appropriate formatter.
    Returns (success, formatter_used)
    """
    if not file_path.exists():
        log(f"File does not exist: {file_path}")
        return False, None

    # Get file extension
    extension = file_path.suffix.lower()
    if extension not in FORMATTERS:
        log(f"No formatter configured for {extension}")
        return False, None

    # Check if formatting is enabled for this language
    if not is_language_enabled(extension):
        log(f"Formatting disabled for {extension}")
        return False, None

    # Get original file hash
    original_hash = get_file_hash(file_path)

    # Try formatters in order of preference
    for formatter_name, command_template in FORMATTERS[extension]:
        if not command_exists(formatter_name):
            continue

        # Build command safely - avoid shell injection
        command = []
        for arg in command_template:
            if arg == "{file}":
                # Replace placeholder with actual file path as separate argument
                command.append(str(file_path))
            elif "{file}" in arg:
                # Don't allow partial replacements that could enable injection
                log(f"Skipping unsafe formatter command template: {command_template}", "WARNING")
                continue
            else:
                command.append(arg)

        try:
            log(f"Running {formatter_name} on {file_path}")

            # Special handling for jq (needs to write output)
            if formatter_name == "jq":
                # Use shell=False to prevent injection
                result = subprocess.run(
                    command, check=False, capture_output=True, text=True, timeout=10, shell=False
                )
                if result.returncode == 0:
                    # Write formatted output back to file
                    with open(file_path, "w") as f:
                        f.write(result.stdout)
                else:
                    continue
            else:
                # Run formatter with shell=False to prevent injection
                result = subprocess.run(
                    command, check=False, capture_output=True, text=True, timeout=10, shell=False
                )

                if result.returncode != 0:
                    log(f"{formatter_name} failed: {result.stderr}")
                    continue

            # Check if file was modified
            new_hash = get_file_hash(file_path)
            if original_hash and new_hash and original_hash != new_hash:
                log(f"File formatted with {formatter_name}: {file_path}")
                return True, formatter_name
            log(f"No changes needed by {formatter_name}: {file_path}")
            return True, formatter_name

        except subprocess.TimeoutExpired:
            log(f"{formatter_name} timed out", "WARNING")
            continue
        except Exception as e:
            log(f"Error running {formatter_name}: {e}", "ERROR")
            continue

    log(f"No available formatter found for {file_path}", "WARNING")
    return False, None


def extract_edited_files(tool_use: Dict) -> List[Path]:
    """Extract file paths from Edit/MultiEdit tool usage"""
    edited_files = []
    tool_name = tool_use.get("name", "")

    if tool_name == "Edit":
        # Single file edit
        file_path = tool_use.get("parameters", {}).get("file_path")
        if file_path:
            edited_files.append(Path(file_path))

    elif tool_name == "MultiEdit":
        # Multiple edits to same file
        file_path = tool_use.get("parameters", {}).get("file_path")
        if file_path:
            edited_files.append(Path(file_path))

    elif tool_name == "Write":
        # File write/creation
        file_path = tool_use.get("parameters", {}).get("file_path")
        if file_path:
            edited_files.append(Path(file_path))

    elif tool_name == "NotebookEdit":
        # Jupyter notebook edit
        notebook_path = tool_use.get("parameters", {}).get("notebook_path")
        if notebook_path:
            edited_files.append(Path(notebook_path))

    return edited_files


def main():
    """Process post tool use event"""
    try:
        # Check if formatting is enabled
        if not is_formatting_enabled():
            log("Auto-formatting is disabled")
            json.dump({}, sys.stdout)
            return

        # Read input
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        # Extract tool information
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")

        # Only process Edit-related tools
        if tool_name not in ["Edit", "MultiEdit", "Write", "NotebookEdit"]:
            json.dump({}, sys.stdout)
            return

        log(f"Processing {tool_name} tool usage")

        # Extract edited files
        edited_files = extract_edited_files(tool_use)

        if not edited_files:
            log("No files to format")
            json.dump({}, sys.stdout)
            return

        # Format each file
        formatted_files = []
        formatters_used = {}

        for file_path in edited_files:
            success, formatter = format_file(file_path)
            if success and formatter:
                formatted_files.append(str(file_path))
                formatters_used[str(file_path)] = formatter

        # Prepare output
        output = {}
        if formatted_files:
            # Create user-friendly message
            messages = []
            for file in formatted_files:
                formatter = formatters_used.get(file, "formatter")
                messages.append(f"  • {Path(file).name} (formatted with {formatter})")

            if messages:
                output["message"] = f"Auto-formatted {len(formatted_files)} file(s):\n" + "\n".join(
                    messages
                )
                output["formatted_files"] = formatted_files
                output["formatters"] = formatters_used

        # Return output
        json.dump(output, sys.stdout)

    except json.JSONDecodeError as e:
        log(f"Invalid JSON input: {e}", "ERROR")
        json.dump({}, sys.stdout)
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
