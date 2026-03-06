# Amplihack Proxy Configuration Guide

## Tool Calling Fix

**PROBLEM**: Tool calls were being described instead of executed due to
`AMPLIHACK_USE_LITELLM=true` routing through broken LiteLLM proxy.

**SOLUTION**: Set `AMPLIHACK_USE_LITELLM=false` to use the working Azure
streaming proxy.

## Available Configurations

### 1. Working Configuration (Tool Calling Enabled)

**File**: `.azure.env` OR `amplihack_litellm_proxy.env` (after fix)

- **Key Setting**: No `AMPLIHACK_USE_LITELLM` or `AMPLIHACK_USE_LITELLM=false`
- **Result**: Uses Azure streaming proxy with tool calling support
- **Status**: ✅ WORKS - Tools execute properly

### 2. Broken Configuration (Fixed)

**File**: `amplihack_litellm_proxy.env` (before fix)

- **Key Setting**: `AMPLIHACK_USE_LITELLM=true`
- **Result**: Routes through LiteLLM, breaks tool calling
- **Status**: ❌ BROKEN - Tools only described, not executed

## Usage Instructions

### Option A: Use .azure.env (Recommended)

```bash
# This configuration works out of the box
amplihack launch --with-proxy-config .azure.env
```

### Option B: Use Fixed amplihack_litellm_proxy.env

```bash
# This configuration now works after setting AMPLIHACK_USE_LITELLM=false
amplihack launch --with-proxy-config amplihack_litellm_proxy.env
```

## Verification

After starting the proxy, test that tool calling works:

1. Tool calls should execute (not just be described)
2. Only one proxy instance should be running
3. Port 9001 should be in use by the working proxy

## Key Difference

The critical difference is the `AMPLIHACK_USE_LITELLM` setting:

- `true` = Uses LiteLLM proxy (broken tool calling)
- `false` or unset = Uses Azure streaming proxy (working tool calling)
