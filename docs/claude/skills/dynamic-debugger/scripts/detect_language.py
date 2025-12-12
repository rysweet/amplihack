#!/usr/bin/env python3
"""Language detection for debugging sessions.

Detects project language from:
1. Manifest files (package.json, Cargo.toml, go.mod, etc.)
2. File extension distribution
3. Git repository analysis

Returns confidence score and detected language.

Public API:
    detect_language(project_dir) -> (language, confidence)
    get_debugger_for_language(language) -> debugger_name
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Tuple

# Public API
__all__ = ["detect_language", "get_debugger_for_language"]

# Manifest file → language mapping
MANIFEST_MAP = {
    "package.json": "javascript",
    "tsconfig.json": "typescript",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "Pipfile": "python",
    "setup.py": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "CMakeLists.txt": "cpp",
    "Makefile": "c",
    "pom.xml": "java",
    "build.gradle": "java",
    ".csproj": "csharp",
    ".sln": "csharp",
}

# Extension → language mapping
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".java": "java",
    ".cs": "csharp",
    ".csx": "csharp",
    ".vb": "csharp",
}


def detect_language(project_dir: str = ".") -> Tuple[str, float]:
    """Detect project language with confidence score.

    Returns:
        (language, confidence) where confidence is 0.0-1.0
    """
    path = Path(project_dir).resolve()

    if not path.exists():
        print(f"ERROR: Project directory not found: {path}", file=sys.stderr)
        print("Please verify the path exists and try again.", file=sys.stderr)
        return ("unknown", 0.0)

    # Check manifest files (highest confidence)
    for manifest, lang in MANIFEST_MAP.items():
        if (path / manifest).exists():
            return (lang, 0.95)

    # Check file extensions (medium confidence)
    extensions = Counter()

    # Exclude common non-source directories
    exclude_dirs = {".git", ".venv", "node_modules", "target", "build", "dist", "__pycache__"}

    for ext, lang in EXTENSION_MAP.items():
        count = 0
        try:
            for file_path in path.rglob(f"*{ext}"):
                # Skip excluded directories
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                if file_path.is_file():
                    count += 1
        except (PermissionError, OSError):
            continue

        if count > 0:
            extensions[lang] += count

    if extensions:
        most_common_lang, count = extensions.most_common(1)[0]
        total = sum(extensions.values())
        confidence = min(0.85, count / total)
        return (most_common_lang, confidence)

    # No detection possible
    return ("unknown", 0.0)


def get_debugger_for_language(language: str) -> str:
    """Get recommended debugger for language (dap-mcp supported only).

    Currently supported by dap-mcp:
    - python: debugpy
    - c/cpp/rust: lldb

    See issue #1570 for planned language support.
    """
    debugger_map = {
        "python": "debugpy",
        "c": "lldb",
        "cpp": "lldb",
        "rust": "lldb",
    }
    return debugger_map.get(language, "unsupported")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Detect project language")
    parser.add_argument("--path", default=".", help="Project path to analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    lang, conf = detect_language(args.path)
    debugger = get_debugger_for_language(lang)

    if args.json:
        result = {"language": lang, "confidence": round(conf, 2), "debugger": debugger}
        print(json.dumps(result, indent=2))
    else:
        print(f"Language: {lang}")
        print(f"Confidence: {conf:.0%}")
        print(f"Debugger: {debugger}")
