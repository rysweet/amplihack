"""Profile loading functionality for different URI schemes.

This module provides ProfileLoader for loading profiles from:
- file:// URIs (local filesystem)
- amplihack:// URIs (built-in profiles)
"""

import urllib.parse
from pathlib import Path


class ProfileLoader:
    """Load profiles from different URI schemes.

    Supports:
    - file:// - Load from local filesystem
    - amplihack:// - Load from built-in profiles directory

    Example:
        >>> loader = ProfileLoader()
        >>> yaml_content = loader.load("amplihack://profiles/coding")
        >>> yaml_content = loader.load("file:///home/user/my-profile.yaml")
    """

    def __init__(self, builtin_profiles_dir: Path | None = None):
        """Initialize loader with built-in profiles directory.

        Args:
            builtin_profiles_dir: Path to built-in profiles directory.
                                 Defaults to .claude/profiles
        """
        if builtin_profiles_dir is None:
            # Default to .claude/profiles relative to this file's location
            # This file is in .claude/tools/amplihack/profile_management/loader.py
            # Go up: profile_management -> amplihack -> tools -> .claude -> profiles
            self.builtin_dir = Path(__file__).parent.parent.parent.parent / "profiles"
        else:
            self.builtin_dir = builtin_profiles_dir

    def load(self, uri: str) -> str:
        """Load profile YAML from URI or simple name.

        Args:
            uri: Profile URI (file://, amplihack://) or simple built-in name

        Returns:
            Raw YAML content as string

        Raises:
            ValueError: Invalid URI scheme or malformed URI
            FileNotFoundError: Local file or built-in profile not found
            PermissionError: Insufficient permissions to read file
        """
        # Detect if this is a URI (contains "://") or simple name
        if "://" not in uri:
            # Simple name - treat as built-in profile
            return self._load_builtin(uri)

        # Parse the URI
        try:
            parsed = urllib.parse.urlparse(uri)
        except Exception as e:
            raise ValueError(f"Malformed URI: {uri}. Error: {e}")

        # Route to appropriate loader based on scheme
        if parsed.scheme == "file":
            return self._load_file(parsed.path)
        if parsed.scheme == "amplihack":
            # For amplihack://, the profile name might be in netloc or path
            # amplihack://all -> netloc="all", path=""
            # amplihack://profiles/all -> netloc="profiles", path="/all"
            # amplihack:///all -> netloc="", path="/all"
            profile_identifier = parsed.netloc + parsed.path
            return self._load_builtin(profile_identifier)
        raise ValueError(
            f"Unsupported URI scheme: {parsed.scheme}. Supported schemes: file, amplihack"
        )

    def _load_file(self, path: str) -> str:
        """Load from local file:// URI.

        Security: Restricts access to ~/.amplihack/ and current directory to
        prevent path traversal attacks.

        Args:
            path: Path component from file:// URI

        Returns:
            File content as string

        Raises:
            FileNotFoundError: File does not exist
            PermissionError: Cannot read file
            ValueError: Path is outside allowed directories
        """
        file_path = Path(path).resolve()

        # Define allowed directories for security
        allowed_dirs = [
            Path.home() / ".amplihack",
            Path.cwd(),
        ]

        # Verify path is within allowed directories to prevent path traversal
        if not any(file_path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs):
            raise ValueError(
                f"Security: Profile path outside allowed directories.\n"
                f"Allowed: ~/.amplihack/ or current directory\n"
                f"Attempted: {file_path}"
            )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Profile not found: {file_path}. Ensure the file exists and the path is correct."
            )

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            return file_path.read_text(encoding="utf-8")
        except PermissionError:
            raise PermissionError(f"Insufficient permissions to read file: {file_path}")

    def _load_builtin(self, path: str) -> str:
        """Load from built-in amplihack:// URI.

        Supports formats:
        - amplihack://profiles/coding
        - amplihack://coding
        - amplihack://profiles/coding.yaml

        Args:
            path: Path component from amplihack:// URI

        Returns:
            Built-in profile content as string

        Raises:
            FileNotFoundError: Built-in profile not found
        """
        # Path format: //profiles/name or /profiles/name or //name or /name
        profile_path = path.lstrip("/")

        # If path starts with "profiles/", extract the profile name
        if profile_path.startswith("profiles/"):
            profile_name = profile_path.split("/", 1)[1]
        else:
            profile_name = profile_path

        # Add .yaml extension if not present
        if not profile_name.endswith(".yaml"):
            profile_name += ".yaml"

        # Construct full path to built-in profile
        profile_file = self.builtin_dir / profile_name

        if not profile_file.exists():
            # Provide helpful error message with available profiles
            available = self._list_builtin_profiles()
            available_str = ", ".join(available) if available else "none"
            raise FileNotFoundError(
                f"Built-in profile not found: {profile_name}. Available profiles: {available_str}"
            )

        try:
            return profile_file.read_text(encoding="utf-8")
        except PermissionError:
            raise PermissionError(
                f"Insufficient permissions to read built-in profile: {profile_name}"
            )

    def _list_builtin_profiles(self) -> list[str]:
        """List available built-in profiles.

        Returns:
            List of profile names (without .yaml extension)
        """
        if not self.builtin_dir.exists():
            return []

        profiles = []
        for file_path in self.builtin_dir.glob("*.yaml"):
            profiles.append(file_path.stem)

        return sorted(profiles)

    def validate_uri(self, uri: str) -> bool:
        """Check if URI is valid and accessible.

        Args:
            uri: Profile URI to validate

        Returns:
            True if URI is valid and accessible, False otherwise
        """
        try:
            self.load(uri)
            return True
        except Exception:
            return False

    def list_builtin_profiles(self) -> list[str]:
        """List available built-in profiles.

        Returns:
            List of profile names (without .yaml extension)
        """
        return self._list_builtin_profiles()
