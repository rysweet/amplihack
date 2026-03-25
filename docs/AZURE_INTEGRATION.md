# Azure OpenAI Integration Guide

This guide covers Azure OpenAI configuration for Amplihack.

## Configuration Reference

### Required Variables

```env
# Your Azure OpenAI API key
OPENAI_API_KEY="your-azure-openai-api-key-here"  # pragma: allowlist secret

# Azure OpenAI endpoint URL with deployment and API version
OPENAI_BASE_URL="https://your-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"

# Azure-specific settings
AZURE_OPENAI_KEY="your-azure-openai-api-key-here"
AZURE_API_VERSION="2025-01-01-preview"
```

## Azure Endpoint URL Format

Your `OPENAI_BASE_URL` should follow this pattern:

```
https://<resource-name>.openai.azure.com/openai/deployments/<deployment-name>/chat/completions?api-version=<version>
```

**Examples:**

```env
# GPT-4 deployment
OPENAI_BASE_URL="https://mycompany-ai.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"

# GPT-4o deployment
OPENAI_BASE_URL="https://eastus-openai.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview"

# Custom deployment name
OPENAI_BASE_URL="https://prod-ai.openai.azure.com/openai/deployments/my-gpt4-model/chat/completions?api-version=2025-01-01-preview"

# Azure Responses API (for structured output)
OPENAI_BASE_URL="https://mycompany-ai.openai.azure.com/openai/responses?api-version=2025-04-01-preview"
```

## Troubleshooting

### Authentication Errors

**Error:** `401 Unauthorized` or `403 Forbidden`

**Solutions:**

1. **Verify API key**: Test with `curl` directly to Azure endpoint
2. **Check permissions**: Ensure key has access to the deployment
3. **Validate endpoint**: Confirm deployment name and resource name

### Connection Timeouts

**Error:** `Request timed out` or slow responses

**Solutions:**

1. **Check region**: Use Azure region closest to your location
2. **Verify endpoint**: Ensure the endpoint URL is correct

### Model Not Found

**Error:** `The model 'gpt-4' does not exist`

**Solutions:**

1. **Check deployment name**: Verify exact deployment name in Azure portal
2. **Update URL**: Ensure `OPENAI_BASE_URL` uses correct deployment

### Security Best Practices

1. **Secure credentials**: Never commit `.azure.env` to git
2. **Regular key rotation**: Rotate Azure API keys periodically
3. **Monitor usage**: Use Azure monitoring for API usage tracking
4. **Network security**: Consider VPN/private endpoints for production

## Support

### Common Questions

**Q: Does this work with Azure Government Cloud?**
A: Yes, use the appropriate Azure Government endpoints (e.g., `*.azure.us`).

**Q: What Azure API versions are supported?**
A: The integration supports all current Azure OpenAI API versions. Use the latest stable version (e.g., `2025-01-01-preview`) for best results.

### Getting Help

If you encounter issues:

1. **Test direct connection**: Use `curl` to test Azure endpoint directly
2. **Validate configuration**: Use Azure portal to verify deployment names
3. **Update integration**: Ensure you're using the latest version
