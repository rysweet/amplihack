#!/usr/bin/env python3
"""
Claude Code hook for post tool use events.
Uses unified HookProcessor for common functionality.
Includes quality checking for Write/Edit operations.
"""

# Import the base processor
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Import quality checker - gracefully handle if not available
try:
    # Add src to path to import amplihack modules
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    src_path = repo_root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))

    from amplihack.quality import QualityChecker
    QUALITY_AVAILABLE = True
except ImportError:
    QUALITY_AVAILABLE = False


class PostToolUseHook(HookProcessor):
    """Hook processor for post tool use events."""

    def __init__(self):
        super().__init__("post_tool_use")
        self.quality_checker = None
        if QUALITY_AVAILABLE:
            try:
                self.quality_checker = QualityChecker()
            except Exception as e:
                self.log(f"Failed to initialize quality checker: {e}", "WARNING")

    def save_tool_metric(self, tool_name: str, duration_ms: Optional[int] = None):
        """Save tool usage metric with structured data.

        Args:
            tool_name: Name of the tool used
            duration_ms: Duration in milliseconds (if available)
        """
        metadata = {}
        if duration_ms is not None:
            metadata["duration_ms"] = duration_ms

        self.save_metric("tool_usage", tool_name, metadata)

    def _extract_file_path(self, tool_use: Dict[str, Any]) -> Optional[Path]:
        """Extract file path from tool use parameters.

        Args:
            tool_use: Tool use data

        Returns:
            Path object or None if not found
        """
        params = tool_use.get("input", {})
        file_path = params.get("file_path") or params.get("path")

        if file_path:
            return Path(file_path)
        return None

    def _run_quality_checks(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Run quality checks on file.

        Args:
            file_path: Path to file to check

        Returns:
            Quality check results or None
        """
        if not self.quality_checker:
            return None

        try:
            result = self.quality_checker.check_file(file_path)
            if result and not result.passed and not result.skipped:
                # Format issues for output
                issues_text = []
                for issue in result.issues[:5]:  # Limit to first 5 issues
                    issues_text.append(str(issue))

                total_issues = len(result.issues)
                if total_issues > 5:
                    issues_text.append(f"... and {total_issues - 5} more issues")

                return {
                    "quality_check": {
                        "passed": False,
                        "validator": result.validator,
                        "error_count": result.error_count,
                        "warning_count": result.warning_count,
                        "issues": issues_text,
                        "message": f"Quality check found {result.error_count} errors and {result.warning_count} warnings",
                    }
                }

        except Exception as e:
            self.log(f"Quality check error: {e}", "WARNING")

        return None

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process post tool use event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict or validation messages
        """
        # Extract tool information
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")

        # Extract result if available (not currently used but could be useful)
        result = input_data.get("result", {})

        self.log(f"Tool used: {tool_name}")

        # Save metrics - could extract duration from result if available
        duration_ms = None
        if isinstance(result, dict):
            # Some tools might include timing information
            duration_ms = result.get("duration_ms")

        self.save_tool_metric(tool_name, duration_ms)

        # Check for specific tool types that might need validation
        output = {}
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            # Check if edits were successful
            if isinstance(result, dict) and result.get("error"):
                self.log(f"Tool {tool_name} reported error: {result.get('error')}", "WARNING")
                output["metadata"] = {
                    "warning": f"Tool {tool_name} encountered an error",
                    "tool": tool_name,
                }
            else:
                # Run quality checks on the modified file
                file_path = self._extract_file_path(tool_use)
                if file_path and file_path.exists():
                    quality_result = self._run_quality_checks(file_path)
                    if quality_result:
                        self.log(
                            f"Quality check failed for {file_path}: {quality_result['quality_check']['message']}",
                            "INFO"
                        )
                        # Add quality check results to output
                        output.update(quality_result)
                        # Save quality metrics
                        self.save_metric("quality_checks_failed", 1, {
                            "file": str(file_path),
                            "validator": quality_result["quality_check"]["validator"],
                            "errors": quality_result["quality_check"]["error_count"],
                            "warnings": quality_result["quality_check"]["warning_count"],
                        })

        # Track high-level metrics
        if tool_name == "Bash":
            self.save_metric("bash_commands", 1)
        elif tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
            self.save_metric("file_operations", 1)
        elif tool_name in ["Grep", "Glob"]:
            self.save_metric("search_operations", 1)

        return output


def main():
    """Entry point for the post tool use hook."""
    hook = PostToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
