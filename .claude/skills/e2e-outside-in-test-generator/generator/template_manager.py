"""Template manager for test generation.

Manages test templates and rendering using string.format().
NO Jinja2 - uses simple string-based templates.
"""

from pathlib import Path
from typing import Any

from .models import TemplateNotFoundError


class TemplateManager:
    """Manages test templates with caching."""

    def __init__(self):
        """Initialize template manager and load templates."""
        self._cache: dict[str, str] = {}
        self._template_dir = Path(__file__).parent / "templates"
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from templates directory into cache."""
        if not self._template_dir.exists():
            self._template_dir.mkdir(parents=True, exist_ok=True)
            return

        # Load all .template files
        for template_file in self._template_dir.glob("*.template"):
            name = template_file.stem  # filename without extension
            try:
                self._cache[name] = template_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: Failed to load template {name}: {e}")

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render template with context data using string.format().

        Args:
            template_name: Name of template (without .template extension)
            context: Data to populate template

        Returns:
            Rendered test code

        Raises:
            TemplateNotFoundError: If template doesn't exist

        Example:
            >>> mgr = TemplateManager()
            >>> code = mgr.render("smoke", {"feature": "Login", "route": "/login"})
        """
        template = self._cache.get(template_name)
        if not template:
            raise TemplateNotFoundError(f"Template '{template_name}' not found")

        try:
            return template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

    def register_template(self, name: str, template: str) -> None:
        """Register custom template at runtime.

        Args:
            name: Template name
            template: Template string

        Example:
            >>> mgr = TemplateManager()
            >>> mgr.register_template("custom", "test('{test_name}', ...)")
        """
        self._cache[name] = template

    def list_templates(self) -> list[str]:
        """Return list of available template names.

        Returns:
            List of template names

        Example:
            >>> mgr = TemplateManager()
            >>> mgr.list_templates()
            ['smoke', 'form_interaction', 'component_interaction', ...]
        """
        return list(self._cache.keys())

    def reload_templates(self) -> None:
        """Reload all templates from disk.

        Useful for development and testing.
        """
        self._cache.clear()
        self._load_templates()
