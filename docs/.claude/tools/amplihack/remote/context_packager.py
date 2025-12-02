"""Context packaging with secret scanning.

This module handles creating secure archives of project context for remote execution.
It implements multi-layer secret detection and exclusion of sensitive files.
"""

import re
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import PackagingError


@dataclass
class SecretMatch:
    """Represents a detected secret in source files."""

    file_path: str
    line_number: int
    line_content: str
    pattern_name: str


# Secret detection patterns - comprehensive coverage
SECRET_PATTERNS = {
    "anthropic_key": r'ANTHROPIC_API_KEY\s*=\s*["\']sk-ant-[^"\']+["\']',
    "openai_key": r'OPENAI_API_KEY\s*=\s*["\']sk-[^"\']+["\']',
    "anthropic_key_generic": r"sk-ant-[a-zA-Z0-9\-_]{20,}",
    "openai_key_generic": r"sk-[a-zA-Z0-9\-_]{20,}",
    "github_pat": r"ghp_[a-zA-Z0-9]{36}",
    "azure_key": r'AZURE_[A-Z_]*KEY\s*=\s*["\'][^"\']+["\']',
    "aws_key": r'AWS_[A-Z_]*KEY\s*=\s*["\'][^"\']+["\']',
    "api_key_generic": r'api[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']',
    "password": r'password\s*[=:]\s*["\'][^"\']+["\']',
    "token": r'token\s*[=:]\s*["\'][^"\']{20,}["\']',
    "bearer_token": r"[Bb]earer\s+[a-zA-Z0-9\-_\.]{20,}",
}

# File patterns to always exclude
EXCLUDED_PATTERNS = [
    ".env*",
    "*credentials*",  # Credential files
    "*secret*",  # Secret files
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    ".ssh/*",
    ".aws/*",
    ".azure/*",
    ".config/gh/*",
    "node_modules/*",
    "__pycache__/*",
    ".venv/*",
    "venv/*",
    "*.pyc",
    ".git/*",
    ".DS_Store",
]


class ContextPackager:
    """Packages project context for remote execution.

    This class creates a secure, minimal archive containing:
    - Git repository state (via git bundle)
    - .claude directory
    - Essential configuration files

    It explicitly excludes sensitive files and scans for hardcoded secrets.
    """

    def __init__(self, repo_path: Path, max_size_mb: int = 500, skip_secret_scan: bool = False):
        """Initialize context packager.

        Args:
            repo_path: Path to git repository root
            max_size_mb: Maximum archive size in megabytes (default: 500)
        """
        self.repo_path = Path(repo_path).resolve()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.skip_secret_scan = skip_secret_scan
        self.temp_dir: Path | None = None

    def scan_secrets(self) -> list[SecretMatch]:
        """Scan repository for hardcoded secrets.

        Returns:
            List of SecretMatch objects for detected secrets

        Raises:
            PackagingError: If scanning fails
        """
        matches: list[SecretMatch] = []

        try:
            # Get list of tracked files
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            files = result.stdout.strip().split("\n")
        except subprocess.CalledProcessError as e:
            raise PackagingError(
                f"Failed to list git files: {e.stderr}", context={"repo_path": str(self.repo_path)}
            )
        except subprocess.TimeoutExpired:
            raise PackagingError(
                "Git ls-files command timed out", context={"repo_path": str(self.repo_path)}
            )

        # Scan each file
        for rel_path in files:
            file_path = self.repo_path / rel_path

            # Skip binary files and excluded patterns
            if not file_path.is_file():
                continue
            if self._is_excluded(rel_path):
                continue
            if self._is_binary(file_path):
                continue

            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        # Check against all patterns
                        for pattern_name, pattern in SECRET_PATTERNS.items():
                            if re.search(pattern, line, re.IGNORECASE):
                                matches.append(
                                    SecretMatch(
                                        file_path=rel_path,
                                        line_number=line_num,
                                        line_content=line.strip()[:100],  # Truncate long lines
                                        pattern_name=pattern_name,
                                    )
                                )
            except (OSError, UnicodeDecodeError, PermissionError) as e:
                # Non-fatal: file may be binary, inaccessible, or corrupted
                print(f"Warning: Could not scan {rel_path}: {e}")

        return matches

    def create_bundle(self) -> Path:
        """Create git bundle with all branches and history.

        Returns:
            Path to created bundle file

        Raises:
            PackagingError: If bundle creation fails
        """
        if not self.temp_dir:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="amplihack-remote-"))

        bundle_path = self.temp_dir / "repo.bundle"

        try:
            subprocess.run(
                ["git", "bundle", "create", str(bundle_path), "--all"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minutes for large repos
            )
        except subprocess.CalledProcessError as e:
            raise PackagingError(
                f"Failed to create git bundle: {e.stderr}",
                context={"repo_path": str(self.repo_path)},
            )
        except subprocess.TimeoutExpired:
            raise PackagingError(
                "Git bundle creation timed out (>5 minutes)",
                context={"repo_path": str(self.repo_path)},
            )

        # Verify bundle was created and is valid
        if not bundle_path.exists():
            raise PackagingError(
                "Git bundle file not created", context={"expected_path": str(bundle_path)}
            )

        # Verify bundle is valid
        try:
            subprocess.run(
                ["git", "bundle", "verify", str(bundle_path)],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as e:
            raise PackagingError(
                f"Git bundle verification failed: {e.stderr}",
                context={"bundle_path": str(bundle_path)},
            )

        return bundle_path

    def package(self) -> Path:
        """Create complete context archive.

        Returns:
            Path to context.tar.gz archive

        Raises:
            PackagingError: If packaging fails or secrets detected
        """
        # Step 1: Scan for secrets (unless skipped)
        if not self.skip_secret_scan:
            secrets = self.scan_secrets()
            if secrets:
                error_details = "\n".join(
                    f"  - {s.file_path}:{s.line_number} ({s.pattern_name}): {s.line_content}"
                    for s in secrets[:10]  # Show first 10
                )
                if len(secrets) > 10:
                    error_details += f"\n  ... and {len(secrets) - 10} more"

                raise PackagingError(
                    f"Detected {len(secrets)} potential secret(s) in repository:\n{error_details}\n\n"
                    "Action required:\n"
                    "  1. Remove hardcoded secrets from source files\n"
                    "  2. Add secrets to .env file (automatically excluded)\n"
                    "  3. Retry remote execution\n",
                    context={"secret_count": len(secrets)},
                )
        else:
            print("  ⚠ Secret scan skipped (skip_secret_scan=True)")

        # Step 2: Create git bundle
        bundle_path = self.create_bundle()

        # Step 3: Create .claude archive
        claude_dir = self.repo_path / ".claude"
        if not claude_dir.exists():
            raise PackagingError(
                ".claude directory not found in repository",
                context={"repo_path": str(self.repo_path)},
            )

        # Step 4: Create combined archive
        archive_path = self.temp_dir / "context.tar.gz"

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add git bundle
                tar.add(bundle_path, arcname="repo.bundle")

                # Add .claude directory (with exclusions)
                tar.add(claude_dir, arcname=".claude", filter=self._tar_filter)

        except Exception as e:
            raise PackagingError(
                f"Failed to create tar archive: {e!s}", context={"archive_path": str(archive_path)}
            )

        # Step 5: Verify archive size
        archive_size = archive_path.stat().st_size
        if archive_size > self.max_size_bytes:
            raise PackagingError(
                f"Archive size ({archive_size / 1024 / 1024:.1f} MB) exceeds limit "
                f"({self.max_size_bytes / 1024 / 1024:.1f} MB)",
                context={"archive_size": archive_size, "limit": self.max_size_bytes},
            )

        return archive_path

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

    def _is_excluded(self, path: str) -> bool:
        """Check if path matches exclusion patterns."""
        from fnmatch import fnmatch

        return any(fnmatch(path, pattern) for pattern in EXCLUDED_PATTERNS)

    def _is_binary(self, file_path: Path) -> bool:
        """Check if file is binary (simple heuristic)."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                # Check for null bytes (common in binary files)
                return b"\x00" in chunk
        except (OSError, PermissionError):
            # If we can't read it, treat as binary to skip secret scanning
            return True

    def _tar_filter(self, tarinfo):
        """Filter function for tar.add() to exclude sensitive files."""
        # Get relative path from .claude
        rel_path = tarinfo.name.replace(".claude/", "", 1)

        # Exclude patterns
        if self._is_excluded(rel_path):
            return None

        # Exclude logs directory (will be recreated remotely)
        if "runtime/logs" in rel_path:
            return None

        return tarinfo

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files."""
        self.cleanup()
