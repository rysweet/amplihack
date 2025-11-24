"""Profile loading functionality for different URI schemes.

This module provides ProfileLoader for loading profiles from:
- file:// URIs (local filesystem)
- amplihack:// URIs (built-in profiles)
- git+https:// URIs (remote GitHub repositories)
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import urllib.parse


class ProfileLoader:
    """Load profiles from different URI schemes.

    Supports:
    - file:// - Load from local filesystem
    - amplihack:// - Load from built-in profiles directory
    - git+https:// - Load from GitHub repository

    Example:
        >>> loader = ProfileLoader()
        >>> yaml_content = loader.load("amplihack://profiles/coding")
        >>> yaml_content = loader.load("file:///home/user/my-profile.yaml")
        >>> yaml_content = loader.load("git+https://github.com/user/repo/blob/main/profile.yaml")
    """

    def __init__(self, builtin_profiles_dir: Optional[Path] = None):
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
        """Load profile YAML from URI.

        Args:
            uri: Profile URI (file://, amplihack://)

        Returns:
            Raw YAML content as string

        Raises:
            ValueError: Invalid URI scheme or malformed URI
            FileNotFoundError: Local file or built-in profile not found
            PermissionError: Insufficient permissions to read file
        """
        # Parse the URI
        try:
            parsed = urllib.parse.urlparse(uri)
        except Exception as e:
            raise ValueError(f"Malformed URI: {uri}. Error: {e}")

        # Route to appropriate loader based on scheme
        if parsed.scheme == "file":
            return self._load_file(parsed.path)
        elif parsed.scheme == "amplihack":
            # For amplihack://, the profile name might be in netloc or path
            # amplihack://all -> netloc="all", path=""
            # amplihack://profiles/all -> netloc="profiles", path="/all"
            # amplihack:///all -> netloc="", path="/all"
            profile_identifier = parsed.netloc + parsed.path
            return self._load_builtin(profile_identifier)
        elif uri.startswith("git+https://") or uri.startswith("git+http://"):
            return self._load_git(uri)
        else:
            raise ValueError(
                f"Unsupported URI scheme: {parsed.scheme}. "
                f"Supported schemes: file, amplihack, git+https"
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
                f"Profile not found: {file_path}. "
                f"Ensure the file exists and the path is correct."
            )

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            return file_path.read_text(encoding="utf-8")
        except PermissionError:
            raise PermissionError(
                f"Insufficient permissions to read file: {file_path}"
            )

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
                f"Built-in profile not found: {profile_name}. "
                f"Available profiles: {available_str}"
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

    def _load_git(self, uri: str) -> str:
        """Load profile from git repository.

        Supports URLs like:
        - git+https://github.com/user/repo/blob/main/profiles/custom.yaml
        - git+https://github.com/user/repo/blob/branch-name/path/to/profile.yaml

        Args:
            uri: git+https:// URI pointing to profile file

        Returns:
            File content as string

        Raises:
            ValueError: Malformed git URL
            subprocess.CalledProcessError: Git operation failed
            FileNotFoundError: File not found in repository
        """
        # Parse git+https://github.com/user/repo/blob/ref/path/to/file.yaml
        # Remove git+ prefix
        if uri.startswith("git+"):
            https_url = uri[4:]  # Remove "git+"
        else:
            https_url = uri

        # Parse GitHub URL format: https://github.com/user/repo/blob/ref/path/to/file
        parts = https_url.split("/blob/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid git URL format. Expected: git+https://github.com/user/repo/blob/ref/path/to/file.yaml, got: {uri}"
            )

        repo_url = parts[0]  # https://github.com/user/repo
        ref_and_path = parts[1]  # ref/path/to/file.yaml

        # For GitHub blob URLs, the path after /blob/ is: branch/.claude/profiles/file.yaml
        # We need to extract everything before .claude as the ref
        if "/.claude/" in ref_and_path:
            # Split on /.claude/ to separate ref from file path
            ref_parts = ref_and_path.split("/.claude/", 1)
            ref = ref_parts[0]  # Could be "main" or "feat/issue-1234"
            file_path = ".claude/" + ref_parts[1]  # .claude/profiles/coding.yaml
        else:
            # Fallback: assume first component is ref, rest is path
            ref_path_parts = ref_and_path.split("/", 1)
            if len(ref_path_parts) != 2:
                raise ValueError(f"Invalid git URL: missing file path after ref. Got: {uri}")
            ref = ref_path_parts[0]
            file_path = ref_path_parts[1]

        # Use cache directory for cloned repos
        cache_dir = Path.home() / ".amplihack" / "cache" / "repos"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create unique directory name from repo URL
        repo_name = repo_url.split("/")[-1]  # Last part of URL
        repo_cache = cache_dir / repo_name

        # Clone or update repository
        if not repo_cache.exists():
            # Clone repository
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(repo_cache)],
                check=True,
                capture_output=True,
                text=True
            )
        else:
            # Update existing clone
            try:
                subprocess.run(
                    ["git", "-C", str(repo_cache), "fetch", "origin", ref],
                    check=True,
                    capture_output=True,
                    text=True
                )
                subprocess.run(
                    ["git", "-C", str(repo_cache), "checkout", ref],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError:
                # If update fails, re-clone
                import shutil
                shutil.rmtree(repo_cache)
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(repo_cache)],
                    check=True,
                    capture_output=True,
                    text=True
                )

        # Read the profile file from cloned repo
        profile_file = repo_cache / file_path
        if not profile_file.exists():
            raise FileNotFoundError(f"Profile file not found in repository: {file_path}")

        with open(profile_file, encoding="utf-8") as f:
            return f.read()

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
