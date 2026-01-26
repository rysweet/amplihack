"""Language detection and LSP configuration generation."""

from pathlib import Path
from typing import Any


class LSPDetector:
    """Detects project languages and generates LSP configurations.

    This detector:
    - Scans project for language-specific files
    - Generates appropriate LSP server configurations
    - Updates settings.json with MCP server configs
    """

    # Language file patterns
    LANGUAGE_PATTERNS = {
        "python": ["**/*.py"],
        "javascript": ["**/*.js", "**/*.jsx"],
        "typescript": ["**/*.ts", "**/*.tsx", "**/*.d.ts"],
        "rust": ["**/*.rs"],
        "go": ["**/*.go"],
    }

    # Directories to ignore during detection
    IGNORED_DIRS = {
        "node_modules",
        ".git",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        "target",
    }

    # LSP server configurations
    LSP_CONFIGS = {
        "python": {
            "python-lsp-server": {
                "command": "pylsp",
                "args": [],
            }
        },
        "typescript": {
            "typescript-language-server": {
                "command": "typescript-language-server",
                "args": ["--stdio"],
            }
        },
        "rust": {
            "rust-analyzer": {
                "command": "rust-analyzer",
                "args": [],
            }
        },
        "go": {
            "gopls": {
                "command": "gopls",
                "args": [],
            }
        },
        "javascript": {
            "typescript-language-server": {
                "command": "typescript-language-server",
                "args": ["--stdio"],
            }
        },
    }

    def detect_languages(self, project_path: Path) -> list[str]:
        """Detect languages used in project.

        Args:
            project_path: Path to project directory

        Returns:
            List of detected language names
        """
        detected = set()

        try:
            for language, patterns in self.LANGUAGE_PATTERNS.items():
                for pattern in patterns:
                    # Search for files matching pattern
                    matches = list(project_path.glob(pattern))

                    # Filter out files in ignored directories and hidden files
                    filtered_matches = [
                        m
                        for m in matches
                        if not any(ignored in m.parts for ignored in self.IGNORED_DIRS)
                        and not any(
                            part.startswith(".") for part in m.parts[len(project_path.parts) :]
                        )
                    ]

                    if filtered_matches:
                        detected.add(language)
                        break  # Found language, move to next

        except PermissionError:
            # Return empty list if we can't access the directory
            return []

        return sorted(list(detected))

    def generate_lsp_config(self, languages: list[str]) -> dict[str, Any]:
        """Generate LSP configurations for detected languages.

        Args:
            languages: List of language names

        Returns:
            Dictionary of LSP server configurations
        """
        if not isinstance(languages, list):
            raise TypeError("languages must be a list")

        config = {}

        for language in languages:
            if language in self.LSP_CONFIGS:
                # Merge language-specific configs
                config.update(self.LSP_CONFIGS[language])

        return config

    def update_settings_json(
        self, existing_settings: dict[str, Any], lsp_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update settings.json with LSP configurations.

        Args:
            existing_settings: Current settings dictionary
            lsp_config: LSP configurations to add

        Returns:
            Updated settings dictionary
        """
        if not isinstance(existing_settings, dict):
            raise TypeError("existing_settings must be a dict")

        if not isinstance(lsp_config, dict):
            raise TypeError("lsp_config must be a dict")

        # If no LSP config, return unchanged
        if not lsp_config:
            return existing_settings

        # Create copy to avoid modifying original
        updated = dict(existing_settings)

        # Ensure mcpServers exists
        if "mcpServers" not in updated:
            updated["mcpServers"] = {}

        # Merge LSP configs into mcpServers
        updated["mcpServers"].update(lsp_config)

        return updated
