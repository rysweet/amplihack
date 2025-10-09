"""Unit tests for Azure endpoint detection."""

from amplihack.proxy.azure_detector import AzureEndpointDetector


class TestAzureEndpointDetector:
    """Test Azure endpoint detection patterns."""

    def test_detect_openai_azure_com(self):
        """Detect standard openai.azure.com endpoint."""
        detector = AzureEndpointDetector()
        assert detector.validate_azure_endpoint("https://my-resource.openai.azure.com")

    def test_detect_openai_azure_us(self):
        """Detect US government cloud endpoint."""
        detector = AzureEndpointDetector()
        assert detector.validate_azure_endpoint("https://my-resource.openai.azure.us")

    def test_detect_openai_azure_cn(self):
        """Detect China cloud endpoint."""
        detector = AzureEndpointDetector()
        assert detector.validate_azure_endpoint("https://my-resource.openai.azure.cn")

    def test_detect_cognitiveservices_domain(self):
        """Detect cognitiveservices.azure.com endpoint."""
        detector = AzureEndpointDetector()
        assert detector.validate_azure_endpoint(
            "https://ai-adapt-oai-eastus2.cognitiveservices.azure.com"
        )

    def test_reject_non_https(self):
        """Reject non-HTTPS endpoints for security."""
        detector = AzureEndpointDetector()
        assert not detector.validate_azure_endpoint("http://my-resource.openai.azure.com")

    def test_reject_non_azure_domain(self):
        """Reject non-Azure domains."""
        detector = AzureEndpointDetector()
        assert not detector.validate_azure_endpoint("https://api.openai.com")
        assert not detector.validate_azure_endpoint("https://example.com")

    def test_endpoint_with_path(self):
        """Accept Azure endpoints with paths."""
        detector = AzureEndpointDetector()
        assert detector.validate_azure_endpoint(
            "https://my-resource.openai.azure.com/openai/deployments/gpt-4"
        )

    def test_is_azure_endpoint_with_base_url(self):
        """Test is_azure_endpoint with base_url parameter."""
        detector = AzureEndpointDetector()
        assert detector.is_azure_endpoint(base_url="https://my-resource.openai.azure.com")
        assert not detector.is_azure_endpoint(base_url="https://api.openai.com")

    def test_is_azure_endpoint_with_config(self):
        """Test is_azure_endpoint with config dict."""
        detector = AzureEndpointDetector()

        # With Azure-specific config vars
        config = {
            "AZURE_OPENAI_ENDPOINT": "https://my-resource.openai.azure.com",
            "AZURE_OPENAI_KEY": "test-key",  # pragma: allowlist secret
        }
        assert detector.is_azure_endpoint(config=config)

        # With OpenAI config vars
        config = {"OPENAI_API_KEY": "test-key"}  # pragma: allowlist secret
        assert not detector.is_azure_endpoint(config=config)

    def test_extract_resource_name(self):
        """Test extracting Azure resource name from endpoint."""
        detector = AzureEndpointDetector()

        assert (
            detector.extract_azure_resource_name("https://my-resource.openai.azure.com")
            == "my-resource"
        )

        assert (
            detector.extract_azure_resource_name(
                "https://ai-adapt-oai-eastus2.cognitiveservices.azure.com"
            )
            == "ai-adapt-oai-eastus2"
        )

    def test_get_endpoint_type(self):
        """Test endpoint type detection."""
        detector = AzureEndpointDetector()

        assert (
            detector.get_endpoint_type(base_url="https://my-resource.openai.azure.com") == "azure"
        )

        assert detector.get_endpoint_type(base_url="https://api.openai.com") == "openai"

        # With config
        config = {"AZURE_OPENAI_KEY": "test"}  # pragma: allowlist secret
        assert detector.get_endpoint_type(config=config) == "azure"

    def test_caching_behavior(self):
        """Test that validation results are cached."""
        detector = AzureEndpointDetector()
        endpoint = "https://my-resource.openai.azure.com"

        # First call validates
        result1 = detector.validate_azure_endpoint(endpoint)

        # Second call should use cache
        result2 = detector.validate_azure_endpoint(endpoint)

        assert result1 is True
        assert result2 is True

        # Cache should contain the endpoint
        assert endpoint in detector._validation_cache
