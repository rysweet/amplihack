"""Update manager for agent bundles with framework version tracking."""

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import BundleGeneratorError


@dataclass
class UpdateInfo:
    """Information about available updates."""

    available: bool
    current_version: str
    latest_version: str
    changes: List[str]


@dataclass
class UpdateResult:
    """Result of bundle update operation."""

    success: bool
    updated_files: List[str]
    preserved_files: List[str]
    conflicts: List[str]
    error: Optional[str] = None


class UpdateManager:
    """Manages bundle updates from upstream framework."""

    def __init__(self, framework_repo_path: Optional[Path] = None):
        """Initialize update manager.

        Args:
            framework_repo_path: Path to amplihack framework repository  # noqa
                               (defaults to parent of this file)
        """
        if framework_repo_path is None:
            # Default to the amplihack repo containing this code
            self.framework_repo = Path(__file__).parent.parent.parent.parent
        else:
            self.framework_repo = framework_repo_path

    def check_for_updates(self, bundle_path: Path) -> UpdateInfo:
        """Check if updates are available for bundle.

        Args:
            bundle_path: Path to bundle directory

        Returns:
            UpdateInfo with current and latest versions

        Raises:
            BundleGeneratorError: If manifest unreadable or repo unavailable
        """
        # Load current version from manifest
        manifest_path = bundle_path / "manifest.json"
        if not manifest_path.exists():
            raise BundleGeneratorError(
                f"Manifest not found: {manifest_path}",
                recovery_suggestion="Ensure this is a valid bundle directory",
            )

        with open(manifest_path) as f:
            manifest = json.load(f)

        current_version = manifest.get("framework", {}).get("version", "unknown")

        # Get latest version from framework repo
        try:
            latest_version = self._get_framework_version()
        except Exception as e:
            raise BundleGeneratorError(
                f"Could not detect framework version: {e}",
                recovery_suggestion="Ensure framework repository is accessible",
            )

        # Get changelog if versions differ
        changes = []
        if current_version != latest_version:
            try:
                changes = self._get_changelog(current_version, latest_version)
            except Exception:
                changes = ["Changelog unavailable"]

        return UpdateInfo(
            available=(current_version != latest_version),
            current_version=current_version,
            latest_version=latest_version,
            changes=changes,
        )

    def update_bundle(
        self, bundle_path: Path, preserve_edits: bool = True, backup: bool = True
    ) -> UpdateResult:
        """Update bundle with latest framework version.

        Args:
            bundle_path: Path to bundle directory
            preserve_edits: Whether to preserve user-modified files
            backup: Whether to create backup before updating

        Returns:
            UpdateResult with details of update operation

        Raises:
            BundleGeneratorError: If update fails
        """
        updated_files = []
        preserved_files = []
        conflicts = []

        try:
            # Create backup if requested
            if backup:
                backup_path = self._create_backup(bundle_path)
                print(f"Created backup: {backup_path}")

            # Load manifest and checksums
            manifest_path = bundle_path / "manifest.json"
            with open(manifest_path) as f:
                manifest = json.load(f)

            checksums = manifest.get("file_checksums", {})

            # Detect customizations if preserve_edits enabled
            customized_files = set()
            if preserve_edits:
                customized_files = self._detect_customizations(bundle_path, checksums)
                if customized_files:
                    print(f"\nFound {len(customized_files)} user-modified file(s)")

            # NOTE: Actual file update implementation coming in future PR
            # For now, update is detection-only
            raise BundleGeneratorError(
                "Update functionality is currently in preview mode.",
                recovery_suggestion=(
                    "Use --check-only to check for updates. Full update implementation coming soon."
                ),
            )

            # Update manifest with new version
            manifest["framework"]["version"] = self._get_framework_version()
            manifest["framework"]["updated_at"] = datetime.now().isoformat()

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            return UpdateResult(
                success=True,
                updated_files=updated_files,
                preserved_files=preserved_files,
                conflicts=conflicts,
            )

        except Exception as e:
            return UpdateResult(
                success=False, updated_files=[], preserved_files=[], conflicts=[], error=str(e)
            )

    def detect_customizations(self, bundle_path: Path) -> Dict[str, bool]:
        """Detect which files have been customized by user.

        Args:
            bundle_path: Path to bundle directory

        Returns:
            Dict mapping file paths to customization status
        """
        manifest_path = bundle_path / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        checksums = manifest.get("file_checksums", {})
        customized_files = self._detect_customizations(bundle_path, checksums)

        return {file_path: (file_path in customized_files) for file_path in checksums.keys()}

    def _get_framework_version(self) -> str:
        """Get current framework version from git."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            cwd=self.framework_repo,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")

        return result.stdout.strip()[:12]  # Short hash

    def _get_changelog(self, old_version: str, new_version: str) -> List[str]:
        """Get changelog between versions."""
        result = subprocess.run(
            ["git", "log", f"{old_version}..{new_version}", "--oneline"],
            check=False,
            cwd=self.framework_repo,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        return result.stdout.strip().split("\n")[:10]  # Limit to 10 entries

    def _detect_customizations(self, bundle_path: Path, checksums: Dict[str, str]) -> set:
        """Detect files that have been modified from original."""
        customized = set()

        for file_rel_path, original_checksum in checksums.items():
            file_path = bundle_path / file_rel_path

            if not file_path.exists():
                continue

            current_checksum = self._compute_checksum(file_path)

            if current_checksum != original_checksum:
                customized.add(file_rel_path)

        return customized

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"

    def _create_backup(self, bundle_path: Path) -> Path:
        """Create backup of bundle before updating."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = bundle_path.parent / f"{bundle_path.name}.backup.{timestamp}"

        shutil.copytree(bundle_path, backup_path)

        return backup_path
