"""YAML recipe parser.

Parses YAML recipe definitions into Recipe model objects, with validation
and step-type inference.
"""

from __future__ import annotations

from typing import Any

import yaml

from amplihack.recipes.models import Recipe, Step, StepType


class RecipeParser:
    """Parses YAML recipe strings into Recipe objects.

    Supports:
    - Explicit ``type`` field on steps (``bash`` or ``agent``)
    - Inference from ``agent`` or ``command`` field presence
    - Validation of required fields and uniqueness constraints
    """

    def parse(self, yaml_content: str) -> Recipe:
        """Parse a YAML string into a Recipe.

        Args:
            yaml_content: Raw YAML text defining a recipe.

        Returns:
            A fully populated Recipe object.

        Raises:
            ValueError: If required fields are missing or constraints violated.
        """
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ValueError("Recipe YAML must be a mapping at the top level")

        name = data.get("name")
        if not name:
            raise ValueError("Recipe must have a 'name' field")

        raw_steps = data.get("steps")
        if not raw_steps:
            raise ValueError("Recipe must have a 'steps' field with at least one step")

        # Check for duplicate step ids
        step_ids: list[str] = []
        for raw in raw_steps:
            sid = raw.get("id", "")
            if sid in step_ids:
                raise ValueError(f"Duplicate step id: '{sid}'")
            step_ids.append(sid)

        steps = [self._parse_step(raw) for raw in raw_steps]

        return Recipe(
            name=name,
            steps=steps,
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            context=data.get("context", {}),
        )

    # Top-level and step-level fields recognized by the parser.
    # Fields outside these sets produce validation warnings (catch typos).
    _KNOWN_TOP_FIELDS = frozenset(
        {
            "name",
            "description",
            "version",
            "author",
            "tags",
            "context",
            "steps",
            "recursion",
            "output",
        }  # recursion/output: recognized but not modeled yet
    )
    _KNOWN_STEP_FIELDS = frozenset(
        {
            "id",
            "type",
            "agent",
            "prompt",
            "command",
            "output",
            "condition",
            "parse_json",
            "mode",
            "working_dir",
            "timeout",
        }
    )

    def validate(self, recipe: Recipe, raw_yaml: str | None = None) -> list[str]:
        """Validate a parsed recipe and return a list of warning strings.

        Args:
            recipe: A parsed Recipe object.
            raw_yaml: Optional raw YAML string for checking unrecognized fields.

        Returns:
            List of warning messages. Empty list means no issues.
        """
        warnings: list[str] = []

        for step in recipe.steps:
            if step.step_type == StepType.AGENT and not step.prompt:
                warnings.append(f"Step '{step.id}': agent step is missing a 'prompt' field")
            if step.step_type == StepType.BASH and not step.command:
                warnings.append(f"Step '{step.id}': bash step is missing a 'command' field")

        # Check for unrecognized fields if raw YAML is provided
        if raw_yaml is not None:
            data = yaml.safe_load(raw_yaml)
            if isinstance(data, dict):
                for key in data:
                    if key not in self._KNOWN_TOP_FIELDS:
                        warnings.append(f"Unrecognized top-level field '{key}' (possible typo)")
                for i, step_raw in enumerate(data.get("steps") or []):
                    if isinstance(step_raw, dict):
                        for key in step_raw:
                            if key not in self._KNOWN_STEP_FIELDS:
                                sid = step_raw.get("id", f"index {i}")
                                warnings.append(
                                    f"Step '{sid}': unrecognized field '{key}' (possible typo)"
                                )

        return warnings

    def _parse_step(self, raw: dict[str, Any]) -> Step:
        """Parse a single step dict into a Step object."""
        step_id = raw.get("id", "")
        if not step_id:
            raise ValueError("Every step must have a non-empty 'id' field")
        step_type = self._infer_step_type(raw)

        return Step(
            id=step_id,
            step_type=step_type,
            command=raw.get("command"),
            agent=raw.get("agent"),
            prompt=raw.get("prompt"),
            output=raw.get("output"),
            condition=raw.get("condition"),
            parse_json=raw.get("parse_json", False),
            mode=raw.get("mode"),
            working_dir=raw.get("working_dir"),
            timeout=raw.get("timeout", 120),
        )

    def _infer_step_type(self, raw: dict[str, Any]) -> StepType:
        """Determine step type from explicit field or infer from other fields.

        Priority:
        1. Explicit ``type`` field
        2. Presence of ``agent`` field -> AGENT
        3. Presence of ``prompt`` field (without ``command``) -> AGENT
        4. Presence of ``command`` field -> BASH
        5. Default to BASH
        """
        explicit = raw.get("type")
        if explicit:
            return StepType(explicit.lower())

        if "agent" in raw:
            return StepType.AGENT

        if "prompt" in raw and "command" not in raw:
            return StepType.AGENT

        if "command" in raw:
            return StepType.BASH

        return StepType.BASH
