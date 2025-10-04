# Azure OpenAI Integration Guide

This guide covers the comprehensive Azure OpenAI integration for AmplihHack, including setup, configuration, troubleshooting, and advanced usage scenarios.

## Quick Start

### 1. Basic Setup (< 5 minutes)

```bash
# 1. Copy the example configuration
cp examples/example.azure.env .azure.env

# 2. Edit with your Azure credentials
nano .azure.env  # Set OPENAI_API_KEY, OPENAI_BASE_URL, etc.

# 3. Launch with Azure integration
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding@feat/issue-676-azure-openai-proxy amplihack launch --with-proxy-config ./.azure.env
```

### 2. What Happens Automatically

- ✅ **Proxy Setup**: claude-code-proxy starts with Azure configuration
- ✅ **Model Mapping**: OpenAI model names → Azure deployment names
- ✅ **Persistence**: Azure persistence prompt automatically appended
- ✅ **Environment**: Proper environment variables configured

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

### Model Mapping

Map Claude's model tiers to your Azure deployments:

```env
# Maps to Claude's largest model
BIG_MODEL="gpt-4"
# Maps to Claude's mid-tier model
MIDDLE_MODEL="gpt-4"
# Maps to Claude's smallest/fastest model
SMALL_MODEL="gpt-4-turbo"
```

### Performance Settings

Optimized for large context windows:

```env
# Use localhost for security
HOST="127.0.0.1"
PORT="8082"
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL="INFO"

# 512k tokens - maximum context size
MAX_TOKENS_LIMIT="512000"
# Minimum tokens (to avoid errors with thinking model)
MIN_TOKENS_LIMIT="4096"
# 5 minutes for large requests
REQUEST_TIMEOUT="300"
# Retry on transient failures
MAX_RETRIES="2"
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
```

## Configuration Examples

### Single Model Setup

For simple setups using one Azure deployment:

```env
OPENAI_API_KEY="abcd1234..."  # pragma: allowlist secret
OPENAI_BASE_URL="https://myai.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"
AZURE_OPENAI_KEY="abcd1234..."
AZURE_API_VERSION="2025-01-01-preview"

BIG_MODEL="gpt-4"
MIDDLE_MODEL="gpt-4"
SMALL_MODEL="gpt-4"

HOST="127.0.0.1"
PORT="8082"
LOG_LEVEL="INFO"
REQUEST_TIMEOUT="300"
MAX_RETRIES="2"
```

### Multi-Model Setup

For environments with multiple Azure deployments:

```env
OPENAI_API_KEY="abcd1234..."  # pragma: allowlist secret
OPENAI_BASE_URL="https://multimodel.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"
AZURE_OPENAI_KEY="abcd1234..."
AZURE_API_VERSION="2025-01-01-preview"

# Different deployments for different model tiers
BIG_MODEL="gpt-4-32k"
MIDDLE_MODEL="gpt-4"
SMALL_MODEL="gpt-4o-mini"

HOST="127.0.0.1"
PORT="8082"
LOG_LEVEL="INFO"
REQUEST_TIMEOUT="300"
MAX_RETRIES="3"
```

### High-Performance Setup

For heavy usage with maximum context windows:

```env
OPENAI_API_KEY="abcd1234..."  # pragma: allowlist secret
OPENAI_BASE_URL="https://perf-ai.openai.azure.com/openai/deployments/gpt-4-turbo/chat/completions?api-version=2025-01-01-preview"
AZURE_OPENAI_KEY="abcd1234..."
AZURE_API_VERSION="2025-01-01-preview"

BIG_MODEL="gpt-4-turbo"
MIDDLE_MODEL="gpt-4-turbo"
SMALL_MODEL="gpt-4o"

HOST="127.0.0.1"
PORT="8082"
LOG_LEVEL="DEBUG"  # More detailed logging
MAX_TOKENS_LIMIT="512000"  # Maximum context
MIN_TOKENS_LIMIT="8192"    # Higher minimum for complex tasks
REQUEST_TIMEOUT="600"      # 10 minutes for very large requests
MAX_RETRIES="5"            # More retries for reliability
```

## Recent Fixes (PR #679)

### Fixed: REQUEST_TIMEOUT Parsing Error

**Problem**: Proxy failed to start with error:

```
ValueError: could not convert string to float: '"300"      # 5 minutes for large requests'
```

**Solution**: Enhanced configuration parser to handle inline comments in .env files.

## Known Issues (External Package)

### Issue: Internal Server Error from claude-code-proxy

**Problem**: The external `claude-code-proxy` package has bugs that cause Internal Server Errors:

```
TypeError: Object of type Response is not JSON serializable
```

**Root Cause**: Bug in the proxy's error handling code when trying to log Azure request failures.

**Impact**:

- ❌ Proxy returns "Internal Server Error" instead of proper responses
- ❌ No log file location output during startup
- ⚠️ Model mapping warnings for Azure deployments

**Workaround**: This is an external package issue that needs to be reported upstream to the `claude-code-proxy` maintainers.

**Before (Broken):**

```env
REQUEST_TIMEOUT="300"      # 5 minutes for large requests
```

**After (Fixed):**

```env
# 5 minutes for large requests
REQUEST_TIMEOUT="300"
```

### Fixed: Environment Variable Handling

- Added support for performance and server configuration variables
- Improved environment variable validation and sanitization
- Fixed cross-platform compatibility issues

### Fixed: Configuration Format Issues

- Enhanced .env file parsing to strip inline comments
- Better error messages for configuration problems
- Improved validation of Azure endpoint URLs

## Troubleshooting

### Proxy Won't Start

**Error:** `Proxy failed to start. Exit code: 1`

**Common Causes:**

1. **Inline comments in .env file**
   - **Solution**: Move comments to separate lines above variables
   - **Example**: Change `PORT="8082"  # comment` to separate lines

2. **Invalid Azure endpoint URL**
   - **Check**: URL format matches Azure OpenAI pattern
   - **Verify**: Deployment name exists in your Azure resource

3. **Missing or invalid API key**
   - **Check**: API key is correct and has proper permissions
   - **Verify**: Key works with direct Azure API calls

### Internal Server Error (NEW ISSUE)

**Error:** `Internal Server Error` responses when making requests to proxy

**Root Cause:** Bug in external `claude-code-proxy` package's error handling

**Diagnosis Steps:**

1. Check proxy logs for `TypeError: Object of type Response is not JSON serializable`
2. Look for model mapping warnings: `⚠️ No prefix or mapping rule for model`
3. Verify proxy starts but provides no log location output

**Solutions:**

1. **Report upstream**: This is a bug in the `claude-code-proxy` PyPI package
2. **Use alternative**: Consider direct Azure OpenAI integration
3. **Monitor status**: Check for updates to the external package

### Authentication Errors

**Error:** `401 Unauthorized` or `403 Forbidden`

**Solutions:**

1. **Verify API key**: Test with `curl` directly to Azure endpoint
2. **Check permissions**: Ensure key has access to the deployment
3. **Validate endpoint**: Confirm deployment name and resource name

### Connection Timeouts

**Error:** `Request timed out` or slow responses

**Solutions:**

1. **Increase timeout**: Set higher `REQUEST_TIMEOUT` value
2. **Check region**: Use Azure region closest to your location
3. **Reduce context**: Lower `MAX_TOKENS_LIMIT` if hitting limits

### Model Not Found

**Error:** `The model 'gpt-4' does not exist`

**Solutions:**

1. **Check deployment name**: Verify exact deployment name in Azure portal
2. **Update URL**: Ensure `OPENAI_BASE_URL` uses correct deployment
3. **Verify model mapping**: Check `BIG_MODEL`, `MIDDLE_MODEL`, `SMALL_MODEL` values

### Configuration Format Errors

**Error:** `Invalid configuration` or parsing errors

**Solutions:**

1. **No inline comments**: Move all comments to separate lines
2. **Proper quotes**: Use double quotes consistently: `KEY="value"`
3. **No trailing spaces**: Remove spaces after values
4. **Valid URLs**: Ensure endpoints start with `https://`

## Advanced Configuration

### Custom Model Deployments

If you have custom deployment names in Azure:

```env
# Map to your actual Azure deployment names
BIG_MODEL="my-company-gpt4-large"
MIDDLE_MODEL="my-company-gpt4-standard"
SMALL_MODEL="my-company-gpt35-fast"
```

### Multiple Azure Resources

For organizations with multiple Azure OpenAI resources:

```env
# Primary resource for large models
OPENAI_BASE_URL="https://primary.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"

# You can switch resources by changing the base URL
# Secondary resource would be:
# OPENAI_BASE_URL="https://secondary.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2025-01-01-preview"
```

### Security Best Practices

1. **Use localhost only**: Always set `HOST="127.0.0.1"`
2. **Secure credentials**: Never commit `.azure.env` to git
3. **Regular key rotation**: Rotate Azure API keys periodically
4. **Monitor usage**: Use Azure monitoring for API usage tracking
5. **Network security**: Consider VPN/private endpoints for production

### Monitoring and Logging

Enable detailed logging for troubleshooting:

```env
LOG_LEVEL="DEBUG"
```

Log files are automatically created in your system's temporary directory. The proxy will show the log file path when starting:

```
Logs will be written to:
  JSONL: /tmp/amplihack_logs/log-2025-10-04-19-16-16.jsonl
  HTML:  /tmp/amplihack_logs/log-2025-10-04-19-16-16.html
```

## Support

### Common Questions

**Q: Can I use multiple Azure deployments simultaneously?**
A: Currently, you configure one primary deployment via `OPENAI_BASE_URL`. Model mapping (`BIG_MODEL`, etc.) allows different deployments for different Claude model tiers.

**Q: Does this work with Azure Government Cloud?**
A: Yes, use the appropriate Azure Government endpoints (e.g., `*.azure.us`).

**Q: Can I switch between OpenAI and Azure dynamically?**
A: You need to restart with different configuration. Consider using multiple `.env` files for different providers.

**Q: What Azure API versions are supported?**
A: The integration supports all current Azure OpenAI API versions. Use the latest stable version (e.g., `2025-01-01-preview`) for best results.

### Getting Help

If you encounter issues:

1. **Check logs**: Review proxy logs for detailed error information
2. **Test direct connection**: Use `curl` to test Azure endpoint directly
3. **Validate configuration**: Use Azure portal to verify deployment names
4. **Update integration**: Ensure you're using the latest version with fixes

---

**Last Updated**: Based on PR #679 fixes for configuration parsing and environment handling.
