# Azure Proxy Testing Guide

## Overview

This guide explains how to test the Azure LiteLLM proxy integration with both
Chat API and Responses API endpoints.

## Prerequisites

1. Copy example configs and fill in your Azure credentials:

   ```bash
   cp docs/proxy/proxy_config_chat_api.env.example proxy_config_chat_api.env
   cp docs/proxy/proxy_config_responses_api.env.example proxy_config_responses_api.env
   ```

2. Edit both files and replace:
   - `your-api-key-here` with your actual Azure OpenAI API key
   - `your-resource` with your Azure resource name

## Test Commands

### Test Chat API (gpt-5)

Tests the Chat API endpoint with bash tool calling:

```bash
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git@feat/azure-endpoint-detection amplihack launch --with-proxy-config proxy_config_chat_api.env -- -p "List all Python files in the current directory using bash"
```

### Test Responses API (gpt-5-codex)

Tests the Responses API endpoint with bash tool calling:

```bash
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git@feat/azure-endpoint-detection amplihack launch --with-proxy-config proxy_config_responses_api.env -- -p "List all Python files in the current directory using bash"
```

## What to Verify

### Routing Verification

1. **Chat API Test**:
   - Should route through LiteLLM router
   - Model name: `gpt-5`
   - Endpoint: `/openai/deployments/gpt-5/chat/completions`
   - API Version: `2025-01-01-preview`

2. **Responses API Test**:
   - Should route through LiteLLM router
   - Model name: `gpt-5-codex`
   - Endpoint: `/openai/responses`
   - API Version: `2025-04-01-preview`

### Tool Calling Verification

Both tests should:

- Successfully invoke bash tool
- Execute `ls *.py` or equivalent
- Return list of Python files
- Show proper tool call formatting in response

## Expected Output

Successful test output should show:

1. Proxy initialization logs
2. LiteLLM router startup
3. Model routing decision
4. Tool call execution
5. Bash command output
6. Final response with file list

## Troubleshooting

### Authentication Errors

If you see auth errors:

- Verify Azure API key is correct
- Check Azure resource name matches deployment
- Ensure API version matches your deployment

### Routing Errors

If wrong endpoint is used:

- Check `OPENAI_BASE_URL` in config file
- Verify model name matches config (`gpt-5` vs `gpt-5-codex`)
- Review LiteLLM router logs for routing decision

### Tool Calling Errors

If bash tool doesn't work:

- Ensure `thinking` and `tool_choice` parameters supported
- Check Azure deployment supports function calling
- Verify API version is recent enough

## Configuration Details

### Chat API Config

```env
# Routes to /chat/completions endpoint
OPENAI_BASE_URL="https://your-resource.cognitiveservices.azure.com"
BIG_MODEL=gpt-5  # Uses Chat API
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

### Responses API Config

```env
# Routes to /responses endpoint
OPENAI_BASE_URL="https://your-resource.cognitiveservices.azure.com/openai/responses"
BIG_MODEL=gpt-5-codex  # Uses Responses API
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

## Architecture

The routing works as follows:

1. **amplihack** receives request with model name from config
2. **integrated_proxy.py** checks `should_use_responses_api_for_model()`
3. **azure_unified_integration.py** creates LiteLLM router with correct endpoint
4. **LiteLLM router** sends request to Azure with proper transformation
5. Response flows back through proxy to amplihack

Key files:

- `src/amplihack/proxy/integrated_proxy.py` - Routing logic
- `src/amplihack/proxy/azure_unified_integration.py` - LiteLLM configuration
- `src/amplihack/proxy/azure_unified_handler.py` - Request/response handling

## Success Criteria

✅ Both tests complete without errors ✅ Correct endpoints used for each model
✅ Bash tool calling works in both cases ✅ Responses show proper file listings
✅ No authentication or routing failures

## Notes

- Chat API and Responses API use different endpoints and API versions
- Model names determine routing: `gpt-5` → Chat, `gpt-5-codex` → Responses
- Both configs can work with same Azure resource (different deployments)
- Your actual .env files are .gitignored - secrets stay local
