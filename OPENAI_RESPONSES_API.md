# OpenAI Responses API Implementation

## Overview

This document describes the implementation of OpenAI Responses API support in the claude-code-proxy integration for Azure OpenAI services.

## Background

The original PR was intended to support the new OpenAI Responses API (https://platform.openai.com/docs/guides/migrate-to-responses) instead of the traditional Chat Completions API. The Responses API provides a different request/response format optimized for structured conversations.

## Implementation Details

### Request Format

The Responses API uses a simplified request format:

```json
{
  "model": "gpt-5-codex",
  "input": "tell me what agents and commands you have available to you"
}
```

### Response Format

The API returns responses in the OpenAI Responses format:

```json
{
  "id": "resp_...",
  "object": "response",
  "created_at": 1759611575,
  "status": "completed",
  "model": "gpt-5-codex",
  "output": [
    {
      "id": "msg_...",
      "type": "message",
      "status": "completed",
      "content": [...],
      "role": "assistant"
    }
  ],
  "usage": {
    "input_tokens": 17,
    "output_tokens": 58,
    "total_tokens": 75
  }
}
```

## Changes Made

### 1. FastAPI Endpoint Addition

Added a new `/openai/responses` endpoint to the claude-code-proxy FastAPI server:

- **File**: `server/fastapi.py` (in cached claude-code-proxy instances)
- **Endpoint**: `POST /openai/responses`
- **Request Model**: `OpenAIResponsesRequest` with `model` and `input` fields
- **Integration**: Uses LiteLLM for Azure OpenAI backend processing

### 2. JSON Serialization Fix

Fixed a critical bug in error handling that was causing "Internal Server Error" responses:

- **Issue**: TypeError when serializing Response objects in error details
- **Fix**: Added JSON serializability checking with fallback to string conversion
- **Impact**: Proper error responses instead of crashes

### 3. Enhanced Logging

Improved proxy startup logging to show log file locations like other Claude Code components.

## Testing

### Automated Tests

Created `tests/test_openai_responses_api.py` with:

- Endpoint existence validation
- Response format validation
- Integration test framework

### Manual Testing

Verified working with curl:

```bash
curl -X POST http://localhost:8082/openai/responses \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-codex", "input": "tell me what agents you have available"}'
```

### Azure Integration

Tested with real Azure OpenAI configuration:

- **Endpoint**: `ai-adapt-oai-eastus2.openai.azure.com`
- **Model**: `gpt-5-codex`
- **API Version**: `2025-04-01-preview`

## Current Status

✅ **WORKING**: OpenAI Responses API endpoint implemented and tested
✅ **WORKING**: JSON serialization crashes fixed
✅ **WORKING**: Azure OpenAI integration with correct model mappings
✅ **WORKING**: Enhanced logging and error reporting

## Architecture Notes

The claude-code-proxy is an external dependency installed via UVX. The implementation modifies the cached UVX instances to provide the Responses API support. For production deployment, these changes would need to be:

1. Submitted upstream to claude-code-proxy project, OR
2. Maintained as a fork with custom changes, OR
3. Integrated directly into the amplihack proxy management system

## Dependencies

- `uvx` for claude-code-proxy installation
- `litellm` for Azure OpenAI backend
- `fastapi` for endpoint handling
- `httpx` for async HTTP client functionality

## Configuration

Uses standard Azure OpenAI environment variables:

- `OPENAI_API_KEY` / `AZURE_OPENAI_KEY`
- `OPENAI_BASE_URL` with Responses API endpoint
- `AZURE_API_VERSION`
- Model mappings (`BIG_MODEL`, `MIDDLE_MODEL`, `SMALL_MODEL`)

The implementation automatically detects Responses API endpoints and uses the appropriate request/response format.
