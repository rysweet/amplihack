"""Utility functions for E2E Outside-In Test Generator.

Shared utilities used across multiple modules.
"""

import json
import re
from pathlib import Path
from typing import Any

from .security import read_json_safe, validate_project_root


def find_files(root: Path, pattern: str) -> list[Path]:
    """Find files matching glob pattern recursively.

    Args:
        root: Root directory to search
        pattern: Glob pattern (e.g., "*.ts", "**/*.py")

    Returns:
        List of matching file paths
    """
    if not root.exists():
        return []
    return list(root.glob(pattern)) if "**" in pattern else list(root.glob(f"**/{pattern}"))


def read_json_file(file_path: Path) -> dict[str, Any]:
    """Read and parse JSON file with security validation.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        SecurityError: If file is too large or path is invalid
        ValueError: If JSON is invalid
    """
    # Use secure JSON reading with size limits
    return read_json_safe(file_path, max_size_mb=10)


def write_json_file(file_path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Write data to JSON file.

    Args:
        file_path: Path to write to
        data: Data to write
        indent: JSON indentation level
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)


def read_file(file_path: Path) -> str:
    """Read file contents as string with path validation.

    Args:
        file_path: Path to file

    Returns:
        File contents

    Raises:
        FileNotFoundError: If file doesn't exist
        SecurityError: If path is outside project boundaries
    """
    # Validate path is within allowed boundaries
    validated_path = validate_project_root(file_path)
    with open(validated_path, encoding="utf-8") as f:
        return f.read()


def write_file(file_path: Path, content: str) -> None:
    """Write string content to file with path validation.

    Args:
        file_path: Path to write to
        content: Content to write

    Raises:
        SecurityError: If path is outside project boundaries
    """
    # Validate path is within allowed boundaries
    validated_path = validate_project_root(file_path)
    validated_path.parent.mkdir(parents=True, exist_ok=True)
    with open(validated_path, "w", encoding="utf-8") as f:
        f.write(content)


def extract_imports(file_content: str) -> list[str]:
    """Extract import statements from JavaScript/TypeScript file.

    Args:
        file_content: File content

    Returns:
        List of imported module names
    """
    imports = []
    # Match: import ... from 'module' or import ... from "module"
    import_pattern = re.compile(r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]")
    matches = import_pattern.findall(file_content)
    imports.extend(matches)

    # Match: import('module') - dynamic imports
    dynamic_pattern = re.compile(r"import\(['\"]([^'\"]+)['\"]\)")
    matches = dynamic_pattern.findall(file_content)
    imports.extend(matches)

    return imports


def extract_exports(file_content: str) -> list[str]:
    """Extract export statements from JavaScript/TypeScript file.

    Args:
        file_content: File content

    Returns:
        List of exported identifiers
    """
    exports = []
    # Match: export const/function/class NAME
    export_pattern = re.compile(r"export\s+(?:const|function|class|interface|type)\s+(\w+)")
    matches = export_pattern.findall(file_content)
    exports.extend(matches)

    # Match: export { name1, name2 }
    export_list_pattern = re.compile(r"export\s+\{([^}]+)\}")
    matches = export_list_pattern.findall(file_content)
    for match in matches:
        names = [name.strip().split()[0] for name in match.split(",")]
        exports.extend(names)

    return exports


def parse_route_from_file(file_path: Path, framework: str) -> str | None:
    """Parse route path from file path based on framework conventions.

    Args:
        file_path: Path to route file
        framework: Frontend framework (nextjs, react, vue, angular)

    Returns:
        Route path or None if not a route file
    """
    if framework == "nextjs":
        # Next.js app router: app/dashboard/page.tsx -> /dashboard
        # Next.js pages router: pages/dashboard.tsx -> /dashboard
        if "app" in file_path.parts:
            route_parts = []
            found_app = False
            for part in file_path.parts:
                if found_app and part != "page.tsx" and part != "layout.tsx":
                    route_parts.append(part)
                if part == "app":
                    found_app = True
            return "/" + "/".join(route_parts) if route_parts else "/"
        if "pages" in file_path.parts:
            route_parts = []
            found_pages = False
            for part in file_path.parts:
                if found_pages:
                    route_parts.append(part.replace(".tsx", "").replace(".jsx", ""))
                if part == "pages":
                    found_pages = True
            route = "/" + "/".join(route_parts)
            return route.replace("/index", "") or "/"

    elif framework == "react":
        # React Router typically in src/routes or src/pages
        if "routes" in file_path.parts or "pages" in file_path.parts:
            return "/" + file_path.stem.lower()

    elif framework == "vue":
        # Vue Router typically in src/views or src/pages
        if "views" in file_path.parts or "pages" in file_path.parts:
            return "/" + file_path.stem.lower()

    elif framework == "angular":
        # Angular routes typically in src/app/*-routing.module.ts
        if "routing" in file_path.stem:
            return None  # Angular routes need content parsing

    return None


def sanitize_test_name(name: str) -> str:
    """Sanitize string for use as test name.

    Args:
        name: Original name

    Returns:
        Sanitized name safe for test descriptions
    """
    # Replace special characters with spaces
    name = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)
    # Capitalize first letter
    return name.strip().capitalize()


def calculate_coverage_percent(covered: int, total: int) -> float:
    """Calculate coverage percentage.

    Args:
        covered: Number of covered items
        total: Total number of items

    Returns:
        Coverage percentage (0.0 to 100.0)
    """
    if total == 0:
        return 0.0
    return (covered / total) * 100.0


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1m 30s", "45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if needed.

    Args:
        path: Directory path

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_path(path: Path, base: Path) -> Path:
    """Get relative path from base.

    Args:
        path: Absolute path
        base: Base path

    Returns:
        Relative path from base to path
    """
    try:
        return path.relative_to(base)
    except ValueError:
        return path


def count_lines(file_path: Path) -> int:
    """Count lines in file.

    Args:
        file_path: Path to file

    Returns:
        Number of lines
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except (FileNotFoundError, UnicodeDecodeError):
        return 0


def is_test_file(file_path: Path) -> bool:
    """Check if file is a test file.

    Args:
        file_path: Path to file

    Returns:
        True if file is a test file
    """
    test_patterns = [".test.", ".spec.", "_test.", "_spec."]
    return any(pattern in file_path.name for pattern in test_patterns)


def parse_package_json(project_root: Path) -> dict[str, Any] | None:
    """Parse package.json if it exists.

    Args:
        project_root: Project root directory

    Returns:
        Parsed package.json or None if not found
    """
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            return read_json_file(package_json)
        except json.JSONDecodeError:
            return None
    return None


def get_framework_from_dependencies(dependencies: dict[str, Any]) -> str | None:
    """Detect framework from package.json dependencies.

    Args:
        dependencies: Combined dependencies from package.json

    Returns:
        Framework name or None
    """
    if "next" in dependencies:
        return "nextjs"
    if "react" in dependencies:
        return "react"
    if "vue" in dependencies:
        return "vue"
    if "@angular/core" in dependencies:
        return "angular"
    if "svelte" in dependencies:
        return "svelte"
    return None
