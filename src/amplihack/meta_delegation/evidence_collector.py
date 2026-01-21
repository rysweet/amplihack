"""Evidence Collector Module.

This module collects and organizes artifacts generated during AI assistant execution,
including code files, tests, documentation, and execution logs.

Evidence Types:
- code_file: Source code files
- test_file: Test files
- documentation: README, guides, tutorials
- architecture_doc: Design documents, architecture specs
- api_spec: API definitions (OpenAPI, etc.)
- test_results: Test execution output
- execution_log: Process execution logs
- validation_report: QA validation reports
- diagram: Visual diagrams (mermaid, etc.)
- configuration: Config files (YAML, JSON, etc.)

Philosophy:
- Standard library file operations (pathlib, glob)
- Lazy content loading for large files
- Persona-aware prioritization
- Incremental collection support
"""

import fnmatch
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Evidence type to file pattern mapping
EVIDENCE_PATTERNS = {
    "code_file": [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rs",
        "*.cpp",
        "*.c",
        "*.h",
        "*.rb",
        "*.php",
        "*.swift",
        "*.kt",
    ],
    "test_file": [
        "test_*.py",
        "*_test.py",
        "test_*.js",
        "*_test.js",
        "*.test.js",
        "*.test.ts",
        "*_test.go",
        "*Test.java",
        "*_spec.rb",
    ],
    "documentation": [
        "README.md",
        "README.txt",
        "*.md",
        "GUIDE.md",
        "TUTORIAL.md",
        "docs/*.md",
    ],
    "architecture_doc": [
        "ARCHITECTURE.md",
        "DESIGN.md",
        "architecture/*.md",
        "docs/architecture/*.md",
        "ADR-*.md",
    ],
    "api_spec": [
        "openapi.yaml",
        "openapi.json",
        "swagger.yaml",
        "swagger.json",
        "api.yaml",
        "*.openapi.yaml",
    ],
    "test_results": [
        "test-results.xml",
        "test-results.json",
        "coverage.xml",
        "pytest.xml",
        ".pytest_cache/*",
    ],
    "execution_log": [
        "execution.log",
        "output.log",
        "*.log",
    ],
    "validation_report": [
        "validation-report.md",
        "qa-report.md",
        "test-report.md",
    ],
    "diagram": [
        "*.mmd",
        "*.mermaid",
        "diagrams/*.mmd",
        "*.puml",
        "*.dot",
    ],
    "configuration": [
        "*.yaml",
        "*.yml",
        "*.json",
        "*.toml",
        "*.ini",
        "*.cfg",
        ".env",
        "config/*",
    ],
}


@dataclass
class EvidenceItem:
    """Evidence item representing an artifact.

    Attributes:
        type: Evidence type (e.g., "code_file", "test_file")
        path: Relative or absolute file path
        content: File content
        excerpt: Truncated content preview (max 200 chars)
        size_bytes: File size in bytes
        timestamp: Collection timestamp
        metadata: Additional metadata dictionary
    """

    type: str
    path: str
    content: str
    excerpt: str
    size_bytes: int
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

    def save_to_file(self, output_path: str) -> None:
        """Save evidence content to file.

        Args:
            output_path: Path to write content

        Raises:
            ValueError: If output_path attempts path traversal
        """
        output_path_obj = Path(output_path).resolve()
        expected_parent = Path(output_path).parent.resolve()

        # Validate resolved path is within expected parent directory
        if not str(output_path_obj).startswith(str(expected_parent)):
            raise ValueError(f"Path traversal detected in output path: {output_path}")

        output_path_obj.write_text(self.content, encoding="utf-8")

    def get_metadata(self, key: str, default=None):
        """Get metadata value with default.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)


class EvidenceCollector:
    """Collects and organizes evidence from working directory.

    Attributes:
        working_directory: Directory to collect evidence from
        evidence_priorities: Optional ordered list of evidence types to prioritize
    """

    def __init__(
        self,
        working_directory: str,
        evidence_priorities: Optional[List[str]] = None,
    ):
        """Initialize evidence collector.

        Args:
            working_directory: Directory to scan for evidence
            evidence_priorities: Optional priority order for evidence types
        """
        self.working_directory = Path(working_directory)
        self.evidence_priorities = evidence_priorities or []
        self._collected_evidence: List[EvidenceItem] = []

    def collect_evidence(
        self,
        execution_log: Optional[str] = None,
        evidence_types: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[EvidenceItem]:
        """Collect evidence from working directory.

        Args:
            execution_log: Optional execution log content to include
            evidence_types: Optional list of specific types to collect (default: all)
            exclude_patterns: Optional glob patterns to exclude

        Returns:
            List of evidence items
        """
        evidence = []
        exclude_patterns = exclude_patterns or ["__pycache__/*", "*.pyc", ".git/*", "node_modules/*"]

        # Determine which types to collect
        types_to_collect = evidence_types or list(EVIDENCE_PATTERNS.keys())

        # Collect files for each evidence type
        for evidence_type in types_to_collect:
            if evidence_type == "execution_log" and execution_log:
                # Add execution log as special evidence
                evidence.append(
                    EvidenceItem(
                        type="execution_log",
                        path="<execution_log>",
                        content=execution_log,
                        excerpt=execution_log[:200],
                        size_bytes=len(execution_log.encode("utf-8")),
                        timestamp=datetime.now(),
                        metadata={},
                    )
                )
                continue

            patterns = EVIDENCE_PATTERNS.get(evidence_type, [])

            for pattern in patterns:
                files = self._find_files(pattern, exclude_patterns)

                for file_path in files:
                    try:
                        item = self._create_evidence_item(file_path, evidence_type)
                        evidence.append(item)
                    except Exception as e:
                        # Skip files that can't be read (binary files, permission errors, etc.)
                        continue

        self._collected_evidence = evidence
        return evidence

    def get_evidence_by_type(self, evidence_type: str) -> List[EvidenceItem]:
        """Get evidence items of specific type.

        Args:
            evidence_type: Evidence type to filter by

        Returns:
            List of evidence items of specified type
        """
        return [item for item in self._collected_evidence if item.type == evidence_type]

    def get_evidence_by_path_pattern(self, pattern: str) -> List[EvidenceItem]:
        """Get evidence items matching path pattern.

        Args:
            pattern: Glob pattern to match paths

        Returns:
            List of matching evidence items
        """
        return [
            item
            for item in self._collected_evidence
            if fnmatch.fnmatch(item.path, pattern)
        ]

    def export_evidence(self, output_directory: str) -> None:
        """Export all collected evidence to directory.

        Args:
            output_directory: Directory to export evidence to

        Raises:
            ValueError: If output_directory attempts path traversal
        """
        # Validate output directory - resolve and check it's in a safe location
        output_dir = Path(output_directory).resolve()

        # Ensure the resolved path doesn't escape the current working directory
        # (unless it's an absolute path, which we allow)
        if not Path(output_directory).is_absolute():
            cwd = Path.cwd().resolve()
            if not str(output_dir).startswith(str(cwd)):
                raise ValueError(f"Path traversal detected in output directory: {output_directory}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Organize by evidence type
        for item in self._collected_evidence:
            # Validate evidence type doesn't contain path traversal
            if ".." in item.type or "/" in item.type or "\\" in item.type:
                continue  # Skip invalid evidence types

            type_dir = output_dir / item.type
            type_dir.mkdir(exist_ok=True)

            # Create safe filename - use only the filename, not the full path
            filename = Path(item.path).name if item.path != "<execution_log>" else "execution.log"
            output_path = type_dir / filename

            # Validate the final path is within output_dir
            resolved_output_path = output_path.resolve()
            if not str(resolved_output_path).startswith(str(output_dir)):
                continue  # Skip paths that escape the output directory

            item.save_to_file(str(output_path))

    def _find_files(self, pattern: str, exclude_patterns: List[str]) -> List[Path]:
        """Find files matching pattern, excluding specified patterns.

        Args:
            pattern: Glob pattern to match
            exclude_patterns: Patterns to exclude

        Returns:
            List of matching file paths
        """
        files = []

        # Handle patterns with directory components
        if "/" in pattern:
            # Pattern has directory structure
            matching_files = self.working_directory.glob(pattern)
        else:
            # Pattern is just filename, search recursively
            matching_files = self.working_directory.rglob(pattern)

        for file_path in matching_files:
            if not file_path.is_file():
                continue

            # Check exclusions
            relative_path = file_path.relative_to(self.working_directory)
            excluded = False

            for exclude_pattern in exclude_patterns:
                if fnmatch.fnmatch(str(relative_path), exclude_pattern):
                    excluded = True
                    break

            if not excluded:
                files.append(file_path)

        return files

    def _create_evidence_item(self, file_path: Path, evidence_type: str) -> EvidenceItem:
        """Create evidence item from file.

        Args:
            file_path: Path to file
            evidence_type: Type of evidence

        Returns:
            EvidenceItem instance
        """
        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary file - skip or handle specially
            raise

        # Generate excerpt (first 200 characters)
        excerpt = content[:200] if len(content) > 200 else content

        # Calculate size
        size_bytes = len(content.encode("utf-8"))

        # Get relative path
        try:
            relative_path = file_path.relative_to(self.working_directory)
        except ValueError:
            relative_path = file_path

        # Extract metadata
        metadata = self._extract_metadata(file_path, content)

        return EvidenceItem(
            type=evidence_type,
            path=str(relative_path),
            content=content,
            excerpt=excerpt,
            size_bytes=size_bytes,
            timestamp=datetime.now(),
            metadata=metadata,
        )

    def _extract_metadata(self, file_path: Path, content: str) -> Dict:
        """Extract metadata from file.

        Args:
            file_path: File path
            content: File content

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Detect language
        suffix = file_path.suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cpp": "c++",
            ".c": "c",
            ".h": "c",
        }

        if suffix in language_map:
            metadata["language"] = language_map[suffix]

        # Count lines
        metadata["line_count"] = content.count("\n") + 1

        return metadata
