"""Validation utilities - Batch 337"""

from typing import Any, Callable, Optional

class Validator:
    """Generic validation framework."""

    def __init__(self):
        self.rules: list[Callable[[Any], bool]] = []
        self.errors: list[str] = []

    def add_rule(self, rule: Callable[[Any], bool], error_msg: str) -> None:
        """Add a validation rule."""
        self.rules.append((rule, error_msg))

    def validate(self, value: Any) -> bool:
        """Run all validation rules."""
        self.errors.clear()
        for rule, error_msg in self.rules:
            try:
                if not rule(value):
                    self.errors.append(error_msg)
            except Exception as e:
                self.errors.append(f"Validation error: {{e}}")
        return len(self.errors) == 0

    def get_errors(self) -> list[str]:
        """Get all validation errors."""
        return self.errors.copy()
