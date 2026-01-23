# Neo4j Session Cleanup Feature

## Overview

The Neo4j Session Cleanup feature provides intelligent, user-friendly management of Neo4j database shutdown when exiting Amplihack sessions. It automatically detects when you're the last active connection and offers to gracefully shut down the Neo4j container, preventing resource waste while maintaining data safety.

**Key Benefits:**

- **Resource Efficiency**: Automatically stops unused Neo4j containers
- **Zero Disruption**: Never prompts if other sessions are connected
- **User Control**: Configurable preferences for always/never/ask behavior
- **Safe by Default**: Conservative error handling protects your data
- **Non-Intrusive**: 10-second timeout with sensible defaults

## How It Works

### Architecture

The feature consists of three main components:

1. **Connection Tracker** (`connection_tracker.py`)
   - Queries Neo4j HTTP API to count active connections
   - Uses `dbms.listConnections()` procedure
   - Handles timeouts and connection errors gracefully
   - Returns connection count or `None` if unable to determine

2. **Shutdown Coordinator** (`shutdown_coordinator.py`)
   - Loads user preferences from `USER_PREFERENCES.md`
   - Evaluates whether to prompt based on connection count and preferences
   - Presents timed prompt (10 seconds) with preference-saving options
   - Executes shutdown via container manager if approved

3. **Exit Hook** (registered at startup)
   - Registered as Python `atexit` handler
   - Invoked automatically when Amplihack session ends
   - Coordinates the full cleanup flow
   - Never raises exceptions (fail-safe design)

### Decision Flow

```
Session Exit
    ↓
Is auto mode enabled? → YES → Skip (no prompts in auto mode)
    ↓ NO
Preference = 'never'? → YES → Skip (user preference)
    ↓ NO
Check connection count
    ↓
Multiple connections? → YES → Skip (safe default - don't disrupt others)
    ↓ NO
Last connection detected
    ↓
Preference = 'always'? → YES → Shutdown without prompt
    ↓ NO
Prompt user (10s timeout)
    ↓
User responds:
  - 'y' / 'yes' → Shutdown (one-time)
  - 'a' / 'always' → Save preference + Shutdown
  - 'v' / 'never' → Save preference + Skip
  - 'n' / 'no' / timeout → Skip
    ↓
Execute shutdown (if approved)
```

## User Guide

### Preferences

The feature respects your preferences stored in `~/.amplihack/.claude/context/USER_PREFERENCES.md`:

**Available Values:**

- **`ask`** (default): Prompt when you're the last connection
- **`always`**: Automatically shutdown without prompting
- **`never`**: Never prompt or shutdown

**Preference Locations (checked in order):**

1. Project-local: `~/.amplihack/.claude/context/USER_PREFERENCES.md` (in current directory)
2. Home directory: `~/.claude/context/USER_PREFERENCES.md`

**Setting Preferences:**

**Option 1: Interactive Prompt**

When prompted for shutdown, use these responses to save preferences:

```
Neo4j database is running. Shutdown now? (y/n/Always/Never):
  a or always → Saves 'always' preference and shuts down
  v or never  → Saves 'never' preference and skips shutdown
  y or yes    → Shuts down this time only (doesn't save preference)
  n or no     → Skips shutdown this time only
  <timeout>   → Defaults to 'no' after 10 seconds
```

**Option 2: Manual Edit**

Edit `~/.amplihack/.claude/context/USER_PREFERENCES.md` and add:

```markdown
### neo4j_auto_shutdown

**Current setting:** always

Options: always, never, ask (default)
```

**Option 3: Use /amplihack:customize Command**

```bash
/amplihack:customize set neo4j_auto_shutdown always
/amplihack:customize set neo4j_auto_shutdown never
/amplihack:customize set neo4j_auto_shutdown ask
```

### Prompt Behavior

When prompted for shutdown:

```
Neo4j database is running. Shutdown now? (y/n/Always/Never):
```

**Timeout Handling:**

- Prompt times out after **10 seconds**
- Default behavior: **No shutdown** (safe default)
- Helpful tip displayed suggesting preference options

**User-Friendly Messages:**

- Clear indication of why prompt appeared
- Guidance on preference options
- File locations shown if preference saving fails
- Docker commands suggested when connection issues occur

### Logging

The feature provides comprehensive logging at multiple levels:

**INFO Level** (visible by default):

- Preference loaded (value and source)
- Auto mode skip notifications
- Multiple connection detections (with count)
- Shutdown decision outcomes
- Shutdown completion status

**DEBUG Level** (enable with `--log-level DEBUG`):

- Connection tracking attempts
- Preference file paths checked
- Decision logic flow at each step
- Detailed query operations

**WARNING Level** (always visible):

- Connection errors with troubleshooting hints
- Preference file issues with remediation steps
- Shutdown failures with context

## Configuration Options

### Environment Variables

The connection tracker supports configuration via environment variables:

```bash
# Neo4j authentication credentials (PRODUCTION)
export NEO4J_USERNAME="neo4j"      # Default: "neo4j"
export NEO4J_PASSWORD="your-secure-password-here"  # REQUIRED in production

# Development mode (TESTING ONLY - NOT FOR PRODUCTION)
export NEO4J_ALLOW_DEFAULT_PASSWORD="true"  # Allows default "amplihack" password
```

#### Security Best Practices

**PRODUCTION ENVIRONMENTS:**

1. **Always set NEO4J_PASSWORD**: Never use the default "amplihack" password in production
2. **Use strong passwords**: Minimum 16 characters with mixed case, numbers, and symbols
3. **Rotate credentials**: Change passwords regularly
4. **Secure storage**: Use environment variable management tools (e.g., AWS Secrets Manager, HashiCorp Vault)

**DEVELOPMENT MODE:**

The connection tracker requires explicit opt-in to use the default password:

```bash
# This will FAIL without NEO4J_PASSWORD or development mode
python -m amplihack

# ERROR: Neo4j password required. Set NEO4J_PASSWORD environment variable.
# For development/testing only, set NEO4J_ALLOW_DEFAULT_PASSWORD=true

# Development mode (testing only)
export NEO4J_ALLOW_DEFAULT_PASSWORD="true"
python -m amplihack  # Uses "amplihack" password with warning
```

**Why This Matters:**

- Prevents accidental use of default credentials in production
- Forces explicit acknowledgment for development usage
- Provides clear warning messages when default password is used
- Aligns with security best practices for credential management

### Container Settings

Default connection settings (can be customized in code):

```python
Neo4jConnectionTracker(
    container_name="neo4j-amplihack",  # For logging/diagnostics
    timeout=2.0,                        # HTTP request timeout (seconds)
    username=None,                      # Uses NEO4J_USERNAME env or "neo4j"
    password=None                       # Uses NEO4J_PASSWORD env or "amplihack"
)
```

### Retry Logic and Resilience

The connection tracker implements intelligent retry logic for transient network issues:

**Retry Behavior:**

- **Timeout errors**: Retry with exponential backoff
- **Connection errors**: No retry (container not running)
- **Generic errors**: No retry (unexpected conditions)
- **Max retries**: 2 (total 3 attempts including initial)

**Exponential Backoff:**

```
Attempt 1: Immediate (0s delay)
Attempt 2: 0.5s delay
Attempt 3: 0.75s delay
```

Formula: `backoff = 0.5 * (1.5 ** attempt)`

**Why This Design:**

- **Timeout retries**: Network hiccups or Neo4j briefly overloaded
- **No connection retry**: Container not running = permanent failure
- **Exponential backoff**: Prevents overwhelming a recovering service
- **Short delays**: Minimal impact on session exit time (< 2 seconds total)

**Example Scenario:**

```
# Neo4j temporarily overloaded
Attempt 1: Timeout after 4.0s → Retry in 0.5s
Attempt 2: Timeout after 4.0s → Retry in 0.75s
Attempt 3: Success → Returns connection count

Total time: ~9.25s (3 × 4.0s + 0.5s + 0.75s)
```

### Timeouts

The feature uses carefully tuned timeouts for optimal UX:

| Operation          | Timeout | Purpose                               |
| ------------------ | ------- | ------------------------------------- |
| HTTP request       | 4.0s    | Connection count query (per attempt)  |
| User prompt        | 10.0s   | Enough time to read and respond       |
| Shutdown execution | 30.0s   | Container stop operation (via docker) |

**Note**: HTTP timeout is per attempt. With 3 attempts and backoff, total worst-case connection check time is ~9.25 seconds.

### Path Validation Security

The shutdown coordinator implements strict path validation to prevent path traversal attacks:

**Validation Rules:**

1. **File name check**: Must be named `USER_PREFERENCES.md` exactly
2. **Directory check**: Path must contain `~/.amplihack/.claude/context`
3. **Absolute path**: Resolved to canonical absolute path
4. **No symlink exploitation**: Uses `Path.resolve()` to follow symlinks safely

**Protected Against:**

```bash
# These attacks are automatically rejected:
../../../etc/passwd                          # Traversal to system files
/tmp/USER_PREFERENCES.md                     # Invalid directory
.claude/context/../../../etc/USER_PREFERENCES.md  # Complex traversal
```

**Allowed Paths:**

```bash
# Project-local (preferred)
/path/to/project/.claude/context/USER_PREFERENCES.md

# Home directory (fallback)
~/.claude/context/USER_PREFERENCES.md
```

**Why This Matters:**

- Prevents reading/writing arbitrary files on the system
- Protects against malicious preference file injection
- Ensures preferences are always stored in expected locations
- Maintains security even if path construction has vulnerabilities

### Exception Sanitization

The connection tracker sanitizes all exception messages before logging to prevent information disclosure:

**Sanitization Process:**

1. **Newline removal**: Replaces `\n` and `\r` with escaped versions
2. **Truncation**: Limits message length to 100 characters
3. **Dual logging**: Detailed at DEBUG level, generic at WARNING level

**Example:**

```python
# Original exception
raise ValueError("Database error: password='secret123'\nConnection failed")

# DEBUG log (detailed)
"Detailed error: ValueError: Database error: password='secret123'\\nConnection failed"

# WARNING log (generic)
"Failed to query Neo4j connection count. Check if container is running."
```

**Why This Matters:**

- Prevents password/credential leakage in logs
- Stops log injection attacks (newlines breaking log parsers)
- Reduces log bloat from verbose error messages
- Provides diagnostics at DEBUG level without risking production exposure

## Troubleshooting

### Common Issues

**Issue: "Cannot connect to Neo4j HTTP API"**

**Cause:** Neo4j container is not running or HTTP API is unavailable

**Solution:**

```bash
# Check if container is running
docker ps | grep neo4j-amplihack

# If not running, start it
docker start neo4j-amplihack

# Verify HTTP API is accessible
curl -u neo4j:amplihack http://localhost:7474/db/data/
```

**Issue: "Timeout querying Neo4j connection count"**

**Cause:** Neo4j is running but responding slowly (overloaded or starting up)

**Solution:**

```bash
# Check container status
docker ps | grep neo4j-amplihack

# Check Neo4j logs for issues
docker logs neo4j-amplihack

# Wait for Neo4j to fully start (can take 10-30 seconds)
```

**Issue: "Cannot save preference - USER_PREFERENCES.md not found"**

**Cause:** Preference file doesn't exist in project or home directory

**Solution:**

```bash
# Option 1: Create project-local preferences
mkdir -p .claude/context
touch .claude/context/USER_PREFERENCES.md

# Option 2: Use customize command
/amplihack:customize set neo4j_auto_shutdown always

# Option 3: Manually create with content
cat > .claude/context/USER_PREFERENCES.md << 'EOF'
# User Preferences

### neo4j_auto_shutdown

**Current setting:** ask

Options: always, never, ask (default)
EOF
```

**Issue: "Multiple connections detected - skipping prompt"**

**Cause:** Other Amplihack sessions or Neo4j clients are connected

**Not an error:** This is intentional safe behavior to avoid disrupting other users

**To verify:**

```bash
# Check all processes using Neo4j
lsof -i :7474 -i :7687

# Or use Neo4j browser to see connections
# Open: http://localhost:7474
# Run: CALL dbms.listConnections()
```

### Debug Mode

For detailed troubleshooting, enable debug logging:

```bash
# Enable debug logging
amplihack --log-level DEBUG

# Or set environment variable
export AMPLIHACK_LOG_LEVEL=DEBUG
amplihack
```

Debug logs include:

- Connection tracker HTTP operations
- Preference file resolution paths
- Decision logic evaluation steps
- Thread operations for prompt timeout
- Container manager interactions

### Known Limitations

1. **Auto Mode Bypass**: Feature is completely skipped in auto mode (by design)
2. **HTTP API Dependency**: Requires Neo4j HTTP API at `http://localhost:7474`
3. **Docker Dependency**: Shutdown uses Docker CLI commands
4. **Single Container**: Assumes single Neo4j container named `neo4j-amplihack`
5. **Project-Local Priority**: Project preferences override home directory

## Examples

### Example 1: First-Time User (Default Behavior)

```
# User exits Amplihack session
# Neo4j has 1 active connection (this session)
# No preference set (defaults to 'ask')

Output:
Neo4j database is running. Shutdown now? (y/n/Always/Never): y
Neo4j database stopped successfully
```

### Example 2: Setting "Always" Preference

```
# User exits Amplihack session
# Wants to always shutdown automatically

Prompt:
Neo4j database is running. Shutdown now? (y/n/Always/Never): always

Output:
Neo4j database stopped successfully

# Future sessions automatically shutdown without prompting
```

### Example 3: Multiple Sessions Running

```
# User exits Amplihack session
# Neo4j has 3 active connections
# Feature detects other connections

Output:
# No prompt shown - safe default behavior
# Neo4j continues running for other sessions
```

### Example 4: Auto Mode

```
# User runs Amplihack in auto mode
amplihack --auto

# Feature is completely disabled
# No prompts, no shutdowns
# Neo4j lifecycle managed externally
```

### Example 5: Timeout Scenario

```
# User exits Amplihack session
# Gets distracted, doesn't respond to prompt

Prompt:
Neo4j database is running. Shutdown now? (y/n/Always/Never):
# ... 10 seconds pass ...

Output:
(timeout after 10 seconds - defaulting to no shutdown)
Tip: Set preference with 'always' or 'never' to avoid future prompts
```

### Example 6: Preference Set to "Never"

```
# USER_PREFERENCES.md contains:
# neo4j_auto_shutdown: never

# User exits Amplihack session
# No prompt shown, Neo4j continues running
# Logs show: "neo4j_auto_shutdown=never - skipping shutdown prompt"
```

## Performance Characteristics

### HTTP Calls

**Optimized for minimal overhead:**

- **Maximum 1 HTTP call** per session exit
- **Only when needed**: Skipped if auto mode or preference='never'
- **Fast query**: `dbms.listConnections()` is a lightweight operation
- **Short timeout**: 2-second timeout prevents blocking

### Timeouts

**Carefully tuned for user experience:**

| Phase            | Timeout | Impact                                          |
| ---------------- | ------- | ----------------------------------------------- |
| Connection check | 2s      | Non-blocking, fails fast                        |
| User prompt      | 10s     | Comfortable response time                       |
| Container stop   | 30s     | Docker operation (handled by container manager) |

**Total worst-case delay:** ~12 seconds (2s + 10s) before session exit completes

### Blocking Operations

**None in critical path:**

- Connection check runs synchronously but with short timeout
- User prompt uses background thread (non-blocking main thread)
- Shutdown executes only after user approval

### Early Returns

**Optimized common paths:**

1. **Auto mode**: Returns immediately (no operations)
2. **Preference='never'**: Returns after preference check (no connection query)
3. **Multiple connections**: Returns after connection check (no prompt)
4. **User declines**: Returns immediately (no shutdown)

**Performance by scenario:**

```
Auto mode:           <1ms   (immediate return)
Preference='never':  <10ms  (file read only)
Multiple connections: ~50ms  (HTTP query + return)
Last connection:     10s+   (user prompt time)
```

## Integration Points

### Startup Registration

The exit hook is registered during Amplihack initialization:

```python
# In startup code
from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator
from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager

# Initialize components
tracker = Neo4jConnectionTracker()
manager = Neo4jContainerManager()
coordinator = Neo4jShutdownCoordinator(
    connection_tracker=tracker,
    container_manager=manager,
    auto_mode=config.auto_mode
)

# Register exit handler
import atexit
atexit.register(coordinator.handle_session_exit)
```

### Testing Integration

For testing, the feature supports dependency injection:

```python
# Test with mock components
from unittest.mock import Mock

mock_tracker = Mock(spec=Neo4jConnectionTracker)
mock_manager = Mock(spec=Neo4jContainerManager)

coordinator = Neo4jShutdownCoordinator(
    connection_tracker=mock_tracker,
    container_manager=mock_manager,
    auto_mode=False
)
```

## Related Documentation

- **Implementation Details**: See module docstrings in `connection_tracker.py` and `shutdown_coordinator.py`
- **Test Coverage**: See `tests/unit/neo4j/` for comprehensive unit tests
- **Container Management**: See `amplihack.memory.neo4j.lifecycle` module
- **User Preferences**: See `~/.amplihack/.claude/context/USER_PREFERENCES.md` documentation

## Support

For issues or questions:

1. Check troubleshooting section above
2. Enable debug logging for detailed diagnostics
3. Review logs in `~/.amplihack/.claude/runtime/logs/`
4. Report issues with log excerpts and reproduction steps

---

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: 2025-11-08
