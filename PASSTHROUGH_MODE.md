# Passthrough Mode

Passthrough mode is a feature that allows the proxy to start with the Anthropic API and automatically switch to Azure OpenAI fallback when encountering 429 rate limit errors.

## Overview

When passthrough mode is enabled, the proxy will:

1. **Start with Anthropic API**: All Claude model requests are first sent to the official Anthropic API
2. **Monitor for 429 errors**: When the Anthropic API returns a 429 rate limit error, the proxy records the failure
3. **Switch to Azure fallback**: After a configurable number of failures, subsequent requests are automatically routed to Azure OpenAI
4. **Automatic recovery**: After a timeout period without failures, the proxy switches back to Anthropic API

## Configuration

### Environment Variables

| Variable                              | Default | Description                                       |
| ------------------------------------- | ------- | ------------------------------------------------- |
| `PASSTHROUGH_MODE`                    | `false` | Enable passthrough mode                           |
| `PASSTHROUGH_FALLBACK_ENABLED`        | `true`  | Enable Azure OpenAI fallback                      |
| `PASSTHROUGH_MAX_RETRIES`             | `3`     | Maximum retries before giving up                  |
| `PASSTHROUGH_RETRY_DELAY`             | `1.0`   | Delay between retries (seconds)                   |
| `PASSTHROUGH_FALLBACK_AFTER_FAILURES` | `2`     | Number of 429 errors before switching to fallback |

### Required API Keys

For passthrough mode to work, you need:

1. **Anthropic API Key**: `ANTHROPIC_API_KEY`
2. **Azure OpenAI Configuration** (for fallback):
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_VERSION` (optional, defaults to `2024-02-01`)

### Model Mappings

Configure how Claude models map to your Azure deployments:

| Claude Model                 | Environment Variable             | Default Azure Model |
| ---------------------------- | -------------------------------- | ------------------- |
| `claude-3-5-sonnet-20241022` | `AZURE_CLAUDE_SONNET_DEPLOYMENT` | `gpt-4`             |
| `claude-3-5-haiku-20241022`  | `AZURE_CLAUDE_HAIKU_DEPLOYMENT`  | `gpt-4o-mini`       |
| `claude-3-opus-20240229`     | `AZURE_CLAUDE_OPUS_DEPLOYMENT`   | `gpt-4`             |
| `claude-3-sonnet-20240229`   | `AZURE_CLAUDE_SONNET_DEPLOYMENT` | `gpt-4`             |
| `claude-3-haiku-20240307`    | `AZURE_CLAUDE_HAIKU_DEPLOYMENT`  | `gpt-4o-mini`       |

## Quick Start

1. **Copy the example configuration**:

   ```bash
   cp .env.passthrough.example .env
   ```

2. **Edit the configuration**:
   - Add your Anthropic API key
   - Add your Azure OpenAI endpoint and API key
   - Configure the deployment mappings

3. **Start the proxy**:

   ```bash
   python -m amplihack.proxy.server
   ```

4. **Test the proxy**:
   ```bash
   curl -X POST http://localhost:8080/v1/messages \
     -H "Content-Type: application/json" \
     -H "x-api-key: your-anthropic-key" \
     -d '{
       "model": "claude-3-5-sonnet-20241022",
       "max_tokens": 1000,
       "messages": [{"role": "user", "content": "Hello!"}]
     }'
   ```

## How It Works

### Normal Operation

```
Client Request → Proxy → Anthropic API → Response → Client
```

### During Rate Limiting

```
Client Request → Proxy → Anthropic API (429 Error)
                    ↓
                 Azure OpenAI → Response → Client
```

### Request Flow

1. **Request Received**: Client sends request to proxy
2. **Model Detection**: Proxy detects Claude model in request
3. **Passthrough Check**: If passthrough mode enabled and Claude model detected
4. **Primary Attempt**: Try Anthropic API first
5. **Error Handling**: If 429 error received, record failure
6. **Fallback Decision**: If failure count exceeds threshold, use Azure
7. **Response Conversion**: Convert Azure response back to Anthropic format

### Failure Tracking

The proxy maintains a failure counter that:

- Increments on each 429 error from Anthropic
- Resets to zero on successful Anthropic responses
- Triggers fallback mode when threshold is reached
- Resets after a timeout period (5 minutes default)

## Monitoring

### Status Endpoint

Check the proxy status at `GET /status`:

```json
{
  "proxy_active": true,
  "passthrough_mode": true,
  "passthrough_status": {
    "passthrough_enabled": true,
    "fallback_enabled": true,
    "anthropic_configured": true,
    "azure_configured": true,
    "failure_count": 0,
    "using_fallback": false,
    "last_failure_time": 0,
    "max_retries": 3,
    "fallback_after_failures": 2
  }
}
```

### Logging

The proxy logs important events:

- Passthrough mode activation
- API switching (Anthropic ↔ Azure)
- Failure tracking
- Configuration validation

## Limitations

1. **Streaming**: Streaming responses are not yet implemented for passthrough mode
2. **Tool Calls**: Complex tool interactions may have slight formatting differences between APIs
3. **Model Features**: Some Claude-specific features may not be available through Azure mappings

## Troubleshooting

### Common Issues

1. **Invalid API Keys**:

   ```
   Passthrough mode requires ANTHROPIC_API_KEY
   Passthrough fallback requires AZURE_OPENAI_API_KEY
   ```

2. **Missing Azure Configuration**:

   ```
   Passthrough fallback requires AZURE_OPENAI_ENDPOINT
   ```

3. **Deployment Not Found**:
   - Check your Azure deployment names
   - Ensure deployment mappings are correctly configured

### Testing

Run the test suite to verify your configuration:

```bash
python test_passthrough_mode.py
```

For integration testing:

```bash
python test_passthrough_integration.py
```

## Example Configuration

See `.env.passthrough.example` for a complete configuration example.

## Security Notes

- API keys are never logged or exposed in error messages
- All communication with APIs uses HTTPS
- Sensitive configuration is sanitized in logs
- No API keys are stored persistently
