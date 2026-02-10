"""GitHub Copilot model mapping and capabilities."""

import re
from typing import Any

# Claude model constants (exported for use in server.py)
CLAUDE_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-opus-4-20240229",
    "claude-sonnet-4",  # Generic Sonnet 4 (Issue #1920 fix)
    "claude-sonnet-4-20250514",
    "claude-sonnet-4.5-20250514",
]

# OpenAI model constants
OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini",
]

# GitHub Copilot model constants
GITHUB_COPILOT_MODELS = [
    "copilot-gpt-4",
    "copilot-gpt-3.5-turbo",
    "github-copilot-gpt-4",
    "github-copilot-gpt-3.5-turbo",
]


class GitHubModelMapper:
    """Maps OpenAI model names to GitHub Copilot models."""

    def __init__(self, config: dict[str, str]):
        """Initialize GitHub model mapper.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self._model_cache: dict[str, str] = {}
        self._capability_cache: dict[str, dict] = {}

    def get_github_model(self, openai_model: str) -> str | None:
        """Get GitHub Copilot model for OpenAI model name.

        Args:
            openai_model: OpenAI model name (e.g., "gpt-4")

        Returns:
            GitHub Copilot model name if mapping exists, None otherwise.
        """
        # Check cache first
        if openai_model in self._model_cache:
            return self._model_cache[openai_model]

        # Direct model mapping from config
        github_model = self._get_direct_model_mapping(openai_model)
        if github_model:
            self._model_cache[openai_model] = github_model
            return github_model

        # Default model mappings
        github_model = self._get_default_model_mapping(openai_model)
        if github_model:
            self._model_cache[openai_model] = github_model
            return github_model

        # Fallback to general GitHub Copilot model if no specific mapping exists
        fallback_model = self.config.get("GITHUB_COPILOT_MODEL")
        if fallback_model:
            self._model_cache[openai_model] = fallback_model
            return fallback_model

        return None

    def get_available_models(self) -> list[str]:
        """Get list of available GitHub Copilot models.

        Returns:
            List of GitHub Copilot model names.
        """
        return [
            "copilot-gpt-4",
            "copilot-gpt-3.5-turbo",
            "github-copilot-gpt-4",
            "github-copilot-gpt-3.5-turbo",
            "claude-sonnet-4",
            "claude-sonnet-4.5",
            "claude-opus-4",
        ]

    def get_model_capabilities(self, model: str) -> dict[str, Any]:
        """Get capabilities for a GitHub Copilot model.

        Args:
            model: GitHub Copilot model name

        Returns:
            Dictionary with model capabilities.
        """
        # Check cache first
        if model in self._capability_cache:
            return self._capability_cache[model]

        capabilities = self._build_model_capabilities(model)
        self._capability_cache[model] = capabilities
        return capabilities

    def supports_function_calling(self, model: str) -> bool:
        """Check if model supports function calling.

        Args:
            model: GitHub Copilot model name

        Returns:
            True if function calling is supported, False otherwise.
        """
        capabilities = self.get_model_capabilities(model)
        return capabilities.get("function_calling", False)

    def supports_streaming(self, model: str) -> bool:
        """Check if model supports streaming responses.

        Args:
            model: GitHub Copilot model name

        Returns:
            True if streaming is supported, False otherwise.
        """
        capabilities = self.get_model_capabilities(model)
        return capabilities.get("streaming", True)

    def get_context_window(self, model: str) -> int:
        """Get context window size for model.

        Args:
            model: GitHub Copilot model name

        Returns:
            Context window size in tokens.
        """
        capabilities = self.get_model_capabilities(model)
        return capabilities.get("context_window", 8192)

    def get_max_output_tokens(self, model: str) -> int:
        """Get maximum output tokens for model.

        Args:
            model: GitHub Copilot model name

        Returns:
            Maximum output tokens.
        """
        capabilities = self.get_model_capabilities(model)
        return capabilities.get("max_output_tokens", 4096)

    def _get_direct_model_mapping(self, openai_model: str) -> str | None:
        """Get direct model mapping from configuration.

        Args:
            openai_model: OpenAI model name

        Returns:
            GitHub Copilot model name if configured, None otherwise.
        """
        # Check for explicit model mapping in config
        mapping_key = f"GITHUB_COPILOT_{openai_model.upper().replace('-', '_')}_MODEL"
        github_model = self.config.get(mapping_key)
        if github_model:
            return github_model

        return None

    def _get_default_model_mapping(self, openai_model: str) -> str | None:
        """Get default model mapping for OpenAI model.

        Args:
            openai_model: OpenAI model name

        Returns:
            Default GitHub Copilot model name if mapping exists, None otherwise.
        """
        # Default mappings from OpenAI to GitHub Copilot models
        default_mappings = {
            "gpt-4": "copilot-gpt-4",
            "gpt-4-turbo": "copilot-gpt-4",
            "gpt-4o": "copilot-gpt-4",
            "gpt-4o-mini": "copilot-gpt-3.5-turbo",
            "gpt-3.5-turbo": "copilot-gpt-3.5-turbo",
            "claude-3-5-sonnet-20241022": "claude-sonnet-4",  # Legacy mapping
            "claude-sonnet-4": "claude-sonnet-4",  # Pass through
            "claude-sonnet-4.5": "claude-sonnet-4.5",  # Pass through
            "claude-opus-4": "claude-opus-4",  # Pass through
        }

        return default_mappings.get(openai_model)

    def _build_model_capabilities(self, model: str) -> dict[str, Any]:
        """Build capabilities dictionary for model.

        Args:
            model: GitHub Copilot model name

        Returns:
            Capabilities dictionary.
        """
        # Default capabilities
        capabilities = {
            "streaming": True,
            "function_calling": False,
            "context_window": 8192,
            "max_output_tokens": 4096,
            "supports_system_message": True,
            "supports_images": False,
        }

        # Model-specific capabilities
        if "gpt-4" in model.lower():
            capabilities.update(
                {
                    "context_window": 128000,
                    "max_output_tokens": 8192,
                    "function_calling": True,
                }
            )
        elif "gpt-3.5" in model.lower():
            capabilities.update(
                {
                    "context_window": 16384,
                    "max_output_tokens": 4096,
                    "function_calling": True,
                }
            )
        elif "claude" in model.lower():
            capabilities.update(
                {
                    "context_window": 200000,
                    "max_output_tokens": 8192,
                    "function_calling": True,
                    "supports_images": True,  # Claude supports vision
                }
            )

        # GitHub Copilot specific adjustments
        if "copilot" in model.lower():
            capabilities.update(
                {
                    "code_generation": True,
                    "code_completion": True,
                    "supports_programming_languages": True,
                }
            )

        return capabilities

    def get_supported_languages(self, model: str) -> set[str]:
        """Get programming languages supported by model.

        Args:
            model: GitHub Copilot model name

        Returns:
            Set of supported programming language names.
        """
        # GitHub Copilot supports a wide range of programming languages
        return {
            "python",
            "javascript",
            "typescript",
            "java",
            "c",
            "cpp",
            "csharp",
            "go",
            "rust",
            "php",
            "ruby",
            "swift",
            "kotlin",
            "scala",
            "r",
            "shell",
            "bash",
            "powershell",
            "sql",
            "html",
            "css",
            "json",
            "yaml",
            "xml",
            "markdown",
            "dockerfile",
            "makefile",
        }

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for model usage.

        Args:
            model: GitHub Copilot model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD (may be 0 for GitHub Copilot subscription).
        """
        # GitHub Copilot is typically subscription-based, not pay-per-token
        # Return 0 for cost estimation, but could be extended for enterprise pricing
        return 0.0

    def validate_model_name(self, model_name: Any) -> bool:
        """Validate model name format for security.

        Simplified validation focused on actual threats in this system:
        - Type and emptiness checks
        - Length limits
        - Character pattern validation (alphanumeric + hyphens/dots)
        - ASCII-only (reject unicode)

        Removed future-proofing:
        - SQL injection checks (no database queries with model names)
        - XSS checks (no HTML rendering of model names)

        Args:
            model_name: Model name to validate

        Returns:
            True if valid

        Raises:
            ValueError: If model name is invalid
            TypeError: If model_name is not a string
        """
        # Type check
        if not isinstance(model_name, str):
            raise TypeError(f"Model name must be string, got {type(model_name)}")

        # Empty check
        if not model_name or len(model_name) == 0:
            raise ValueError("Invalid model name: empty string")

        # Length check (reasonable max length)
        if len(model_name) > 200:
            raise ValueError(f"Invalid model name: too long ({len(model_name)} chars)")

        # Valid pattern: lowercase alphanumeric, hyphens, dots, underscores only
        # Must start with lowercase letter (model names are always lowercase)
        valid_pattern = re.compile(r"^[a-z][a-z0-9\-\.]{0,199}$")

        if not valid_pattern.match(model_name):
            raise ValueError(f"Invalid model name: {model_name}")

        # Check for path traversal (legitimate security concern)
        if ".." in model_name or "/" in model_name or "\\" in model_name:
            raise ValueError("Invalid model name: contains forbidden characters")

        # Check for newlines (header injection - legitimate concern)
        if "\n" in model_name or "\r" in model_name:
            raise ValueError("Invalid model name: contains newline characters")

        # Check for null bytes (legitimate security concern)
        if "\x00" in model_name:
            raise ValueError("Invalid model name: contains null byte")

        # Check for non-ASCII characters (unicode)
        if not model_name.isascii():
            raise ValueError("Invalid model name: contains non-ASCII characters")

        return True
