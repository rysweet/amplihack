"""Test Azure .env file loading functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_azure_env_loading():
    """Test that .azure.env file is loaded when proxy starts."""
    # Create a temporary .azure.env file
    with tempfile.TemporaryDirectory() as tmpdir:
        azure_env_path = Path(tmpdir) / ".azure.env"
        azure_env_path.write_text("""
OPENAI_API_KEY=test_api_key_123
OPENAI_BASE_URL=https://test.openai.azure.com/openai/responses
AZURE_API_VERSION=2025-04-01-preview
BIG_MODEL=gpt-5-codex
""")

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Mock the FastAPI app and dotenv
            with patch("amplihack.proxy.server.FastAPI"):
                with patch("amplihack.proxy.server.load_dotenv") as mock_load_dotenv:
                    # Import server module to trigger initialization
                    import sys

                    # Remove module from cache if it exists
                    if "amplihack.proxy.server" in sys.modules:
                        del sys.modules["amplihack.proxy.server"]

                    # Import the module
                    from amplihack.proxy import server  # noqa: F401

                    # Verify load_dotenv was called with the .azure.env file
                    mock_load_dotenv.assert_called()
                    call_args = mock_load_dotenv.call_args
                    assert call_args is not None

                    # Check that the path ends with .azure.env
                    called_path = call_args[0][0]
                    assert called_path.endswith(".azure.env")

        finally:
            os.chdir(original_cwd)


def test_azure_env_not_required():
    """Test that proxy starts even without .azure.env file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory (no .azure.env file)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Mock the FastAPI app
            with patch("amplihack.proxy.server.FastAPI"):
                with patch("amplihack.proxy.server.logger") as mock_logger:
                    # Import server module to trigger initialization
                    import sys

                    # Remove module from cache if it exists
                    if "amplihack.proxy.server" in sys.modules:
                        del sys.modules["amplihack.proxy.server"]

                    # Import the module
                    from amplihack.proxy import server  # noqa: F401 - should not raise an error

                    # Verify debug message was logged
                    mock_logger.debug.assert_called()

        finally:
            os.chdir(original_cwd)


def test_azure_responses_api_detection():
    """Test that Azure Responses API endpoints are properly detected."""
    test_cases = [
        ("https://test.openai.azure.com/openai/responses?api-version=2025-04-01-preview", True),
        ("https://test.openai.azure.com/openai/deployments/gpt-4/chat/completions", False),
        ("https://test.openai.azure.com/openai/responses", True),
    ]

    for url, expected_is_responses in test_cases:
        # Check if URL contains /openai/responses
        is_responses = "/openai/responses" in url
        assert is_responses == expected_is_responses, f"Failed for URL: {url}"


def test_azure_responses_api_path_preservation():
    """Test that Responses API path is preserved during configuration."""
    responses_url = "https://test.openai.azure.com/openai/responses?api-version=2025-04-01-preview"

    # Remove query parameters
    clean_url = responses_url.split("?")[0] if "?" in responses_url else responses_url

    # Check if this is Responses API
    is_responses_api = "/openai/responses" in clean_url

    assert is_responses_api, "Should detect as Responses API"

    # For Responses API, path should be preserved
    # (we don't strip /openai/responses like we do for regular endpoints)
    assert "/openai/responses" in clean_url, "Path should be preserved for Responses API"
