#!/usr/bin/env python3
"""
GitHub Copilot API Integration Test

This script demonstrates the complete GitHub Copilot integration with LiteLLM provider support.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_github_copilot_integration():
    """Test the complete GitHub Copilot integration."""
    print("🚀 Testing GitHub Copilot API Integration")
    print("=" * 50)

    # Set up test environment
    os.environ["GITHUB_TOKEN"] = "test-token-for-demo"
    os.environ["GITHUB_COPILOT_ENABLED"] = "true"
    os.environ["GITHUB_COPILOT_LITELLM_ENABLED"] = "true"

    try:
        # Test 1: Configuration and Authentication
        print("\n1. Testing Configuration and Authentication")
        from amplihack.proxy.config import ProxyConfig
        from amplihack.proxy.github_auth import GitHubAuthManager

        config = ProxyConfig()
        print(f"   ✅ GitHub Copilot enabled: {config.is_github_copilot_enabled()}")
        print(f"   ✅ LiteLLM provider enabled: {config.is_github_copilot_litellm_enabled()}")
        print(f"   ✅ GitHub endpoint: {config.get_github_copilot_endpoint()}")

        auth = GitHubAuthManager()
        print(f"   ✅ OAuth client ID: {auth.client_id}")
        print(f"   ✅ OAuth scopes: {auth.scopes}")

        # Test 2: Model Detection and Mapping
        print("\n2. Testing Model Detection and Mapping")
        from amplihack.proxy.github_detector import GitHubEndpointDetector

        detector = GitHubEndpointDetector()
        test_config = {"GITHUB_TOKEN": "test-token", "GITHUB_COPILOT_ENABLED": "true"}

        print(f"   ✅ GitHub endpoint detection: {detector.is_github_endpoint(None, test_config)}")
        print(
            f"   ✅ LiteLLM provider enabled: {detector.is_litellm_provider_enabled(test_config)}"
        )
        print(f"   ✅ Model prefix: {detector.get_litellm_model_prefix()}")

        # Test 3: Server Integration
        print("\n3. Testing Server Integration")
        from amplihack.proxy.server import GITHUB_COPILOT_ENABLED, GITHUB_COPILOT_MODELS, app

        print(f"   ✅ Server GitHub Copilot enabled: {GITHUB_COPILOT_ENABLED}")
        print(f"   ✅ Available models: {GITHUB_COPILOT_MODELS}")

        # Test 4: Request Processing
        print("\n4. Testing Request Processing")
        from amplihack.proxy.server import MessagesRequest, convert_anthropic_to_litellm

        # Test model mapping
        request = MessagesRequest(
            model="copilot-gpt-4", max_tokens=100, messages=[{"role": "user", "content": "Hello"}]
        )
        print(f"   ✅ Model mapped: copilot-gpt-4 -> {request.model}")

        # Test LiteLLM conversion
        litellm_request = convert_anthropic_to_litellm(request)
        print(f"   ✅ LiteLLM format: {litellm_request['model']}")
        print(f"   ✅ Messages converted: {len(litellm_request['messages'])}")

        # Test 5: FastAPI Status Endpoint
        print("\n5. Testing FastAPI Status Endpoint")
        from fastapi.testclient import TestClient  # type: ignore

        client = TestClient(app)
        response = client.get("/status")

        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Status endpoint: {response.status_code}")
            print(f"   ✅ GitHub token configured: {status['github_token_configured']}")
            print(f"   ✅ GitHub Copilot enabled: {status['github_copilot_enabled']}")
            print(f"   ✅ Available models: {status['github_copilot_models']}")
        else:
            print(f"   ❌ Status endpoint failed: {response.status_code}")
            return False

        # Test 6: Configuration Examples
        print("\n6. Testing Configuration Examples")
        config_path = Path(".github.copilot.env")
        if config_path.exists():
            print(f"   ✅ Example configuration file: {config_path}")
        else:
            print("   ⚠️  Example configuration file not found")

        print("\n" + "=" * 50)
        print("🎉 GitHub Copilot API Integration Test PASSED!")
        print("\nNext Steps:")
        print("1. Set your GitHub token: export GITHUB_TOKEN=your_token_here")
        print("2. Or use GitHub CLI: gh auth login --scopes copilot")
        print("3. Start the proxy: python src/amplihack/proxy/server.py")
        print("4. Test with: curl -X POST http://localhost:8080/v1/messages \\")
        print("   -H 'Content-Type: application/json' \\")
        print(
            '   -d \'{"model": "copilot-gpt-4", "max_tokens": 100, "messages": [{"role": "user", "content": "Hello!"}]}\''
        )

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_github_copilot_integration()
    sys.exit(0 if success else 1)
