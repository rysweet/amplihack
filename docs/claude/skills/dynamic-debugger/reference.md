# Dynamic Debugger API Reference

Complete API reference fer all debugging commands, language configurations, and error handling.

## Debugging Commands Reference

### Breakpoint Management

#### Set Breakpoint

**Syntax:**
```
Set breakpoint at <location>
<location> = "line <number>" | "function <name>" | "file:line"
```

**Examples:**
```
Set breakpoint at line 42
Set breakpoint at function calculate_total
Set breakpoint at src/main.py:156
```

**API Call (MCP):**
```json
{
  "tool": "dap_set_breakpoints",
  "arguments": {
    "source": {"path": "/path/to/file.py"},
    "breakpoints": [{"line": 42}]
  }
}
```

**Response:**
```json
{
  "breakpoints": [
    {"id": 1, "verified": true, "line": 42, "source": {"path": "/path/to/file.py"}}
  ]
}
```

#### Remove Breakpoint

**Syntax:**
```
Remove breakpoint at <location>
Clear all breakpoints
```

**Examples:**
```
Remove breakpoint at line 42
Clear all breakpoints
```

**API Call:**
```json
{
  "tool": "dap_set_breakpoints",
  "arguments": {
    "source": {"path": "/path/to/file.py"},
    "breakpoints": []
  }
}
```

#### List Breakpoints

**Syntax:** `List breakpoints` or `Show all breakpoints`

**API Call:**
```json
{
  "tool": "dap_list_breakpoints"
}
```

**Response:**
```json
{
  "breakpoints": [
    {"id": 1, "line": 42, "file": "main.py", "verified": true},
    {"id": 2, "line": 156, "file": "utils.py", "verified": true}
  ]
}
```

### Execution Control

#### Continue

**Syntax:** `Continue` or `Resume execution`

**API Call:**
```json
{
  "tool": "dap_continue",
  "arguments": {"threadId": 1}
}
```

**Effect:** Runs until next breakpoint or program termination

#### Step Over

**Syntax:** `Step over` or `Next`

**API Call:**
```json
{
  "tool": "dap_next",
  "arguments": {"threadId": 1}
}
```

**Effect:** Executes current line without entering function calls

#### Step Into

**Syntax:** `Step into` or `Step in`

**API Call:**
```json
{
  "tool": "dap_step_in",
  "arguments": {"threadId": 1}
}
```

**Effect:** Enters function call on current line

#### Step Out

**Syntax:** `Step out` or `Finish`

**API Call:**
```json
{
  "tool": "dap_step_out",
  "arguments": {"threadId": 1}
}
```

**Effect:** Executes until current function returns

### Variable Inspection

#### Inspect Variable

**Syntax:**
```
What's the value of <variable>?
Show <variable>
Inspect <variable>
```

**Examples:**
```
What's the value of userId?
Show request.headers
Inspect self.config
```

**API Call:**
```json
{
  "tool": "dap_evaluate",
  "arguments": {
    "expression": "userId",
    "frameId": 0,
    "context": "watch"
  }
}
```

**Response:**
```json
{
  "result": "12345",
  "type": "int",
  "variablesReference": 0
}
```

#### Show All Variables

**Syntax:** `Show all variables` or `List local variables`

**API Call:**
```json
{
  "tool": "dap_scopes",
  "arguments": {"frameId": 0}
}
```

**Response:**
```json
{
  "scopes": [
    {
      "name": "Locals",
      "variablesReference": 1,
      "expensive": false
    }
  ]
}
```

#### Evaluate Expression

**Syntax:**
```
Evaluate: <expression>
What's <expression>?
```

**Examples:**
```
Evaluate: x + y
What's len(users)?
Evaluate: request.method == "POST"
```

**API Call:**
```json
{
  "tool": "dap_evaluate",
  "arguments": {
    "expression": "x + y",
    "frameId": 0,
    "context": "repl"
  }
}
```

### Call Stack Inspection

#### Show Call Stack

**Syntax:** `Show call stack` or `Where am I?` or `Stack trace`

**API Call:**
```json
{
  "tool": "dap_stack_trace",
  "arguments": {"threadId": 1}
}
```

**Response:**
```json
{
  "stackFrames": [
    {"id": 0, "name": "calculate_total", "line": 42, "source": {"path": "main.py"}},
    {"id": 1, "name": "process_order", "line": 156, "source": {"path": "orders.py"}},
    {"id": 2, "name": "main", "line": 10, "source": {"path": "app.py"}}
  ]
}
```

### Session Control

#### Start Session

**Syntax:** `Debug this` or `Start debugging`

**Automatic:** Session starts when debugging intent detected

**API Sequence:**
1. `dap_initialize` - Initialize DAP connection
2. `dap_launch` or `dap_attach` - Start/attach to process
3. `dap_configuration_done` - Mark configuration complete

#### Stop Session

**Syntax:** `Stop debugging` or `End session`

**API Call:**
```json
{
  "tool": "dap_disconnect",
  "arguments": {"terminateDebuggee": true}
}
```

**Automatic cleanup:** Triggers on timeout or error

## Language-Specific Configuration

### Python (debugpy)

**Configuration:**
```json
{
  "language": "python",
  "debugger": "debugpy",
  "default_port": 5678,
  "attach_timeout": 10,
  "file_extensions": [".py"],
  "manifest_files": ["requirements.txt", "pyproject.toml", "setup.py", "poetry.lock"],
  "launch_config": {
    "type": "python",
    "request": "launch",
    "program": "${file}",
    "console": "integratedTerminal",
    "justMyCode": false
  }
}
```

**Special Features:**
- Async/await debugging
- Multiple interpreter support
- Virtual environment detection
- Django/Flask support

**Common Issues:**
- **Issue:** "debugpy not found"
- **Fix:** `pip install debugpy`

### JavaScript/TypeScript (Node)

**Configuration:**
```json
{
  "language": "javascript",
  "debugger": "node",
  "default_port": 9229,
  "attach_timeout": 10,
  "file_extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"],
  "manifest_files": ["package.json", "tsconfig.json"],
  "launch_config": {
    "type": "node",
    "request": "launch",
    "program": "${file}",
    "skipFiles": ["<node_internals>/**"],
    "sourceMaps": true
  }
}
```

**Special Features:**
- Promise/async debugging
- Source map support (TypeScript)
- Worker thread debugging
- Browser debugging (Chrome DevTools Protocol)

**Common Issues:**
- **Issue:** "Cannot find module"
- **Fix:** Ensure `NODE_PATH` includes node_modules

### C/C++ (GDB)

**Configuration:**
```json
{
  "language": "cpp",
  "debugger": "gdb",
  "default_port": null,
  "attach_timeout": 15,
  "file_extensions": [".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"],
  "manifest_files": ["CMakeLists.txt", "Makefile", "configure.ac"],
  "launch_config": {
    "type": "cppdbg",
    "request": "launch",
    "program": "${fileDirname}/${fileBasenameNoExtension}",
    "MIMode": "gdb",
    "setupCommands": [
      {
        "description": "Enable pretty-printing",
        "text": "-enable-pretty-printing",
        "ignoreFailures": true
      }
    ]
  }
}
```

**Special Features:**
- Core dump analysis
- Memory inspection
- Multi-threaded debugging
- Pretty printing (STL containers)

**Common Issues:**
- **Issue:** "No debugging symbols found"
- **Fix:** Compile with `-g` flag: `gcc -g program.c`

### Go (Delve)

**Configuration:**
```json
{
  "language": "go",
  "debugger": "delve",
  "default_port": 2345,
  "attach_timeout": 10,
  "file_extensions": [".go"],
  "manifest_files": ["go.mod", "go.sum"],
  "launch_config": {
    "type": "go",
    "request": "launch",
    "mode": "debug",
    "program": "${file}"
  }
}
```

**Special Features:**
- Goroutine debugging
- Channel state inspection
- Interface type inspection
- Concurrent execution visualization

**Common Issues:**
- **Issue:** "delve not found"
- **Fix:** `go install github.com/go-delve/delve/cmd/dlv@latest`

### Rust (rust-gdb/lldb)

**Configuration:**
```json
{
  "language": "rust",
  "debugger": "rust-gdb",
  "default_port": null,
  "attach_timeout": 15,
  "file_extensions": [".rs"],
  "manifest_files": ["Cargo.toml", "Cargo.lock"],
  "launch_config": {
    "type": "lldb",
    "request": "launch",
    "program": "${workspaceFolder}/target/debug/${workspaceFolderBasename}",
    "sourceLanguages": ["rust"]
  }
}
```

**Special Features:**
- Ownership/borrow checking debugging
- Panic backtrace capture
- Enum variant inspection
- Trait object debugging

**Common Issues:**
- **Issue:** "Debug symbols not found"
- **Fix:** Ensure `[profile.dev]` has `debug = true` in Cargo.toml

## Session Management API

### Initialize Session

**Purpose:** Start new debugging session

**Preconditions:**
- No active session exists
- Language detected or specified
- Debugger available for language

**API Flow:**
```
1. Check prerequisites (debugger installed)
2. Detect/confirm language
3. Initialize DAP connection
4. Launch or attach to process
5. Set initial breakpoints (if any)
6. Mark session as active
```

**Error Handling:**
- Prerequisite missing → Show installation instructions
- Language ambiguous → Ask user to specify
- Connection timeout → Show manual start commands
- Process launch failure → Show process requirements

### Manage Active Session

**Session State:**
```json
{
  "session_id": "debug-12345",
  "language": "python",
  "pid": 54321,
  "status": "paused",
  "breakpoints": [{"id": 1, "line": 42, "file": "main.py"}],
  "current_frame": {"line": 42, "file": "main.py"},
  "started_at": "2025-11-24T10:30:00Z",
  "last_activity": "2025-11-24T10:45:00Z"
}
```

**Operations:**
- Check if session active
- Update last activity timestamp
- Get current session state
- Enforce single session per user

### Cleanup Session

**Triggers:**
- Explicit stop command
- Session timeout (30 minutes idle)
- Connection timeout (5 minutes idle)
- Process termination
- Error conditions

**Cleanup Steps:**
```
1. Send disconnect request to DAP
2. Terminate debugged process (if owned)
3. Close MCP connection
4. Clear breakpoints from state
5. Release resources (memory, ports)
6. Log session summary
```

**Guaranteed cleanup:** All cleanup on every exit path (success, error, timeout)

## Error Handling & Recovery

### Error Categories

#### E001: Prerequisite Missing

**Symptom:** "dap-mcp server not available"
**Cause:** dap-mcp not installed or not in PATH
**Recovery:**
```bash
npm install -g dap-mcp
export PATH=$PATH:$(npm bin -g)
npx dap-mcp --version
```

#### E002: Language Debugger Missing

**Symptom:** "debugpy not found" / "gdb not available"
**Cause:** Language-specific debugger not installed
**Recovery:** See language-specific installation in configuration section

#### E003: Session Timeout

**Symptom:** "Session timed out after 30 minutes"
**Cause:** No activity for 30 minutes
**Recovery:** Start new session with "debug this"

#### E004: Connection Timeout

**Symptom:** "Connection timed out after 5 minutes"
**Cause:** No response from debugger for 5 minutes
**Recovery:** Check if debugged process is responsive, restart session

#### E005: Concurrent Session

**Symptom:** "Another debugging session is active"
**Cause:** Single session enforcement
**Recovery:** Stop existing session with "stop debugging" or wait for timeout

#### E006: Memory Limit Exceeded

**Symptom:** "Debugged process exceeded 4GB memory limit"
**Cause:** Process memory usage > 4GB
**Recovery:** Reduce data structures, use sampling for large datasets

#### E007: Startup Timeout

**Symptom:** "Debugger failed to start within 10 seconds"
**Cause:** Process taking too long to initialize
**Recovery:** Check process requirements, increase timeout if needed

#### E008: Breakpoint Not Verified

**Symptom:** "Breakpoint at line 42 could not be verified"
**Cause:** Invalid line number or source file not found
**Recovery:** Check line number, ensure source file path correct

#### E009: Invalid Expression

**Symptom:** "Cannot evaluate expression 'xyz'"
**Cause:** Expression syntax error or variable not in scope
**Recovery:** Check expression syntax, verify variable scope

#### E010: Language Detection Failed

**Symptom:** "Could not detect project language"
**Cause:** No clear language indicators in project
**Recovery:** Specify language explicitly: "Debug this as Python code"

### Error Response Format

All errors return structured information:

```json
{
  "error_code": "E001",
  "error_type": "prerequisite_missing",
  "message": "dap-mcp server not available",
  "recovery_steps": [
    "Install dap-mcp: npm install -g dap-mcp",
    "Verify installation: npx dap-mcp --version",
    "Restart Claude Code"
  ],
  "documentation": "https://github.com/KashunCheng/dap_mcp",
  "manual_fallback": "Use debugger directly: python -m debugpy <script>"
}
```

### Graceful Degradation

If dap-mcp unavailable, provide manual debugger commands:

**Python:**
```bash
python -m debugpy --listen 5678 --wait-for-client script.py
```

**JavaScript:**
```bash
node --inspect-brk script.js
```

**C/C++:**
```bash
gdb ./program
break main
run
```

**Go:**
```bash
dlv debug main.go
```

**Rust:**
```bash
rust-gdb ./target/debug/program
```

## Resource Limits

### Memory Limits

**Debugged Process:** 4GB maximum
**Monitoring:** Check memory usage every 30 seconds
**Enforcement:** Terminate process if limit exceeded
**User Notification:** Show warning at 80% (3.2GB)

### Timeout Configuration

```json
{
  "session_timeout_minutes": 30,
  "connection_timeout_minutes": 5,
  "startup_timeout_seconds": 10,
  "command_timeout_seconds": 3,
  "breakpoint_timeout_seconds": 2
}
```

### Concurrent Sessions

**Limit:** 1 session per user
**Enforcement:** Block new session if existing active
**Override:** Stop existing session first

### Port Management

**Default Ports:**
- Python: 5678
- JavaScript: 9229
- Go: 2345

**Conflict Resolution:** Auto-increment port if default busy

### Process Isolation

- Debugger runs in separate process
- Process tree cleanup on session end
- No shared memory between Claude Code and debugged process

## Performance Expectations

| Operation | Target | 95th Percentile |
|-----------|--------|-----------------|
| Server startup | <10s | 12s |
| Set breakpoint | <2s | 3s |
| Step over/into/out | <3s | 4s |
| Variable inspection | <2s | 3s |
| Call stack retrieval | <2s | 3s |
| Session cleanup | <5s | 7s |

**Token Budget:**
- Orchestration: <100 tokens per command
- Intent detection: <20 tokens
- Language detection: <30 tokens (cached)
- Error messages: <50 tokens

## Security Model

**Threat Model:**
- Local-only execution (no remote debugging)
- User owns all code being debugged
- No untrusted code execution

**Security Boundaries:**
- Process isolation between Claude Code and debugger
- No authentication required (local-only)
- Full filesystem access (required for debugging)
- Network access allowed (debugger protocols)

**Not Protected Against:**
- Local privilege escalation (user can already do this)
- Code injection in debugged process (user owns the code)
- Resource exhaustion (memory/CPU limits enforced)

## API Version Compatibility

**DAP Version:** 1.51+
**MCP Version:** 1.0+
**dap-mcp Version:** 1.0+

**Breaking Changes:** None expected (protocols are stable)

**Version Detection:**
```json
{
  "tool": "dap_get_capabilities"
}
```

**Fallback:** If version mismatch, show warning and suggest upgrade
