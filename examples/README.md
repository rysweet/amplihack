# Azure API Endpoint Configuration Examples

This directory contains configuration examples for both Azure API types supported by the URL-based endpoint detection system.

## 🔍 How URL-Based Detection Works

The proxy automatically detects which Azure API to use based on the endpoint URL structure:

### Chat API Detection

- **URL Pattern**: Contains `/chat` (e.g., `/chat/completions`)
- **Routing**: LiteLLM → Azure Chat Completions API
- **Models**: `gpt-5`, `gpt-4o`, etc.
- **Use Case**: Standard OpenAI-compatible chat completions

### Responses API Detection

- **URL Pattern**: Contains `/responses`
- **Routing**: Direct Azure calls → Azure Responses API
- **Models**: `gpt-5-codex`, Claude models
- **Use Case**: Enhanced tool calling, streaming optimizations

## 📁 Configuration Files

### Environment Files (.env)

#### `azure-chat-api.env`

- **Endpoint**: `https://...cognitiveservices.azure.com/openai/deployments/gpt-5/chat/completions`
- **Model**: `gpt-5`
- **Detection**: URL contains `/chat` → Routes through LiteLLM

#### `azure-responses-api.env`

- **Endpoint**: `https://...cognitiveservices.azure.com/openai/responses`
- **Model**: `gpt-5-codex`
- **Detection**: URL contains `/responses` → Direct Azure calls

### LiteLLM Configuration Files (.yaml)

#### `litellm-chat-api-config.yaml`

- Deployment-based URL structure for Chat API
- Azure model configuration (`azure/gpt-5`)
- Used when proxy detects Chat API endpoint

#### `litellm-responses-api-config.yaml`

- Reference configuration for Responses API
- Note: Actual routing bypasses LiteLLM for `/responses` endpoints

## 🚀 Quick Setup

### Option 1: Chat API (Standard GPT Models)

1. Copy `azure-chat-api.env` to `.azure.env`
2. Replace placeholders with your Azure details:
   ```bash
   # Replace with your resource name and API key
   OPENAI_BASE_URL="https://YOUR-RESOURCE.cognitiveservices.azure.com/openai/deployments/gpt-5/chat/completions?api-version=2025-01-01-preview"
   AZURE_OPENAI_KEY="YOUR-API-KEY-HERE"
   ```
3. Copy `litellm-chat-api-config.yaml` to `litellm_standalone_config.yaml`
4. Update with your resource details

### Option 2: Responses API (Enhanced Tool Calling)

1. Copy `azure-responses-api.env` to `.azure.env`
2. Replace placeholders with your Azure details:
   ```bash
   # Replace with your resource name and API key
   OPENAI_BASE_URL="https://YOUR-RESOURCE.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview"
   AZURE_OPENAI_KEY="YOUR-API-KEY-HERE"
   ```
3. Use model `gpt-5-codex` for requests

## 🧪 Testing Both Configurations

You can test both API types by switching the `OPENAI_BASE_URL`:

```bash
# Test Chat API
export OPENAI_BASE_URL="https://your-resource.cognitiveservices.azure.com/openai/deployments/gpt-5/chat/completions?api-version=2025-01-01-preview"

# Test Responses API
export OPENAI_BASE_URL="https://your-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview"
```

The proxy will automatically detect the API type and route accordingly.

## 🔧 Configuration Keys

### Required Settings

| Setting             | Chat API             | Responses API        | Description        |
| ------------------- | -------------------- | -------------------- | ------------------ |
| `OPENAI_BASE_URL`   | `/chat/completions`  | `/responses`         | Triggers detection |
| `AZURE_OPENAI_KEY`  | Your API key         | Your API key         | Authentication     |
| `AZURE_API_VERSION` | `2025-01-01-preview` | `2025-04-01-preview` | API version        |

### Model Recommendations

| API Type      | Recommended Models | Notes                     |
| ------------- | ------------------ | ------------------------- |
| Chat API      | `gpt-5`, `gpt-4o`  | Standard OpenAI models    |
| Responses API | `gpt-5-codex`      | Enhanced for tool calling |

## 🏥 Health Check

Check which API type is detected:

```bash
curl http://localhost:8000/health
```

Response includes:

```json
{
  "status": "healthy",
  "proxy_type": "integrated_azure_chat", // or "integrated_azure_responses"
  "timestamp": 1728297600.0
}
```

## 🐛 Troubleshooting

### Wrong API Detected

- **Issue**: Proxy routing to wrong API type
- **Solution**: Check `OPENAI_BASE_URL` contains correct pattern (`/chat` or `/responses`)

### Model Not Found

- **Issue**: Model name doesn't match deployment
- **Solution**:
  - Chat API: Use deployment name (e.g., `gpt-5`)
  - Responses API: Use `gpt-5-codex`

### Configuration Not Loading

- **Issue**: Environment variables not loaded
- **Solution**: Restart proxy after changing `.azure.env`

## 📝 Example Requests

### Chat API Request

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Responses API Request

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-codex",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 🔗 Real Examples

Based on your setup, here are the actual endpoints:

**Chat API**: https://ai-adapt-oai-eastus2.cognitiveservices.azure.com/openai/deployments/gpt-5/chat/completions?api-version=2025-01-01-preview

**Responses API**: https://ai-adapt-oai-eastus2.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview

---

## 🎯 Next Steps

1. Choose your API type based on your use case
2. Copy the appropriate example configuration
3. Replace placeholders with your Azure details
4. Test with the health check endpoint
5. Start making requests!

The URL-based detection system automatically handles routing, so you can focus on building your application.
