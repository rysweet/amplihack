# Shell Command Hook Feature

## Overview

This feature adds a secure shell command execution capability to Claude Code
through a UserPromptSubmit hook. Users can execute safe shell commands by
prefixing prompts with `!`, which blocks the original prompt submission and
displays the command output.

## Usage

Type prompts starting with `!` followed by a shell command:

```
!ls -la
!pwd
!date
!whoami
```

## Security Features

### ✅ **Whitelist-Based Command Validation**

Only the following commands are allowed:

- `ls`, `pwd`, `date`, `echo`, `cat`, `head`, `tail`
- `wc`, `grep`, `find`, `sort`, `uniq`, `cut`
- `whoami`, `uname`, `df`, `du`, `ps`, `which`, `type`

### ✅ **Dangerous Pattern Blocking**

The following patterns are automatically blocked:

- Shell metacharacters: `;`, `&`, `|`, `` ` ``, `$`, `(`, `)`
- Path traversal: `../`, `/etc/`, `/root/`, `/usr/`, `/var/`
- Privilege escalation: `sudo`, `su`
- Network access: `curl`, `wget`, `nc`
- File operations: `rm`, `mv`, `cp`, `chmod`, `chown`
- Code execution: `python -c`, `bash -c`, `sh -c`

### ✅ **Restricted Execution Environment**

- Commands run in `/tmp` directory
- Minimal environment variables (PATH, HOME, USER, SHELL, TERM, LC_ALL)
- 5-second execution timeout
- No network access
- No privileged operations

### ✅ **Output Sanitization**

- Sensitive patterns are redacted (passwords, API keys, emails, etc.)
- Output limited to 5000 bytes
- Truncated output clearly marked

### ✅ **Resource Limits**

- 5-second maximum execution time
- Process isolation with `setsid`
- Limited environment variables
- Restricted working directory

## Installation

1. **Hook File**: `.claude/hooks/user_prompt_submit.py` (executable)
2. **Settings Configuration**: Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/user_prompt_submit.py",
            "timeout": 35000
          }
        ]
      }
    ]
  }
}
```

## Examples

### ✅ **Safe Commands (Allowed)**

```
!ls -la
$ ls -la

Output:
total 28640
drwxrwxrwt  545 root  wheel    17440 Oct  4 11:33 .
drwxr-xr-x    6 root  wheel      192 Oct  2 16:41 ..
...

!whoami
$ whoami

Output:
ryan

!date
$ date

Output:
Sat Oct  4 11:37:06 PDT 2025
```

### ❌ **Dangerous Commands (Blocked)**

```
!rm -rf /
🚫 SECURITY: Command blocked
Command: rm -rf /

Security Policy:
• Only whitelisted commands are allowed
• Allowed: ls, pwd, date, echo, cat, head, tail, wc, grep, find, sort, uniq, cut, whoami, uname, df, du, ps, which, type
• Dangerous patterns and system access are blocked

Error: Command blocked by security policy. Only safe, whitelisted commands are allowed.

!curl http://malicious-site.com
🚫 SECURITY: Command blocked
...

!sudo rm important-file
🚫 SECURITY: Command blocked
...
```

## Security Testing

The implementation includes comprehensive security tests covering:

- **Command injection attempts** (`;`, `&&`, `|`)
- **Network access attempts** (`curl`, `wget`)
- **Privilege escalation** (`sudo`, `su`)
- **Path traversal** (`../`, `/etc/passwd`)
- **Shell injection** (`bash -c`, `python -c`)
- **File system attacks** (`rm`, `mv`, `chmod`)

All dangerous commands are properly blocked while safe commands execute
successfully.

## Technical Implementation

### **Core Components**

1. **SecurityConfig**: Defines whitelisted commands and dangerous patterns
2. **SecureCommandValidator**: Validates commands against security policies
3. **OutputSanitizer**: Removes sensitive information from output
4. **SecureExecutor**: Executes commands in restricted environment

### **Security Architecture**

```
User Input (!) → Command Validation → Execution Environment → Output Sanitization → Blocked Response
                       ↓                        ↓                      ↓
                 Whitelist Check         Restricted /tmp          Redact Sensitive
                 Pattern Check           Timeout Limits           Truncate Length
                 Argument Check          Minimal ENV              Safe Display
```

### **Error Handling**

- Invalid commands: Security policy message with allowed commands
- Execution failures: Safe error messages without system information
- Timeouts: Clear timeout notification (5-second limit)
- Exceptions: Generic error handling without information disclosure

## Files

- **Hook**: `.claude/hooks/user_prompt_submit.py` (377 lines)
- **Settings**: `.claude/settings.json` (UserPromptSubmit configuration)
- **Tests**: `test_shell_hook.py` (basic functionality)
- **Security Tests**: `test_security.py` (comprehensive security validation)
- **Documentation**: `SHELL_COMMAND_HOOK.md` (this file)

## Security Recommendations

### ✅ **Safe for Development Use**

This implementation is secure for development environments where:

- Users need quick access to basic shell commands
- Security is important but convenience is also valued
- Commands are limited to read-only operations and safe utilities

### ⚠️ **Production Considerations**

For production environments:

- Review the whitelist of allowed commands
- Consider additional sandboxing (firejail, containers)
- Monitor command usage through audit logs
- Implement user-specific rate limiting

### 🔒 **Security Principles Applied**

- **Whitelist over blacklist**: Only known-safe commands allowed
- **Defense in depth**: Multiple validation layers
- **Principle of least privilege**: Minimal execution environment
- **Fail securely**: Blocks unknown/dangerous commands by default
- **Output sanitization**: Prevents information disclosure

## Testing

Run the test suites to verify functionality:

```bash
# Basic functionality tests
python3 test_shell_hook.py

# Comprehensive security tests
python3 test_security.py
```

Both test suites should pass with 100% success rate.

---

**Security Notice**: This feature allows shell command execution. While
extensively secured, use with appropriate caution and only in trusted
environments. All commands are logged and executed with restricted privileges.
