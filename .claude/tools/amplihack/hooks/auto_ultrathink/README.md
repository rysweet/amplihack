# Auto-UltraThink Hook

Intelligent automatic invocation of UltraThink for complex multi-step requests.

## Overview

The auto-ultrathink hook analyzes incoming user prompts and automatically invokes the `/ultrathink` command when it detects complex, multi-step tasks that would benefit from systematic workflow orchestration.

### Key Features

- **Intelligent Classification**: Pattern-based detection of complex tasks
- **User Preferences**: Configurable modes (enabled, ask, disabled)
- **Fail-Safe Design**: Never blocks user requests - defaults to pass-through
- **Comprehensive Logging**: JSONL-based logging for analysis and debugging
- **Confidence-Based Decisions**: Threshold-based triggering for reliability

## Architecture

The system consists of five main components:

```
User Prompt → Classifier → Decision Engine → Action Executor → Modified Prompt
                ↓              ↓                    ↓
           Preferences    Classification      Logging
```

### Components

1. **Request Classifier** (`request_classifier.py`)
   - Analyzes prompts to determine if UltraThink is needed
   - Pattern matching for multi-file features, refactoring, etc.
   - Confidence scoring (0.0 - 1.0)
   - Returns: `Classification(needs_ultrathink, confidence, reason, matched_patterns)`

2. **Preference Manager** (`preference_manager.py`)
   - Reads user preferences from `.claude/context/USER_PREFERENCES.md`
   - Supports three modes: `enabled`, `ask`, `disabled`
   - Configurable confidence threshold (default: 0.80)
   - Pattern-based exclusions for specific requests

3. **Decision Engine** (`decision_engine.py`)
   - Combines classification + preferences → decision
   - Three possible actions: `INVOKE`, `ASK`, `SKIP`
   - Applies confidence thresholds and exclusion rules
   - Always returns a valid decision (fail-safe)

4. **Action Executor** (`action_executor.py`)
   - Executes the decided action
   - `INVOKE`: Prepends `/ultrathink` to prompt
   - `ASK`: Injects confirmation question
   - `SKIP`: Returns original prompt unchanged
   - Handles edge cases (empty prompts, duplicates, etc.)

5. **Logger** (`logger.py`)
   - JSONL-format structured logging
   - Records all decisions and outcomes
   - Metrics computation for analysis
   - Stored in `.claude/runtime/logs/<session_id>/auto_ultrathink.jsonl`

## Usage

### Configuration

Add to `.claude/context/USER_PREFERENCES.md`:

```yaml
auto_ultrathink:
  mode: "ask"                    # enabled | ask | disabled
  confidence_threshold: 0.80     # 0.0 - 1.0
  excluded_patterns:             # Skip these patterns
    - "quick fix"
    - "simple.*change"
```

### Modes

- **`enabled`**: Automatically invoke UltraThink for high-confidence requests
- **`ask`**: Inject a confirmation question before invoking
- **`disabled`**: Never invoke automatically (manual `/ultrathink` only)

### Environment Variables

- `AMPLIHACK_PREFERENCES_PATH`: Override preferences file location (for testing)
- `AMPLIHACK_LOG_DIR`: Override log directory (for testing)

## Classification Patterns

The classifier detects these high-value patterns:

### Multi-File Features (confidence: 0.85)
- Authentication systems
- API implementations
- Database integrations
- Dashboard creation
- Payment processing

**Patterns:**
```python
"add.*authentication"
"implement.*api"
"create.*dashboard"
"build.*system"
```

### Refactoring (confidence: 0.80)
- Module restructuring
- Architecture redesign
- Code reorganization

**Patterns:**
```python
"refactor"
"redesign"
"restructure"
```

### Skip Patterns (confidence: 0.90+)
- Questions ("What is...", "How do I...")
- Slash commands (`/analyze`, `/fix`)
- Simple edits ("Change variable...", "Fix typo...")
- Read operations ("Show me...", "List all...")

## Decision Logic

The decision engine follows this flow:

```
1. Check if disabled → SKIP
2. Check if classification says not needed → SKIP
3. Check confidence below threshold → SKIP
4. Check excluded patterns → SKIP
5. Apply mode:
   - enabled → INVOKE
   - ask → ASK
   - disabled → SKIP (redundant but explicit)
```

## Logging Format

Each log entry is a JSON line in `.claude/runtime/logs/<session_id>/auto_ultrathink.jsonl`:

```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "session_id": "session_xyz",
  "prompt": "Add authentication to the API",
  "prompt_hash": "a1b2c3d4e5f6g7h8",
  "classification": {
    "needs_ultrathink": true,
    "confidence": 0.85,
    "reason": "Multi-file feature detected",
    "matched_patterns": ["add.*authentication", "api"]
  },
  "preference": {
    "mode": "ask",
    "confidence_threshold": 0.80,
    "excluded_patterns": []
  },
  "decision": {
    "action": "ask",
    "reason": "High confidence, ask mode: Multi-file feature..."
  },
  "result": {
    "action_taken": "ask",
    "modified": true,
    "user_choice": null
  },
  "execution_time_ms": 95.5,
  "version": "1.0"
}
```

## Metrics & Analysis

Get metrics summary:

```python
from logger import get_metrics_summary

# All sessions
metrics = get_metrics_summary()

# Specific session
metrics = get_metrics_summary(session_id="session_xyz")
```

Returns:

```python
{
  "total_entries": 100,
  "success_count": 98,
  "error_count": 2,
  "action_counts": {
    "skip": 70,
    "invoke": 20,
    "ask": 8
  },
  "confidence_stats": {
    "mean": 0.85,
    "median": 0.87,
    "min": 0.70,
    "max": 0.95
  },
  "execution_time_stats": {
    "mean": 100.5,
    "median": 95.0,
    "p95": 150.0,
    "max": 200.0
  },
  "error_breakdown": {
    "classification:ValueError": 1,
    "decision:TypeError": 1
  }
}
```

## Error Handling

The system is designed to **never fail**:

- All exceptions are caught and handled
- Errors log to stderr
- Default behavior: pass-through (SKIP)
- Logging failures are silent (print to stderr only)

## Testing

Run tests:

```bash
# All auto_ultrathink tests
pytest tests/auto_ultrathink/

# Unit tests only
pytest tests/auto_ultrathink/unit/

# Specific module
pytest tests/auto_ultrathink/unit/test_action_executor.py

# With coverage
pytest tests/auto_ultrathink/ --cov=auto_ultrathink --cov-report=html
```

### Test Structure

```
tests/auto_ultrathink/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_action_executor.py
│   ├── test_decision_engine.py
│   ├── test_logger.py
│   ├── test_preference_manager.py
│   └── test_request_classifier.py
├── integration/               # Integration tests
│   └── test_hook_integration.py
├── accuracy/                  # Classification accuracy tests
│   └── test_classification_accuracy.py
├── performance/               # Performance benchmarks
│   └── test_benchmarks.py
└── conftest.py               # Shared fixtures
```

## Performance

Target performance metrics:

- **Classification**: < 50ms per request
- **Decision Making**: < 10ms per request
- **Action Execution**: < 50ms per request
- **Logging**: < 50ms per entry
- **Total Pipeline**: < 150ms end-to-end

## Troubleshooting

### UltraThink not triggering when expected

1. Check preference mode is `enabled` or `ask`:
   ```bash
   grep -A 5 "auto_ultrathink:" .claude/context/USER_PREFERENCES.md
   ```

2. Check confidence threshold:
   ```python
   from request_classifier import classify_request
   result = classify_request("your prompt here")
   print(f"Confidence: {result.confidence}")
   ```

3. Check excluded patterns:
   ```python
   from preference_manager import get_auto_ultrathink_preference, is_excluded
   pref = get_auto_ultrathink_preference()
   print(f"Excluded: {is_excluded('your prompt', pref.excluded_patterns)}")
   ```

### UltraThink triggering too often

1. Increase confidence threshold to 0.90:
   ```yaml
   auto_ultrathink:
     confidence_threshold: 0.90
   ```

2. Add exclusion patterns:
   ```yaml
   auto_ultrathink:
     excluded_patterns:
       - "simple"
       - "quick"
       - "minor"
   ```

3. Switch to `ask` mode for confirmation:
   ```yaml
   auto_ultrathink:
     mode: "ask"
   ```

### Logs not being created

1. Check log directory exists:
   ```bash
   ls -la .claude/runtime/logs/
   ```

2. Check for permission errors:
   ```bash
   python -c "from logger import log_error; log_error('test', 'test', Exception('test'), 'test')" 2>&1
   ```

3. Set custom log directory (for testing):
   ```bash
   export AMPLIHACK_LOG_DIR=/tmp/auto_ultrathink_logs
   ```

## Architecture Decisions

### Why Pattern-Based Classification?

- **Simple & Fast**: No ML model overhead
- **Transparent**: Easy to understand and debug
- **Customizable**: Users can see and modify patterns
- **Reliable**: No training data or model drift issues

### Why JSONL Logging?

- **Append-Only**: No file locking issues
- **Line-Oriented**: Easy to stream and parse
- **Standard Format**: Works with existing log tools
- **Resilient**: Malformed lines don't corrupt entire file

### Why Three Modes?

- **`enabled`**: Power users who trust the system
- **`ask`**: Default for new users (safe, educational)
- **`disabled`**: Users who prefer manual control

### Why Fail-Safe Design?

The hook runs on **every user request**. A single failure would:
- Block user workflow
- Damage trust in the system
- Create support burden

Therefore: **Never fail, always pass through on errors.**

## Future Enhancements

Potential improvements (not currently implemented):

1. **ML-Based Classification**
   - Train on logged decisions + outcomes
   - Improve accuracy over time
   - User-specific models

2. **Context-Aware Decisions**
   - Consider conversation history
   - Detect multi-turn complex tasks
   - Remember user corrections

3. **Adaptive Thresholds**
   - Learn optimal threshold per user
   - Adjust based on feedback
   - Per-pattern thresholds

4. **Rich Metrics Dashboard**
   - Web UI for log analysis
   - Accuracy tracking over time
   - Pattern performance breakdown

## Contributing

When modifying the auto-ultrathink system:

1. **Maintain fail-safe behavior**: Never raise exceptions that block users
2. **Preserve backward compatibility**: Log format is an API
3. **Add tests**: Unit tests for all new patterns
4. **Update documentation**: Keep README in sync with code
5. **Measure performance**: Ensure changes don't slow pipeline

## Related Files

- `.claude/context/USER_PREFERENCES.md` - User configuration
- `.claude/runtime/logs/<session_id>/auto_ultrathink.jsonl` - Decision logs
- `.claude/workflow/DEFAULT_WORKFLOW.md` - UltraThink workflow definition
- `.claude/commands/amplihack/ultrathink.md` - UltraThink command implementation

## License

Part of the amplihack framework - see root LICENSE file.
