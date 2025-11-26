"""Azure OpenAI model mapping."""

from typing import Any


class AzureModelMapper:
    """Maps OpenAI model names to Azure deployment names."""

    # Use __slots__ to reduce memory usage and improve attribute access speed
    __slots__ = ("_deployment_cache", "_normalized_name_cache", "config")

    # Default model mappings for common patterns
    DEFAULT_MODEL_MAPPINGS = {
        "gpt-4": "AZURE_GPT4_DEPLOYMENT",
        "gpt-4o": "AZURE_GPT4_DEPLOYMENT",
        "gpt-4o-mini": "AZURE_GPT4_MINI_DEPLOYMENT",
        "gpt-4-turbo": "AZURE_GPT4_TURBO_DEPLOYMENT",
        "gpt-3.5-turbo": "AZURE_GPT35_DEPLOYMENT",
        "gpt-35-turbo": "AZURE_GPT35_DEPLOYMENT",
        "BIG_MODEL": "AZURE_BIG_MODEL_DEPLOYMENT",
        "SMALL_MODEL": "AZURE_SMALL_MODEL_DEPLOYMENT",
    }

    # Reasoning models that require max_completion_tokens parameter
    REASONING_MODELS = {"gpt-5", "o3", "o4", "o3-mini", "o4-mini", "gpt-5-mini"}

    def __init__(self, config: dict[str, str]):
        """Initialize model mapper with configuration.

        Args:
            config: Configuration dictionary with environment variables
        """
        self.config = config

        # Cache for model deployment lookups to avoid repeated computations
        self._deployment_cache = {}
        self._normalized_name_cache = {}

        # Pre-populate cache with default mappings for better performance
        for model, deployment_var in self.DEFAULT_MODEL_MAPPINGS.items():
            if deployment_var in config:
                self._deployment_cache[model] = config[deployment_var]

    def get_azure_deployment(self, model_name: str) -> str | None:
        """Get Azure deployment name for OpenAI model.

        Args:
            model_name: OpenAI model name

        Returns:
            Azure deployment name if mapping exists, None otherwise
        """
        # Check cache first - most common case
        if model_name in self._deployment_cache:
            return self._deployment_cache[model_name]

        # Check direct deployment mapping first
        deployment_var = self.DEFAULT_MODEL_MAPPINGS.get(model_name)
        if deployment_var and deployment_var in self.config:
            result = self.config[deployment_var]
            self._deployment_cache[model_name] = result
            return result

        # Check for exact model name mapping
        model_deployment_var = f"AZURE_{model_name.upper().replace('-', '_')}_DEPLOYMENT"
        if model_deployment_var in self.config:
            result = self.config[model_deployment_var]
            self._deployment_cache[model_name] = result
            return result

        # Check for normalized model name mapping (use cached normalization)
        normalized = self._normalize_model_name(model_name)
        normalized_var = f"AZURE_{normalized}_DEPLOYMENT"
        if normalized_var in self.config:
            result = self.config[normalized_var]
            self._deployment_cache[model_name] = result
            return result

        # Cache negative result to avoid repeated processing
        self._deployment_cache[model_name] = None
        return None

    def is_reasoning_model(self, model_name: str) -> bool:
        """Check if model is a reasoning model requiring parameter conversion.

        Args:
            model_name: Model name to check

        Returns:
            True if reasoning model, False otherwise
        """
        return model_name.lower() in {m.lower() for m in self.REASONING_MODELS}

    def convert_parameters_for_reasoning(self, params: dict[str, Any]) -> dict[str, Any]:
        """Convert parameters for reasoning models.

        Args:
            params: Original parameters

        Returns:
            Converted parameters with max_tokens -> max_completion_tokens
        """
        converted = params.copy()

        # Convert max_tokens to max_completion_tokens for reasoning models
        if "max_tokens" in converted:
            converted["max_completion_tokens"] = converted.pop("max_tokens")

        return converted

    def get_model_mapping_config(self) -> dict[str, str]:
        """Get all model mapping configuration.

        Returns:
            Dictionary of model mappings from config
        """
        mappings = {}

        # Get all Azure deployment configurations
        for key, value in self.config.items():
            if key.startswith("AZURE_") and key.endswith("_DEPLOYMENT"):
                # Extract model name from deployment variable
                model_part = key[6:-11]  # Remove AZURE_ and _DEPLOYMENT
                mappings[model_part] = value

        return mappings

    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model name for deployment mapping.

        Args:
            model_name: Original model name

        Returns:
            Normalized model name for environment variable lookup
        """
        # Check cache first to avoid repeated string operations
        if model_name in self._normalized_name_cache:
            return self._normalized_name_cache[model_name]

        # Perform normalization once and cache result
        normalized = model_name.upper().replace("-", "_").replace(".", "_")

        # Handle special cases
        if normalized.startswith("GPT_3_5"):
            normalized = normalized.replace("GPT_3_5", "GPT35")
        elif normalized.startswith("GPT_4"):
            normalized = normalized.replace("GPT_4", "GPT4")

        # Cache result for future lookups
        self._normalized_name_cache[model_name] = normalized
        return normalized
