"""GitHub Copilot model mapping and capabilities."""

from typing import Any


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
