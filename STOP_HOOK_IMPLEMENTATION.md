# Azure OpenAI Continuation STOP Hook Implementation

## Overview

Successfully implemented a STOP hook that prevents premature stopping when using
Claude Code with Azure OpenAI models through the proxy. The hook uses
DecisionControl to override stop decisions when work remains to be done.

## Implementation Details

### Files Created

1. **`.claude/tools/amplihack/hooks/stop_azure_continuation.py`**
   - Main hook implementation
   - Auto-activates when Azure OpenAI proxy is detected
   - Uses DecisionControl to continue when needed
   - Comprehensive error handling with logging

2. **`.claude/tools/amplihack/hooks/test_stop_azure_continuation.py`**
   - Complete test suite with 8 test cases
   - All tests passing
   - Tests proxy detection, TODO tracking, continuation phrases, and error
     handling

3. **`.claude/tools/amplihack/hooks/demo_azure_continuation.py`**
   - Interactive demonstration of the hook
   - Shows behavior with and without proxy

4. **`.claude/tools/amplihack/hooks/README.md`**
   - Documentation for all hooks in the directory
   - Installation and usage instructions

## Key Features

### Proxy Detection

The hook automatically activates when it detects:

- `ANTHROPIC_BASE_URL` set to localhost (proxy active)
- `CLAUDE_CODE_PROXY_LAUNCHER` environment variable
- `AZURE_OPENAI_KEY` in environment
- Azure OpenAI URL in `OPENAI_BASE_URL`

### Continuation Logic

The hook continues work if ANY of these conditions are true:

1. **Uncompleted TODOs**: Pending or in-progress items in TodoWrite
2. **Continuation Phrases**: Assistant mentions "next", "let me", "now I'll",
   etc.
3. **Unfulfilled Requests**: Multi-part user requests appear incomplete

### Error Handling

- All errors are logged to `.claude/runtime/logs/stop_azure_continuation.log`
- On any error, defaults to allowing stop (non-intrusive)
- Never disrupts normal Claude Code operation

## Testing

Run the test suite:

```bash
python3 .claude/tools/amplihack/hooks/test_stop_azure_continuation.py
```

Results: **8/8 tests passing** ✓

Run the demo:

```bash
python3 .claude/tools/amplihack/hooks/demo_azure_continuation.py
```

## Integration

The hook integrates seamlessly with the existing Claude Code hook system:

- Placed in `.claude/tools/amplihack/hooks/` directory
- Made executable with appropriate permissions
- Follows Claude Code hook conventions
- Works alongside existing hooks (stop.py, session_start.py, post_tool_use.py)

## Usage

When using `amplihack launch --with-proxy-config`:

1. The proxy starts and sets environment variables
2. Claude Code launches with proxy configuration
3. The hook automatically activates
4. Prevents premature stops when work remains
5. Allows normal stops when all work is complete

## Verification

The hook has been verified to:

- ✓ Only activate when using Azure OpenAI proxy
- ✓ Correctly detect uncompleted TODO items
- ✓ Identify continuation phrases in assistant messages
- ✓ Recognize multi-part user requests
- ✓ Handle errors gracefully without disruption
- ✓ Log activity for debugging
- ✓ Work with existing Claude Code infrastructure

## Notes

- The hook is non-intrusive and will not affect normal Claude Code operation
- It only activates when the Azure OpenAI proxy is detected
- All decisions are logged for transparency and debugging
- The implementation follows Claude Code's DecisionControl specification for
  STOP hooks
