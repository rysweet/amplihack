"""Profile YAML loader and validator.

Loads profile definitions from YAML files and validates their structure.
"""

import yaml
from pathlib import Path
from typing import List, Optional
from .models import Profile


class ProfileLoader:
    """Load and validate profile YAML files.

    Handles loading profile definitions from the .claude/profiles directory
    and validating their structure and content.

    Attributes:
        profiles_dir: Path to profiles directory (default: .claude/profiles)

    Example:
        >>> loader = ProfileLoader()
        >>> profile = loader.load_profile("coding")
        >>> profiles = loader.list_available_profiles()
    """

    def __init__(self, profiles_dir: Optional[Path] = None):
        """Initialize loader with profiles directory.

        Args:
            profiles_dir: Path to profiles directory. If None, uses .claude/profiles
        """
        if profiles_dir is None:
            profiles_dir = Path(".claude/profiles")
        self.profiles_dir = Path(profiles_dir)

    def load_profile(self, profile_name: str) -> Profile:
        """Load profile by name.

        Args:
            profile_name: Name of profile to load (without .yaml extension)

        Returns:
            Profile instance

        Raises:
            FileNotFoundError: If profile file doesn't exist
            yaml.YAMLError: If YAML is invalid
            KeyError: If required fields are missing
            ValueError: If validation fails

        Example:
            >>> loader = ProfileLoader()
            >>> profile = loader.load_profile("coding")
            >>> print(profile.description)
            Development-focused: core workflows, testing, CI/CD
        """
        profile_file = self.profiles_dir / f"{profile_name}.yaml"

        if not profile_file.exists():
            available = self.list_available_profiles()
            available_str = ", ".join(available) if available else "none"
            raise FileNotFoundError(
                f"Profile '{profile_name}' not found at {profile_file}.\n"
                f"Available profiles: {available_str}"
            )

        try:
            with open(profile_file) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in profile '{profile_name}': {e}"
            )

        if data is None:
            raise ValueError(f"Profile '{profile_name}' is empty")

        # Create profile from YAML
        profile = Profile.from_yaml(data)

        # Validate profile
        validation_errors = self.validate_profile(profile)
        if validation_errors:
            errors_str = "\n  - ".join(validation_errors)
            raise ValueError(
                f"Profile '{profile_name}' validation failed:\n  - {errors_str}"
            )

        return profile

    def list_available_profiles(self) -> List[str]:
        """List all available profile names.

        Returns:
            List of profile names (without .yaml extension)

        Example:
            >>> loader = ProfileLoader()
            >>> profiles = loader.list_available_profiles()
            >>> print(profiles)
            ['all', 'coding', 'research']
        """
        if not self.profiles_dir.exists():
            return []

        return sorted([
            p.stem for p in self.profiles_dir.glob("*.yaml")
        ])

    def validate_profile(self, profile: Profile) -> List[str]:
        """Validate profile configuration.

        Args:
            profile: Profile to validate

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> loader = ProfileLoader()
            >>> profile = loader.load_profile("coding")
            >>> errors = loader.validate_profile(profile)
            >>> if not errors:
            ...     print("Profile is valid")
        """
        errors = []

        # Check required fields
        if not profile.name:
            errors.append("Profile name is required")

        if not profile.description:
            errors.append("Profile description is required")

        # Validate version
        if profile.version not in ["1.0.0"]:
            errors.append(
                f"Unsupported profile version: {profile.version}. "
                f"Supported versions: 1.0.0"
            )

        # Validate component filters
        for category in ["commands", "agents", "skills"]:
            filter_obj = getattr(profile, category)

            # Check that includes is not empty
            if not filter_obj.includes:
                errors.append(
                    f"{category}.includes cannot be empty. "
                    f"Use ['**/*'] to include all."
                )

            # Check for valid glob patterns
            for pattern in filter_obj.includes:
                if not isinstance(pattern, str):
                    errors.append(
                        f"{category}.includes pattern must be string, "
                        f"got {type(pattern).__name__}"
                    )

            for pattern in filter_obj.excludes:
                if not isinstance(pattern, str):
                    errors.append(
                        f"{category}.excludes pattern must be string, "
                        f"got {type(pattern).__name__}"
                    )

        return errors

    def profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists.

        Args:
            profile_name: Name of profile to check

        Returns:
            True if profile file exists, False otherwise

        Example:
            >>> loader = ProfileLoader()
            >>> if loader.profile_exists("coding"):
            ...     print("Coding profile is available")
        """
        profile_file = self.profiles_dir / f"{profile_name}.yaml"
        return profile_file.exists()

    def get_profile_path(self, profile_name: str) -> Path:
        """Get the file path for a profile.

        Args:
            profile_name: Name of profile

        Returns:
            Path to profile YAML file

        Example:
            >>> loader = ProfileLoader()
            >>> path = loader.get_profile_path("coding")
            >>> print(path)
            .claude/profiles/coding.yaml
        """
        return self.profiles_dir / f"{profile_name}.yaml"
