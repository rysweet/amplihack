# Amplihack Hooks for GitHub Copilot CLI

This directory contains hook configurations and scripts for integrating amplihack with GitHub Copilot CLI.

## Overview

These hooks mirror the functionality of amplihack's Python hooks (`.claude/tools/amplihack/hooks/`) in a format compatible with GitHub Copilot CLI.

## Files

```
.github/hooks/
├── amplihack-hooks.json    # Hook configuration (JSON schema)
├── scripts/                # Bash hook implementations
│   ├── session-start.sh        # Session initialization
│   ├── session-end.sh          # Session cleanup and lock support
│   ├── user-prompt-submitted.sh # Prompt logging and preference injection
│   ├── pre-tool-use.sh         # Tool validation and safety policies
│   ├── post-tool-use.sh        # Tool usage metrics
│   └── error-occurred.sh       # Error tracking and logging
└── README.md              # This file
```

## Hook Types

### 1. sessionStart (session-start.sh)

**What it does:**
- Initializes session state directory structure
- Injects user preferences from `USER_PREFERENCES.md`
- Logs session startup metrics
- Provides project context to the conversation

**Key Features:**
- Pirate-themed output (matches USER_PREFERENCES.md)
- Full preference injection for MANDATORY enforcement
- Discovers and references DISCOVERIES.md if present
- Creates runtime directories for logs and metrics

### 2. sessionEnd (session-end.sh)

**What it does:**
- Checks for lock flag to enable continuous work mode
- Blocks session end if work is incomplete (lock active)
- Cleans up session resources
- Persists session state and metrics

**Key Features:**
- Lock flag support for autonomous operation
- Custom continuation prompts
- Lock invocation counter for metrics
- Fail-safe: Always allows stop if no lock

### 3. userPromptSubmitted (user-prompt-submitted.sh)

**What it does:**
- Logs user prompts for audit trail
- Injects user preferences on every message (REPL continuity)
- Extracts and tracks prompt metadata

**Key Features:**
- Audit log with truncated previews for long prompts
- Preference extraction using grep/sed
- Context length metrics
- Pirate-themed preference enforcement

### 4. preToolUse (pre-tool-use.sh)

**What it does:**
- Validates tool execution requests
- Enforces safety policies (blocks dangerous operations)
- Logs validation attempts

**Key Features:**
- Blocks `--no-verify` flags in git commands
- Provides clear user guidance on blocked operations
- Cannot be disabled programmatically
- Fail-safe: Allows all non-dangerous operations

### 5. postToolUse (post-tool-use.sh)

**What it does:**
- Logs tool execution results
- Collects tool usage metrics
- Categorizes tool types for analytics
- Tracks execution duration if available

**Key Features:**
- Tool categorization (Bash, file ops, search ops, agents)
- Error detection and logging
- Duration tracking
- High-level analytics

### 6. errorOccurred (error-occurred.sh)

**What it does:**
- Tracks and logs errors for debugging
- Categorizes error severity
- Collects error metrics for analysis
- Provides structured error information

**Key Features:**
- Error pattern categorization (timeout, permission, import, etc.)
- Structured error files in JSON format
- Severity tracking (warning, error, fatal)
- Immediate visibility via stderr

## Usage

### Installing Hooks

1. **Copy configuration to your project:**
   ```bash
   cp .github/hooks/amplihack-hooks.json ~/.config/copilot/hooks/
   ```

2. **Or use directly with CLI:**
   ```bash
   copilot cli --hooks .github/hooks/amplihack-hooks.json
   ```

3. **Or set as default:**
   ```bash
   # Add to ~/.config/copilot/config.json
   {
     "hooks": ".github/hooks/amplihack-hooks.json"
   }
   ```

### Testing Hooks

Test individual hooks manually:

```bash
# Test session-start hook
echo '{"prompt": "test"}' | bash .github/hooks/scripts/session-start.sh

# Test session-end hook with lock
touch .claude/runtime/locks/.lock_active
echo '{}' | bash .github/hooks/scripts/session-end.sh

# Test pre-tool-use validation
echo '{"toolUse":{"name":"Bash","input":{"command":"git commit --no-verify"}}}' | \
  bash .github/hooks/scripts/pre-tool-use.sh
```

### Environment Variables

Hooks respect these environment variables:

- `CLAUDE_PROJECT_DIR` - Project root directory (default: current directory)
- `CLAUDE_SESSION_ID` - Session identifier (default: timestamp)

### Lock Mode (Continuous Work)

Enable autonomous operation:

```bash
# Enable lock mode
mkdir -p .claude/runtime/locks
touch .claude/runtime/locks/.lock_active

# Optional: Set custom continuation prompt
echo "Continue with next steps, focusing on testing" > \
  .claude/runtime/locks/.continuation_prompt

# Disable lock mode
rm .claude/runtime/locks/.lock_active
```

## Generated Files

Hooks create these directories and files:

```
.claude/runtime/
├── logs/
│   └── {session_id}/
│       ├── session_start.log
│       ├── stop.log
│       ├── user_prompt_submit.log
│       ├── pre_tool_use.log
│       ├── post_tool_use.log
│       ├── error_occurred.log
│       ├── prompts_audit.jsonl
│       └── session_completed.txt
├── metrics/
│   ├── session_start_metrics.jsonl
│   ├── stop_metrics.jsonl
│   ├── user_prompt_submit_metrics.jsonl
│   ├── pre_tool_use_metrics.jsonl
│   ├── post_tool_use_metrics.jsonl
│   └── error_metrics.jsonl
└── errors/
    └── error_{timestamp}.json
```

## Converting Python Hooks to Bash

Use the hook converter to generate Bash scripts from Python hooks:

```bash
# Convert all hooks
python src/amplihack/adapters/hooks_converter.py \
  --source-dir .claude/tools/amplihack/hooks \
  --output-dir .github/hooks

# Verbose mode
python src/amplihack/adapters/hooks_converter.py -v
```

The converter:
- Extracts docstrings and logic patterns from Python
- Generates documented Bash scripts
- Creates JSON configuration
- Makes scripts executable

## Requirements

**Dependencies:**
- `bash` (4.0+)
- `jq` (for JSON parsing)
- Standard Unix tools: `date`, `grep`, `sed`, `cat`

**Install jq:**
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt install jq

# RHEL/Fedora
sudo dnf install jq
```

## Troubleshooting

### Hooks not executing

1. Check hook configuration path:
   ```bash
   copilot cli config show
   ```

2. Verify script permissions:
   ```bash
   ls -la .github/hooks/scripts/
   # All .sh files should be executable (755)
   ```

3. Test hooks manually (see "Testing Hooks" above)

### JSON parsing errors

Ensure `jq` is installed and scripts can read JSON from stdin:
```bash
echo '{"test": "value"}' | jq .
```

### Lock mode not working

Check lock flag exists and session-end.sh has correct permissions:
```bash
ls -la .claude/runtime/locks/.lock_active
ls -la .github/hooks/scripts/session-end.sh
```

## Philosophy Alignment

These hooks follow amplihack's core principles:

- **Ruthless Simplicity**: Bash scripts are direct and minimal
- **Zero-BS Implementation**: Every function works or doesn't exist
- **Fail-Safe Design**: Hooks never break the CLI chain
- **Observable Behavior**: Comprehensive logging and metrics
- **User Control**: Lock mode is explicit and controllable

## Comparison with Python Hooks

| Feature | Python Hooks | Bash Hooks |
|---------|-------------|------------|
| **Environment** | Claude Code | Copilot CLI |
| **Language** | Python 3.9+ | Bash 4.0+ |
| **Dependencies** | HookProcessor class | jq + Unix tools |
| **JSON Handling** | Native (json module) | jq |
| **State Management** | Files + runtime dirs | Files + runtime dirs |
| **Error Handling** | Exceptions + structured | Exit codes + logging |
| **Extensibility** | Class inheritance | Script composition |

Both implementations provide the same core functionality with equivalent behavior.

## Contributing

To add new hooks:

1. Create Python hook in `.claude/tools/amplihack/hooks/`
2. Run hook converter to generate Bash version
3. Customize Bash script as needed
4. Add tests
5. Update this README

## Related Documentation

- [Amplihack Hook System](.claude/tools/amplihack/hooks/README.md)
- [Hook Processor](src/amplihack/adapters/hooks_converter.py)
- [User Preferences](.claude/context/USER_PREFERENCES.md)
- [Default Workflow](.claude/workflow/DEFAULT_WORKFLOW.md)

## License

Same as amplihack project - see LICENSE file in project root.
