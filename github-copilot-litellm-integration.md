# GitHub Copilot LiteLLM Integration

This document describes the GitHub Copilot Language Model API integration with LiteLLM provider support in the agentic coding framework.

## Overview

The GitHub Copilot LiteLLM integration provides:

- **OAuth Device Flow Authentication**: Secure GitHub authentication with Copilot access
- **LiteLLM Provider Support**: Standardized integration following LiteLLM's GitHub Copilot provider
- **Model Mapping**: Seamless mapping between OpenAI and GitHub Copilot models
- **Enhanced Configuration**: Extended .env configuration for GitHub Copilot settings
- **Proxy Integration**: Full integration with existing proxy server architecture

## Features

### OAuth Device Flow

- GitHub OAuth device flow for secure authentication
- Automatic detection and usage of existing `gh auth login` tokens
- Token validation and refresh management
- Secure token storage and handling

### LiteLLM Provider Integration

- Native LiteLLM GitHub Copilot provider support
- Automatic model prefix handling (`github/copilot-gpt-4`)
- Request/response transformation for OpenAI compatibility
- Streaming response support

### Model Support

- `copilot-gpt-4`: GitHub Copilot's GPT-4 model
- `copilot-gpt-3.5-turbo`: GitHub Copilot's GPT-3.5 Turbo model
- Automatic mapping from OpenAI model names
- Custom model configuration support

## Configuration

### Environment Variables

Add these variables to your `.env` or `.github.env` file:

```bash
# Required: GitHub token with Copilot access
GITHUB_TOKEN=gho_your_github_token_here  # pragma: allowlist secret

# Enable GitHub Copilot proxy mode
GITHUB_COPILOT_ENABLED=true
PROXY_TYPE=github_copilot

# Enable LiteLLM GitHub Copilot provider integration
GITHUB_COPILOT_LITELLM_ENABLED=true

# Optional: Specify default GitHub Copilot model
GITHUB_COPILOT_MODEL=copilot-gpt-4

# Optional: GitHub Copilot endpoint (defaults to api.github.com)
GITHUB_COPILOT_ENDPOINT=https://api.github.com

# Proxy server settings
PORT=8080
HOST=localhost

# Performance settings
REQUEST_TIMEOUT=300
MAX_RETRIES=3
LOG_LEVEL=INFO

# Optional: Rate limiting (GitHub Copilot has built-in limits)
MAX_TOKENS_LIMIT=8192
```

### Example Configuration

Copy and customize the example configuration:

```bash
cp examples/example.github.env .github.env
# Edit .github.env with your GitHub token
```

## Authentication Setup

### Option 1: Use Existing GitHub CLI Token

If you have GitHub CLI installed and authenticated:

```bash
gh auth login --scopes copilot
```

The integration will automatically detect and use your existing token.

### Option 2: OAuth Device Flow

If no existing token is found, the system will initiate OAuth device flow:

1. Start the proxy server
2. Visit the provided GitHub authorization URL
3. Enter the device code
4. Complete GitHub OAuth authorization
5. Token is automatically saved for future use

### Option 3: Manual Token

Generate a personal access token with Copilot scope:

1. Visit https://github.com/settings/tokens
2. Generate new token with `copilot` scope
3. Add to your `.github.env` file

## Usage

### Starting the Proxy

```bash
# Set environment variables
export GITHUB_TOKEN="your_github_token"  # pragma: allowlist secret
export GITHUB_COPILOT_ENABLED="true"
export GITHUB_COPILOT_LITELLM_ENABLED="true"

# Start proxy server
python src/amplihack/proxy/server.py
```

### Making Requests

Use standard OpenAI API format with GitHub Copilot models:

```python
import openai

# Configure client to use proxy
client = openai.OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed"  # pragma: allowlist secret
)

# Request with GitHub Copilot model
response = client.chat.completions.create(
    model="copilot-gpt-4",  # or "github/copilot-gpt-4"
    messages=[
        {"role": "user", "content": "Hello, GitHub Copilot!"}
    ]
)

print(response.choices[0].message.content)
```

### Model Mapping

The integration automatically maps models:

| OpenAI Model    | GitHub Copilot Model    | LiteLLM Format                 |
| --------------- | ----------------------- | ------------------------------ |
| `gpt-4`         | `copilot-gpt-4`         | `github/copilot-gpt-4`         |
| `gpt-3.5-turbo` | `copilot-gpt-3.5-turbo` | `github/copilot-gpt-3.5-turbo` |

You can use any of these formats in your requests.

## Architecture

### Components

1. **GitHubEndpointDetector**: Detects GitHub Copilot endpoints and validates configuration
2. **GitHubAuthManager**: Handles OAuth device flow and token management
3. **GitHubCopilotClient**: Direct GitHub Copilot API client (fallback)
4. **ProxyConfig**: Extended configuration management for GitHub Copilot
5. **LiteLLM Integration**: Native LiteLLM provider support in proxy server

### Request Flow

1. Client sends request to proxy server
2. Proxy detects GitHub Copilot model
3. Request is routed to LiteLLM GitHub provider
4. LiteLLM handles GitHub Copilot API communication
5. Response is transformed to OpenAI format
6. Client receives standard OpenAI response

### Authentication Flow

1. Check for existing GitHub CLI token
2. If found and valid, use for LiteLLM provider
3. If not found, initiate OAuth device flow
4. Save token for future use
5. Configure LiteLLM provider with token

## Testing

Run comprehensive tests for the integration:

```bash
# Run all GitHub Copilot tests
pytest tests/proxy/test_github_copilot_litellm_integration.py -v

# Run specific test categories
pytest tests/proxy/test_github_copilot_litellm_integration.py::TestGitHubCopilotLiteLLMIntegration::test_github_copilot_model_mapping -v

# Run with coverage
pytest tests/proxy/test_github_copilot_litellm_integration.py --cov=src.amplihack.proxy
```

### Test Coverage

The test suite covers:

- LiteLLM provider detection and configuration
- GitHub OAuth integration
- Model mapping and validation
- Configuration validation
- Request/response processing
- Error handling and edge cases
- Rate limiting and endpoint validation

## Troubleshooting

### Common Issues

**1. Authentication Errors**

```
Error: Missing required GitHub configuration: GITHUB_TOKEN
```

- Ensure GitHub token is set in environment or .env file
- Verify token has `copilot` scope
- Check token format (starts with `gho_`, `ghp_`, etc.)

**2. Model Not Found**

```
Error: Model 'copilot-gpt-4' not found
```

- Verify GitHub Copilot access on your account
- Check model availability in your region
- Ensure LiteLLM provider is properly configured

**3. Rate Limiting**

```
Error: Rate limit exceeded
```

- GitHub Copilot has built-in rate limits
- Implement request throttling
- Check your Copilot subscription status

**4. LiteLLM Provider Issues**

```
Error: LiteLLM GitHub provider not found
```

- Ensure LiteLLM is updated to latest version
- Verify GitHub provider support in your LiteLLM version
- Check LiteLLM configuration

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
```

This will show detailed request/response logs and model mapping information.

### Token Validation

Test your GitHub token:

```python
from src.amplihack.proxy.github_auth import GitHubAuthManager

auth = GitHubAuthManager()
token = "your_github_token"
is_valid = auth._verify_copilot_access(token)
print(f"Token valid: {is_valid}")
```

## Security Considerations

- GitHub tokens are transmitted over HTTPS only
- Tokens are not logged in debug output
- OAuth device flow uses secure GitHub endpoints
- Rate limiting prevents token abuse
- Token validation before usage

## Performance

- LiteLLM provider provides optimized GitHub Copilot access
- Request/response caching when appropriate
- Streaming support for real-time responses
- Efficient token management and reuse

## Limitations

- Requires GitHub Copilot subscription
- Limited to GitHub Copilot model availability
- Subject to GitHub Copilot rate limits
- Regional availability restrictions may apply

## Contributing

When contributing to the GitHub Copilot integration:

1. Follow the existing architecture patterns
2. Add comprehensive tests for new features
3. Update configuration documentation
4. Ensure backward compatibility
5. Test with both OAuth flows and direct tokens

## License

This integration follows the same license as the main project.
