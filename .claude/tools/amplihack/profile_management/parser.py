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

        Security: Limits YAML size and nesting depth to prevent YAML bomb attacks.

        Args:
            raw_yaml: Raw YAML content as string

        Returns:
            Validated ProfileConfig instance

        Raises:
            yaml.YAMLError: Invalid YAML syntax
            ValidationError: Schema validation failure
            ValueError: Profile data is invalid, version unsupported, or YAML too large/nested
        """
        # Security: Limit YAML size to prevent memory exhaustion
        MAX_YAML_SIZE = 100_000  # 100KB
        if len(raw_yaml) > MAX_YAML_SIZE:
            raise ValueError(
                f"Profile YAML too large ({len(raw_yaml)} bytes). "
                f"Maximum allowed: {MAX_YAML_SIZE} bytes"
            )

        # Parse YAML
        try:
            data = yaml.safe_load(raw_yaml)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML syntax: {e}\nEnsure the profile is valid YAML format."
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

        # Security: Check nesting depth to prevent YAML bombs
        max_depth = self._check_nesting_depth(data)
        MAX_ALLOWED_DEPTH = 10
        if max_depth > MAX_ALLOWED_DEPTH:
            raise ValueError(
                f"Profile YAML too deeply nested (depth: {max_depth}). "
                f"Maximum allowed: {MAX_ALLOWED_DEPTH}"
            )

        # Validate against pydantic schema
        try:
            profile = ProfileConfig(**data)
        except ValidationError as e:
            # Format validation errors for better readability
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {field}: {msg}")

            raise ValidationError.from_exception_data(title="ProfileConfig", line_errors=e.errors())

        # Version validation happens automatically via @field_validator in ProfileConfig
        return profile

    def _check_nesting_depth(self, obj: any, current_depth: int = 0) -> int:
        """Check maximum nesting depth of data structure.

        Security: Prevents YAML bomb attacks by detecting deeply nested structures.

        Args:
            obj: Object to check (dict, list, or primitive)
            current_depth: Current recursion depth

        Returns:
            Maximum depth found in the structure
        """
        if not isinstance(obj, (dict, list)):
            return current_depth

        max_depth = current_depth

        if isinstance(obj, dict):
            for value in obj.values():
                depth = self._check_nesting_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
        elif isinstance(obj, list):
            for item in obj:
                depth = self._check_nesting_depth(item, current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth

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
