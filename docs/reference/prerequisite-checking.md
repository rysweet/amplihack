# Prerequisite Checking System

**Last Updated**: 2026-02-03
**Version**: 0.9.0

## Overview

The prerequisite checking system ensures all required tools are installed before launching amplihack. It provides cross-platform detection, interactive installation, and comprehensive error handling.

## Core Components

### PrerequisiteChecker

Main class that orchestrates prerequisite verification and installation.

**Responsibilities:**

- Detect operating system and platform
- Check for required tools (claude, node, npm, rg)
- Prompt for interactive installation
- Execute platform-specific install commands
- Audit all installation attempts

### InstallationResult

Unified dataclass representing the outcome of an installation attempt.

```python
@dataclass
class InstallationResult:
    """Result of an installation attempt."""
    tool: str                                    # Tool being installed
    success: bool                                # Whether installation succeeded
    command_executed: list[str]                  # Command that was run
    stdout: str                                  # Standard output
    stderr: str                                  # Standard error
    exit_code: int                               # Process exit code
    timestamp: str                               # ISO 8601 timestamp
    user_approved: bool                          # User approval status
    message: str = ""                            # Human-readable summary
    verification_result: "ToolCheckResult | None" = None  # Post-install verification
```

**Key Attributes:**

- `message`: User-friendly description of result
- `verification_result`: Optional verification that tool works after install
- `command_executed`: Full command for audit trail

### Exception Handling

All subprocess operations use comprehensive exception handling:

```python
def check_copilot() -> bool:
    """Check if Copilot CLI is installed.

    Handles:
    - FileNotFoundError: Command not found (standard)
    - PermissionError: WSL permission denied (non-existent commands)
    - TimeoutExpired: Hanging command
    """
    try:
        subprocess.run(["copilot", "--version"],
                      capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False
```

**Why PermissionError?**
On Windows Subsystem for Linux (WSL), attempting to execute a non-existent command can raise `PermissionError` instead of `FileNotFoundError`. The system handles both gracefully.

## Platform Detection

Automatic OS detection with WSL support:

```python
class Platform(str, Enum):
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    WINDOWS = "windows"
    UNKNOWN = "unknown"
```

**Detection Logic:**

1. Check for WSL indicators (`/proc/version` contains "Microsoft")
2. Fall back to `platform.system()` mapping
3. Handle unknown platforms gracefully

## Installation Commands

Platform-specific commands for each tool:

| Platform | Tool | Command                       |
| -------- | ---- | ----------------------------- |
| macOS    | node | `brew install node`           |
| macOS    | rg   | `brew install ripgrep`        |
| Linux    | node | `sudo apt install -y nodejs`  |
| Linux    | npm  | `sudo apt install -y npm`     |
| Linux    | rg   | `sudo apt install -y ripgrep` |
| WSL      | node | `sudo apt install -y nodejs`  |

## Interactive Installation

User approval workflow:

1. **Detection**: Check if tool is available
2. **Prompt**: Ask user for approval with command preview
3. **Execute**: Run platform-specific install command
4. **Audit**: Log all attempts (success or failure)
5. **Verify**: Optional post-install verification

```python
# Example approval prompt
Do you want to proceed with installing node? [y/N]: y

Installing node...
The following command will be executed to install node:
  sudo apt install -y nodejs
```

## Audit Logging

All installation attempts logged to `.claude/runtime/logs/installation_audit.jsonl`:

```json
{
  "timestamp": "2026-02-03T10:30:00Z",
  "tool": "node",
  "platform": "linux",
  "command": ["sudo", "apt", "install", "-y", "nodejs"],
  "user_approved": true,
  "success": true,
  "exit_code": 0,
  "error_message": null
}
```

## Error Recovery

### Common Scenarios

| Error             | Cause                    | Resolution                         |
| ----------------- | ------------------------ | ---------------------------------- |
| PermissionError   | WSL non-existent command | Returns false, prompts for install |
| FileNotFoundError | Tool not in PATH         | Returns false, prompts for install |
| TimeoutExpired    | Hanging subprocess       | Returns false, skips tool          |
| Exit code 1       | Install failed           | Logs error, shows stderr to user   |

### Example Error Handling

```python
# Safe subprocess wrapper
def safe_subprocess_call(cmd: list[str], context: str, timeout: int = 30):
    """Safely execute subprocess with comprehensive error handling."""
    try:
        result = subprocess.run(
            cmd,
            stdin=sys.stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
        )
        return (result.returncode, result.stdout, result.stderr)
    except FileNotFoundError:
        return (-1, "", f"{context}: Command not found")
    except subprocess.TimeoutExpired:
        return (-1, "", f"{context}: Command timed out after {timeout}s")
    except PermissionError:
        return (-1, "", f"{context}: Permission denied")
```

## Usage Examples

### Check Prerequisites

```python
from amplihack.utils.prerequisites import check_prerequisites

# Non-interactive check
success = check_prerequisites(interactive=False)
if not success:
    print("Missing prerequisites detected")
    sys.exit(1)
```

### Interactive Installation

```python
from amplihack.utils.prerequisites import check_prerequisites

# Interactive with prompts
success = check_prerequisites(interactive=True)
# User will be prompted to install missing tools
```

### Check Specific Tool

```python
from amplihack.launcher.copilot import check_copilot

if check_copilot():
    print("Copilot CLI is installed")
else:
    print("Copilot CLI not found")
```

## Integration Points

### Launcher Integration

All launchers check prerequisites before execution:

```python
from amplihack.utils.prerequisites import check_prerequisites

def launch():
    if not check_prerequisites(interactive=True):
        sys.exit(1)
    # Continue with launch...
```

### Copilot Launcher

Specific copilot check with auto-install:

```python
from amplihack.launcher.copilot import check_copilot, install_copilot

if not check_copilot():
    print("Copilot CLI not found. Auto-installing...")
    if install_copilot():
        print("✓ Copilot CLI installed")
```

## Testing

### Unit Test Coverage

Comprehensive tests for all exception paths:

```python
# tests/launcher/test_copilot.py
class TestCheckCopilot:
    def test_check_copilot_installed(self, mock_run):
        """Test when copilot is available."""

    def test_check_copilot_not_found(self, mock_run):
        """Test FileNotFoundError handling."""

    def test_check_copilot_permission_error(self, mock_run):
        """Test PermissionError handling (WSL)."""

    def test_check_copilot_timeout(self, mock_run):
        """Test TimeoutExpired handling."""
```

### Manual Testing

Test in realistic environments:

```bash
# Test on fresh WSL system
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot

# Test on macOS
uvx --from git+https://github.com/rysweet/amplihack amplihack claude

# Test prerequisite detection
amplihack --check-prereqs
```

## Troubleshooting

### Issue: PermissionError on WSL

**Symptom**: `PermissionError: [Errno 13] Permission denied: 'copilot'`

**Cause**: WSL raises PermissionError for non-existent commands

**Solution**: System automatically handles this and prompts for installation

### Issue: Installation fails with exit code 1

**Symptom**: Tool installation command fails

**Causes**:

- Network connectivity issues
- Package repository problems
- Insufficient permissions

**Solution**: Check stderr output in audit log for specific error

### Issue: Tool installed but not detected

**Symptom**: Installation succeeds but verification fails

**Causes**:

- Tool not in PATH
- Shell environment not updated
- Need to restart shell

**Solution**:

```bash
# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Verify PATH
echo $PATH | grep -o '[^:]*node[^:]*'
```

## Related Documentation

- [Installation Guide](../installation.md)
- [Prerequisites Overview](PREREQUISITES.md)
- [Platform Support](../platform-support.md)

## Security Considerations

- **No shell=True**: All subprocess calls use list arguments to prevent shell injection
- **Hardcoded commands**: Only pre-approved commands in `INSTALL_COMMANDS` can be executed
- **User approval required**: Every installation prompts for explicit confirmation
- **Command preview**: Users see exact command before approval
- **Audit logging**: All attempts logged to `.claude/runtime/logs/installation_audit.jsonl`
- **Privilege escalation**: Commands using `sudo` are clearly marked in prompts

### Command Dictionaries (Security Design)

The system maintains TWO separate command dictionaries for security:

1. **INSTALL_COMMANDS_DISPLAY** (string format)
   - Multiple installation options shown to users
   - Examples: "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora..."
   - Never executed, only for display

2. **INSTALL_COMMANDS** (List[str] format)
   - Single hardcoded command per platform/tool
   - Example: ["sudo", "apt", "install", "-y", "nodejs"]
   - Prevents shell injection (no shell=True)
   - Only these commands can be executed

This separation ensures users see all options but only vetted commands can be executed.

## Performance

- Tool checks use 5-second timeouts for responsiveness
- Installation commands use 30-second default timeout
- Interactive prompts skip in CI environments (no TTY)
- Version parsing is fail-safe (invalid versions return False, not errors)

## Design Decisions

### Why Unified InstallationResult?

Previously had duplicate dataclass definitions causing TypeErrors. Consolidated to single source of truth with all necessary fields.

### Why Handle PermissionError?

WSL-specific behavior where non-existent commands raise PermissionError instead of standard FileNotFoundError. Cross-platform compatibility requires handling both.

### Why Interactive Installation?

Security and user control - never install software without explicit approval. All commands shown to user before execution.
