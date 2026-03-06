# Interactive Dependency Installation

This document describes the interactive dependency installation feature implemented for issue #1430.

## Overview

The interactive installation feature extends the prerequisite checking system to allow users to install missing dependencies with explicit approval, while maintaining strict security practices and audit logging.

## Key Features

### 1. User-Approved Installation

- **Explicit Consent**: Every installation requires user approval
- **Clear Information**: Shows exactly what command will be executed
- **Security Warnings**: Explains that commands may require sudo password
- **Decline Option**: Default is "no" - user must explicitly approve

### 2. Security Features

- **No Shell Injection**: Commands use `List[str]` format, never `shell=True`
- **Hardcoded Commands**: All commands from `INSTALL_COMMANDS` dictionary
- **Interactive stdin**: Uses `sys.stdin` to allow password prompts
- **Audit Logging**: All attempts logged to `~/.amplihack/.claude/runtime/logs/installation_audit.jsonl`
- **TTY Detection**: Prevents installation in non-interactive environments
- **CI Detection**: Automatically skips prompts in CI/CD environments

### 3. Edge Case Handling

- **Non-Interactive Mode**: Gracefully skips prompts, shows manual instructions
- **Declined Installation**: Records in audit log, continues to next tool
- **Failed Installation**: Captures errors, shows helpful diagnostics
- **Unknown Platform**: Provides generic installation guidance

## Architecture

### Data Structures

```python
@dataclass
class InstallationResult:
    """Result of an installation attempt."""
    tool: str
    success: bool
    command_executed: List[str]
    stdout: str
    stderr: str
    exit_code: int
    timestamp: str
    user_approved: bool

@dataclass
class InstallationAuditEntry:
    """Audit log entry for security tracking."""
    timestamp: str
    tool: str
    platform: str
    command: List[str]
    user_approved: bool
    success: bool
    exit_code: int
    error_message: Optional[str] = None
```

### Classes

#### `InteractiveInstaller`

Main class for handling interactive installations.

**Key Methods:**

- `is_interactive_environment()` - Check if running in interactive terminal
- `prompt_for_approval()` - Ask user for installation approval
- `install_tool()` - Install a tool with user approval
- `_execute_install_command()` - Execute command with interactive stdin
- `_log_audit()` - Log attempt to audit file

**Security Features:**

- TTY detection before prompting
- CI environment detection
- No shell=True subprocess calls
- Hardcoded commands only
- Comprehensive audit logging

#### `PrerequisiteChecker.check_and_install()`

Extended method that combines prerequisite checking with installation.

**Workflow:**

1. Check all prerequisites
2. If missing tools found:
   - Create `InteractiveInstaller` for platform
   - Check if interactive environment
   - For each missing tool:
     - Prompt user for approval
     - Execute installation if approved
     - Log result to audit log
3. Re-check prerequisites after installations
4. Return final status

## Usage

### Basic Usage

```python
from amplihack.utils.prerequisites import PrerequisiteChecker

checker = PrerequisiteChecker()
result = checker.check_and_install(interactive=True)

if result.all_available:
    print("All prerequisites installed!")
else:
    print(f"{len(result.missing_tools)} tools still missing")
```

### Non-Interactive Mode

```python
# Just check, don't install
result = checker.check_and_install(interactive=False)
# Same as check_all_prerequisites()
```

### Direct Installation

```python
from amplihack.utils.prerequisites import InteractiveInstaller, Platform

installer = InteractiveInstaller(Platform.MACOS)
result = installer.install_tool("node")

if result.success:
    print("Node.js installed successfully!")
elif not result.user_approved:
    print("Installation declined by user")
else:
    print(f"Installation failed: {result.stderr}")
```

## Installation Commands

The feature uses platform-specific installation commands stored in `INSTALL_COMMANDS`:

### macOS

```python
{
    "node": ["brew", "install", "node"],
    "npm": ["brew", "install", "node"],
    "uv": ["brew", "install", "uv"],
    "git": ["brew", "install", "git"],
    "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
}
```

### Linux (Ubuntu/Debian)

```python
{
    "node": ["sudo", "apt", "install", "-y", "nodejs"],
    "npm": ["sudo", "apt", "install", "-y", "npm"],
    "uv": ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
    "git": ["sudo", "apt", "install", "-y", "git"],
    "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
}
```

### Windows

```python
{
    "node": ["winget", "install", "OpenJS.NodeJS"],
    "npm": ["winget", "install", "OpenJS.NodeJS"],
    "uv": ["powershell", "-c", "irm https://astral.sh/uv/install.ps1 | iex"],
    "git": ["winget", "install", "Git.Git"],
    "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
}
```

## Audit Logging

All installation attempts are logged to `~/.amplihack/.claude/runtime/logs/installation_audit.jsonl` in JSONL format (one JSON object per line).

### Example Audit Entry

```json
{
  "timestamp": "2025-01-18T10:30:00Z",
  "tool": "node",
  "platform": "macos",
  "command": ["brew", "install", "node"],
  "user_approved": true,
  "success": true,
  "exit_code": 0,
  "error_message": null
}
```

### Declined Installation Entry

```json
{
  "timestamp": "2025-01-18T10:31:00Z",
  "tool": "npm",
  "platform": "macos",
  "command": ["brew", "install", "node"],
  "user_approved": false,
  "success": false,
  "exit_code": -1,
  "error_message": "User declined installation"
}
```

## Testing

The implementation includes comprehensive tests:

- **34 tests** for interactive installation features
- **35 tests** for existing prerequisite checking
- **100% passing** - all 69 tests pass

### Test Coverage

- Data structure creation and serialization
- Interactive environment detection (TTY, CI)
- User approval prompts (yes, no, invalid input)
- Command execution (success, failure, exceptions)
- Audit logging (success, errors, I/O failures)
- Security features (no shell injection, List[str] commands)
- Edge cases (non-interactive, empty tool name, unknown platform)
- Integration tests (full workflow, multiple tools)

### Running Tests

```bash
# All prerequisite tests
pytest tests/test_prerequisites.py tests/test_interactive_installer.py -v

# Just interactive installation tests
pytest tests/test_interactive_installer.py -v

# Specific test class
pytest tests/test_interactive_installer.py::TestInteractiveInstaller -v
```

## Security Considerations

### What We Do

1. **No Shell Injection**
   - Commands stored as `List[str]`
   - Never use `shell=True`
   - No string interpolation

2. **User Control**
   - Explicit approval required
   - Clear command visibility
   - Security warnings displayed

3. **Audit Trail**
   - All attempts logged
   - Includes success/failure
   - User approval status recorded

4. **Environment Detection**
   - TTY check before prompting
   - CI environment detection
   - Graceful degradation

### What We Don't Do

1. **Never Auto-Install** without user approval
2. **Never Hide Commands** from user
3. **Never Run Shell Scripts** directly (except uv via `sh -c`)
4. **Never Skip Logging** (even on I/O errors, logged to terminal)

## Example Output

### Successful Installation

```
======================================================================
MISSING PREREQUISITES DETECTED
======================================================================

Found 1 missing tool(s):
  - node

======================================================================

======================================================================
INSTALL NODE
======================================================================

The following command will be executed to install node:

  brew install node

This command may:
  - Require sudo password for system-level installation
  - Install dependencies automatically
  - Modify system packages or configuration

======================================================================

Do you want to proceed with installing node? [y/N]: y

Installing node...

[SUCCESS] node installed successfully

======================================================================
VERIFYING INSTALLATIONS
======================================================================

[SUCCESS] All prerequisites are now available!
```

### Declined Installation

```
======================================================================
INSTALL NPM
======================================================================

The following command will be executed to install npm:

  brew install node

This command may:
  - Require sudo password for system-level installation
  - Install dependencies automatically
  - Modify system packages or configuration

======================================================================

Do you want to proceed with installing npm? [y/N]: n

[SKIPPED] npm installation declined by user
```

### Non-Interactive Environment

```
======================================================================
MISSING PREREQUISITES DETECTED
======================================================================

Found 2 missing tool(s):
  - git
  - uv

======================================================================

Non-interactive environment detected.
Cannot prompt for installation. Please install manually:

======================================================================
INSTALLATION INSTRUCTIONS
======================================================================

Platform detected: linux

To install git:
  sudo apt install git

To install uv:
  curl -LsSf https://astral.sh/uv/install.sh | sh

======================================================================
```

## Philosophy Alignment

This implementation follows amplihack philosophy:

### Ruthless Simplicity

- Extends existing module instead of creating new one
- Direct, straightforward implementation
- No complex abstractions or frameworks

### Zero-BS Implementation

- All code works - no stubs or placeholders
- Every function tested and functional
- Clear error handling throughout

### Security First

- No shell injection vulnerabilities
- Explicit user control
- Comprehensive audit logging
- Safe subprocess handling

### User Control

- Never auto-install without approval
- Clear information before execution
- Easy to decline
- Graceful handling of edge cases

## Future Enhancements

Potential improvements for future iterations:

1. **Package Manager Detection** - Auto-detect apt vs dnf vs pacman on Linux
2. **Rollback Support** - Uninstall on failure
3. **Batch Approval** - Option to approve all at once
4. **Version Selection** - Install specific versions
5. **Dry Run Mode** - Show what would be installed without doing it
6. **Progress Indicators** - Better visual feedback during installation

## Related Files

- **Implementation**: `src/amplihack/utils/prerequisites.py`
- **Tests**: `tests/test_interactive_installer.py`, `tests/test_prerequisites.py`
- **Example**: `examples/interactive_install_demo.py`
- **Audit Log**: `~/.claude/runtime/logs/installation_audit.jsonl`
