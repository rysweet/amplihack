#!/usr/bin/env python3
"""
Analyze Codebase

Simple codebase analysis tool for comprehensive insights and recommendations.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for amplihack imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class CodebaseAnalyzer:
    """Simple codebase analysis tool."""

    def __init__(self):
        """Initialize analyzer."""
        self.skip_patterns = [".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"]
        self.max_file_size = 1024 * 1024  # 1MB

    def analyze(self, target_path: str, options: dict = None) -> dict[str, Any]:
        """
        Perform analysis of target codebase.

        Args:
            target_path: Directory or file to analyze
            options: Additional analysis options (depth, format, etc.)

        Returns:
            Analysis results with recommendations
        """
        start_time = datetime.now()
        options = options or {}

        # Validate input
        target = Path(target_path).resolve()
        if not target.exists():
            raise ValueError(f"Target path does not exist: {target_path}")

        # Analyze content
        content_map = self._discover_content(target)
        if not content_map:
            return {"message": "No analyzable content found", "files": 0}

        # Generate analysis
        result = self._analyze_content(content_map, start_time)

        # Format output
        return self._format_output(result, options)

    def _analyze_content(
        self, content_map: dict[str, list[Path]], start_time: datetime
    ) -> dict[str, Any]:
        """Analyze discovered content and generate insights."""
        total_files = sum(len(files) for files in content_map.values())
        total_lines = self._count_lines(content_map)

        # Basic analysis
        findings = []
        recommendations = []

        # File structure analysis
        if total_files > 50:
            findings.append(
                {"type": "structure", "message": f"Large codebase with {total_files} files"}
            )
            recommendations.append("Consider organizing code into smaller modules")

        # Language analysis
        if "python" in content_map and len(content_map["python"]) > 10:
            findings.append({"type": "quality", "message": "Python codebase detected"})
            recommendations.append("Ensure code follows PEP 8 style guidelines")

        # Security basic checks
        security_issues = 0
        for files in content_map.values():
            for file_path in files[:5]:  # Sample check
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if "password" in content.lower() or "api_key" in content.lower():
                        security_issues += 1
                except (OSError, PermissionError):
                    continue

        if security_issues > 0:
            findings.append(
                {
                    "type": "security",
                    "message": f"Found {security_issues} potential security concerns",
                }
            )
            recommendations.append("Review hardcoded credentials and sensitive data")

        return {
            "timestamp": start_time.isoformat(),
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "summary": {
                "files_analyzed": total_files,
                "total_lines": total_lines,
                "languages": list(content_map.keys()),
                "security_issues": security_issues,
            },
            "findings": findings,
            "recommendations": recommendations,
        }

    def _discover_content(self, target_path: Path) -> dict[str, list[Path]]:
        """Discover and categorize analyzable content."""
        content_map = {"python": [], "javascript": [], "yaml": [], "markdown": [], "other": []}

        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
        }

        if target_path.is_file():
            ext = target_path.suffix.lower()
            category = ext_map.get(ext, "other")
            content_map[category].append(target_path)
        else:
            for file_path in target_path.rglob("*"):
                if file_path.is_file() and not self._should_skip(file_path):
                    ext = file_path.suffix.lower()
                    category = ext_map.get(ext, "other")
                    content_map[category].append(file_path)

        return {k: v for k, v in content_map.items() if v}

    def _should_skip(self, file_path: Path) -> bool:
        """Determine if file should be skipped during analysis."""
        path_str = str(file_path)
        for pattern in self.skip_patterns:
            if pattern in path_str:
                return True

        try:
            if file_path.stat().st_size > self.max_file_size:
                return True
        except (OSError, PermissionError):
            return True

        return False

    def _count_lines(self, content_map: dict[str, list[Path]]) -> int:
        """Count total lines of code."""
        total_lines = 0
        for files in content_map.values():
            for file_path in files[:10]:  # Sample for performance
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        total_lines += len(f.readlines())
                except (OSError, PermissionError):
                    total_lines += 50  # Estimate

        # Scale up based on sampling
        total_files = sum(len(files) for files in content_map.values())
        sampled_files = min(10 * len(content_map), total_files)
        if sampled_files > 0:
            total_lines = int(total_lines * total_files / sampled_files)

        return total_lines

    def _format_output(self, result: dict[str, Any], options: dict) -> Any:
        """Format output according to user preferences."""
        if options.get("format") == "json":
            return result

        # Text format
        summary = result["summary"]
        lines = [
            "🔍 Codebase Analysis Results",
            "",
            "📊 Summary:",
            f"- Files analyzed: {summary['files_analyzed']}",
            f"- Total lines: {summary['total_lines']}",
            f"- Languages: {', '.join(summary['languages'])}",
        ]

        if summary.get("security_issues", 0) > 0:
            lines.append(f"- Security issues: {summary['security_issues']}")

        if result.get("recommendations"):
            lines.extend(["", "📋 Recommendations:"])
            for i, rec in enumerate(result["recommendations"][:5], 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze codebase for insights and recommendations"
    )
    parser.add_argument("target", help="Directory or file to analyze")
    parser.add_argument("--format", help="Output format (text/json)", default="text")
    parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    try:
        analyzer = CodebaseAnalyzer()
        result = analyzer.analyze(args.target, {"format": args.format})

        if args.output:
            with open(args.output, "w") as f:
                if args.format == "json":
                    json.dump(result, f, indent=2)
                else:
                    f.write(result)
            print(f"Analysis saved to: {args.output}")
        elif args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(result)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
