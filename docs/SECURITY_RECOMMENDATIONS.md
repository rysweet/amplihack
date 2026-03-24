# Security Recommendations for Amplihack

## Critical Security Issues

### 1. API Key Exposure (HIGH PRIORITY)

**Issue**: Hard-coded API keys in configuration files

**Solution**:

```bash
# Use environment variables only — never hard-code keys in files
export ANTHROPIC_API_KEY="your_key_here"  # pragma: allowlist secret
export OPENAI_API_KEY="your_key_here"  # pragma: allowlist secret
```

### 2. Tool Calling Configuration

**Current Secure Settings**:

- `ENFORCE_ONE_TOOL_CALL_PER_RESPONSE=true`
- `AMPLIHACK_TOOL_RETRY_ATTEMPTS=3`
- Tool validation enabled

**Recommended Adjustments for Functionality**:

```bash
# Allow multiple tool calls for complex workflows
export ENFORCE_ONE_TOOL_CALL_PER_RESPONSE=false

# Increase retry attempts for reliability
export AMPLIHACK_TOOL_RETRY_ATTEMPTS=5

# Enable tool fallback for robustness
export ENABLE_TOOL_FALLBACK=true
```

### 3. Supply Chain Security

**litellm Removal**: The `litellm` dependency was removed due to a PyPI supply chain attack (see commit `ead2a7cb0`). Any functionality that previously depended on litellm has been removed or replaced with direct API integrations.

### 4. Enhanced File Logging Security

**Current Security** (Already Excellent):

- Localhost-only binding
- Credential sanitization
- Connection limits
- Proper file permissions

**Additional Recommendations**:

- Add audit logging for tool executions
- Implement rate limiting per IP
- Add request signature validation

## Implementation Priority

1. **IMMEDIATE**: Fix API key exposure
2. **HIGH**: Adjust tool calling limits for functionality
3. **MEDIUM**: Review dependencies for supply chain risks
4. **LOW**: Enhanced audit logging

## Security Compliance Status

- **COMPLIANT**: Log streaming security
- **COMPLIANT**: Tool calling error handling
- **COMPLIANT**: Localhost binding
- **NEEDS FIX**: API key management
- **NEEDS TUNING**: Tool execution limits
