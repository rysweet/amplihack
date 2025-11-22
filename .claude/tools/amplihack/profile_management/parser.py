"""Profile parsing and validation functionality.

This module provides ProfileParser for parsing YAML profiles and validating
them against the ProfileConfig schema.
"""

import yaml
from pydantic import ValidationError
from .models import ProfileConfig


class ProfileParser:
    """Parse and validate YAML profiles.

    Example:
        >>> parser = ProfileParser()
        >>> raw_yaml = "version: '1.0'\\nname: test\\n..."
        >>> profile = parser.parse(raw_yaml)
        >>> print(profile.name)
        test
    """

    def parse(self, raw_yaml: str) -> ProfileConfig:
        """Parse YAML and validate against schema.

        Args:
            raw_yaml: Raw YAML content as string

        Returns:
            Validated ProfileConfig instance

        Raises:
            yaml.YAMLError: Invalid YAML syntax
            ValidationError: Schema validation failure
            ValueError: Profile data is invalid or version unsupported
        """
        # Parse YAML
        try:
            data = yaml.safe_load(raw_yaml)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML syntax: {e}\n"
                f"Ensure the profile is valid YAML format."
            )

        # Validate it's a dictionary
        if not isinstance(data, dict):
            raise ValueError(
                "Profile must be a YAML dictionary (key-value mapping), "
                f"but got {type(data).__name__}"
            )

        # Check for empty profile
        if not data:
            raise ValueError(
                "Profile is empty. A valid profile must contain at minimum: "
                "version, name, description, components, and metadata fields."
            )

        # Validate against pydantic schema
        try:
            profile = ProfileConfig(**data)
        except ValidationError as e:
            # Format validation errors for better readability
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                msg = error['msg']
                error_messages.append(f"  - {field}: {msg}")

            raise ValidationError.from_exception_data(
                title="ProfileConfig",
                line_errors=e.errors()
            )

        # Validate version compatibility
        if not profile.validate_version_compatibility():
            raise ValueError(
                f"Unsupported profile version: {profile.version}. "
                f"This version of amplihack supports profile versions: 1.0"
            )

        return profile

    def parse_safe(self, raw_yaml: str) -> tuple[ProfileConfig | None, str | None]:
        """Parse YAML with error handling.

        Safe version of parse() that returns errors instead of raising them.

        Args:
            raw_yaml: Raw YAML content as string

        Returns:
            Tuple of (ProfileConfig, error_message)
            - If successful: (ProfileConfig instance, None)
            - If failed: (None, error message string)

        Example:
            >>> parser = ProfileParser()
            >>> profile, error = parser.parse_safe(raw_yaml)
            >>> if error:
            ...     print(f"Failed to parse: {error}")
            ... else:
            ...     print(f"Loaded profile: {profile.name}")
        """
        try:
            profile = self.parse(raw_yaml)
            return profile, None
        except yaml.YAMLError as e:
            return None, f"YAML syntax error: {e}"
        except ValidationError as e:
            return None, f"Validation error: {e}"
        except ValueError as e:
            return None, f"Invalid profile: {e}"
        except Exception as e:
            return None, f"Unexpected error: {e}"

    def validate_yaml(self, raw_yaml: str) -> tuple[bool, str | None]:
        """Validate YAML without creating ProfileConfig.

        Args:
            raw_yaml: Raw YAML content as string

        Returns:
            Tuple of (is_valid, error_message)
            - If valid: (True, None)
            - If invalid: (False, error message string)
        """
        _, error = self.parse_safe(raw_yaml)
        return (True, None) if error is None else (False, error)
