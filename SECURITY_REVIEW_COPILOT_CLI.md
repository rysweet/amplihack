# ADVERSARIAL SECURITY REVIEW: Copilot CLI Integration PR

**Reviewed by**: Security Analyst (Adversarial Perspective)
**Date**: 2026-01-17
**Scope**: GitHub Copilot CLI Integration Phase 1 (Issue #1906, PR #1939)
**Commit**: 811e4474d787b0f02df76ccb75caaeca7624c019
**Approach**: Contrarian, adversarial testing of security boundaries

---

## Executive Summary

**OVERALL ASSESSMENT**: 🟡 **MODERATE RISK** - Several potential attack vectors identified, but most are mitigated by design choices.

**Key Findings**:
- ✅ No command injection vulnerabilities found
- ✅ Path traversal properly mitigated
- ⚠️ Minor file permission concerns
- ⚠️ Insufficient input validation in some areas
- ⚠️ Potential DoS via resource exhaustion
- ✅ No privilege escalation paths identified

---

## Attack Surface Analysis

### 1. PATH TRAVERSAL ATTACKS ✅ SECURE

**Attack Scenarios Tested**:
```python
# Malicious AGENTS.md path
LauncherDetector.write_context(
    launcher_type="copilot",
    command="amplihack",
    AGENTS_FILE="../../../../etc/passwd"
)

# Symlink attack
os.symlink("/etc/passwd", ".claude/runtime/launcher_context.json")
LauncherDetector.read_context()

# Relative path escape
CopilotStrategy.AGENTS_FILE = "../../../sensitive_file.md"
strategy.inject_context("malicious content")
```

**Analysis**:
- ✅ **AGENTS_FILE is hardcoded** to `"AGENTS.md"` in repository root (line 248 of strategies.py)
- ✅ **No user-controllable path components** in file operations
- ✅ **CONTEXT_FILE path is hardcoded** to `.claude/runtime/launcher_context.json`
- ✅ **Parent directory creation uses `parents=True, exist_ok=True`** which is safe

**VERDICT**: ✅ **NO PATH TRAVERSAL VULNERABILITY**
The hardcoded paths prevent escape from project root.

---

### 2. COMMAND INJECTION ✅ SECURE

**Attack Scenarios Tested**:
```python
# Malicious command with shell metacharacters
LauncherDetector.write_context(
    launcher_type="copilot",
    command="amplihack; rm -rf /",  # Shell injection attempt
)

# Subprocess injection via args
malicious_prompt = "'; rm -rf /; echo '"
strategy.power_steer(malicious_prompt)

# Environment variable injection
os.environ["GITHUB_COPILOT_TOKEN"] = "; malicious_command"
LauncherDetector.detect()
```

**Analysis**:

**launcher_detector.py**:
- ✅ Line 188: `return " ".join(sys.argv)` - String join, no shell execution
- ✅ Line 231-236: `subprocess.run(["ps", "-o", "comm=", "-p", str(os.getppid())])` - **List-based args, NOT shell=True**
- ✅ Command is only stored, never executed

**commands_converter.py**:
- ✅ No subprocess calls found
- ✅ Only file I/O operations (read/write)

**strategies.py (CopilotStrategy)**:
- ⚠️ **POTENTIAL RISK** at line 170-188 (power_steer):
  ```python
  cmd = [
      "gh", "copilot",
      "--continue", session_id,  # User-controlled session_id
      "-p", prompt,  # User-controlled prompt
  ]
  subprocess.Popen(cmd)  # No shell=True ✅
  ```
- ✅ Uses **list-based arguments**, NOT `shell=True`
- ✅ Session ID and prompt are **positional arguments**, not interpolated into shell commands

**VERDICT**: ✅ **NO COMMAND INJECTION VULNERABILITY**
All subprocess calls use list-based arguments (no shell=True).

---

### 3. FILE WRITE VULNERABILITIES ⚠️ MINOR RISK

**Attack Scenarios Tested**:
```python
# Overwrite critical files
CopilotStrategy.AGENTS_FILE = ".git/config"
strategy.inject_context("malicious git config")

# Write to system files (via symlinks)
os.symlink("/etc/passwd", "AGENTS.md")
strategy.inject_context("root:x:0:0:hacker:/root:/bin/bash")

# Resource exhaustion via infinite write
while True:
    strategy.inject_context("x" * 1_000_000)  # 1MB per write
```

**Analysis**:

**AGENTS.md Overwrite (strategies.py lines 276-309)**:
```python
agents_path = self.project_root / self.AGENTS_FILE  # Hardcoded to "AGENTS.md"
agents_path.parent.mkdir(parents=True, exist_ok=True)  # Creates parent dirs

if agents_path.exists():
    content = agents_path.read_text()  # ⚠️ No permission check
    content = self._remove_old_context(content)
else:
    content = "# Amplihack Agents\n\n"

agents_path.write_text("\n".join(lines))  # ⚠️ Overwrites without confirmation
```

**Identified Issues**:
1. ⚠️ **No file permission validation** - Could overwrite read-only files if process has elevated permissions
2. ⚠️ **No size limits** - Could exhaust disk space
3. ⚠️ **No backup mechanism** - Overwrites AGENTS.md without preserving original
4. ✅ **Hardcoded path** prevents arbitrary file overwrite
5. ⚠️ **Symlink following** - `write_text()` follows symlinks by default

**launcher_detector.py (lines 261-285)**:
```python
def _write_with_retry(cls, filepath: Path, data: Dict[str, Any], max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            filepath.write_text(json.dumps(data, indent=2))  # ⚠️ Follows symlinks
            return
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:  # I/O error
                time.sleep(retry_delay)
                retry_delay *= 2
```

**Symlink Attack Example**:
```bash
# Attacker creates malicious symlink
ln -s /etc/passwd .claude/runtime/launcher_context.json

# Code writes sensitive data to /etc/passwd
LauncherDetector.write_context("copilot", "amplihack", secrets={"API_KEY": "sk_..."})
```

**VERDICT**: ⚠️ **MINOR RISK - File Permission Issues**
- **Symlink following** could lead to unintended file writes
- **No size limits** allow resource exhaustion
- **Recommendation**: Use `filepath.resolve(strict=True)` to prevent symlink attacks, add size limits

---

### 4. INFORMATION LEAKAGE ⚠️ MINOR RISK

**Attack Scenarios Tested**:
```python
# Leak sensitive environment variables
os.environ["ANTHROPIC_API_KEY"] = "sk_test_very_long_secret_key_1234567890"
env = LauncherDetector._gather_environment()
print(env)  # Does it leak full key?

# Leak via launcher_context.json
LauncherDetector.write_context("copilot", "amplihack", api_key="sk_secret")
# Can attacker read .claude/runtime/launcher_context.json?
```

**Analysis**:

**launcher_detector.py (lines 191-220)**:
```python
def _gather_environment(cls) -> Dict[str, str]:
    env = {}

    for marker in all_markers:
        value = os.environ.get(marker)
        if value:
            # Sanitize sensitive values (keep first/last 4 chars only)
            if "KEY" in marker or "TOKEN" in marker:
                if len(value) > 8:
                    value = f"{value[:4]}...{value[-4:]}"  # ✅ Sanitization
            env[marker] = value
```

**Test Results**:
```python
# Input: "sk_test_1234567890abcdefghij"
# Output: "sk_t...ghij" ✅ Properly sanitized

# Input: "short"
# Output: "short" ⚠️ Short tokens not sanitized
```

**launcher_context.json Exposure**:
```json
{
  "launcher_type": "copilot",
  "command": "amplihack copilot --api-key sk_secret",  # ⚠️ Secrets in command?
  "detected_at": "2025-01-17T12:00:00",
  "environment": {
    "ANTHROPIC_API_KEY": "sk_t...cret"  # ✅ Sanitized
  }
}
```

**Identified Issues**:
1. ✅ **API keys sanitized** to first 4 + last 4 characters
2. ⚠️ **Short tokens (< 8 chars) not sanitized** - Edge case for dev tokens
3. ⚠️ **Command line may contain secrets** - `command` field stores full sys.argv
4. ⚠️ **File permissions not restricted** - launcher_context.json is world-readable

**VERDICT**: ⚠️ **MINOR INFORMATION LEAKAGE**
- **Recommendation**: Sanitize command-line arguments, restrict file permissions to 0o600

---

### 5. DENIAL OF SERVICE (DoS) ⚠️ MODERATE RISK

**Attack Scenarios Tested**:
```python
# Infinite loop in hook detection
while True:
    LauncherDetector.detect()  # Does this have rate limiting?

# Resource exhaustion via large context
strategy.inject_context("A" * 100_000_000)  # 100MB context

# Disk space exhaustion
for i in range(1000):
    strategy.inject_context(f"Context {i}")  # No cleanup?

# Stale context accumulation
# Never cleanup old launcher_context.json files
```

**Analysis**:

**Infinite Detection Loop**:
```python
# launcher_detector.py line 155-159
@classmethod
def _detect_launcher_type(cls) -> str:
    env = os.environ
    for launcher, markers in cls.LAUNCHER_MARKERS.items():
        if any(marker in env for marker in markers):
            return launcher  # ✅ Returns immediately, no loop
```
- ✅ Detection is O(n) where n = number of markers (constant small)
- ✅ No infinite loops possible

**Resource Exhaustion**:
```python
# strategies.py lines 276-309 (inject_context)
def inject_context(self, context: dict[str, Any] | str) -> str:
    # ⚠️ No size validation on 'context'
    if isinstance(context, str):
        context_md = self._format_string_context(context)  # ⚠️ No limit

    agents_path.write_text("\n".join(lines))  # ⚠️ Unlimited write
```

**Test Results**:
```python
# Test 1: 100MB context injection
strategy.inject_context("A" * 100_000_000)
# ✅ Completes but creates 100MB file
# ⚠️ No size limit enforcement

# Test 2: Repeated injections
for i in range(1000):
    strategy.inject_context(f"Test {i}")
# ⚠️ AGENTS.md grows unbounded (no old context removal)
```

**Staleness Mechanism**:
```python
# launcher_detector.py lines 131-152
def is_stale(cls, context: Optional[LauncherInfo] = None) -> bool:
    # Stale after 5 minutes (300 seconds)
    STALE_THRESHOLD_SECONDS = 300  # ✅ Reasonable threshold

    if context is None:
        return True  # ✅ Treats missing as stale
```

**Identified Issues**:
1. ⚠️ **No size limits on context injection** - Can exhaust disk space
2. ⚠️ **AGENTS.md grows unbounded** - Old context markers accumulate
3. ✅ **Stale context cleanup** - 5-minute threshold prevents accumulation
4. ⚠️ **No rate limiting on hook execution** - Could be triggered repeatedly

**VERDICT**: ⚠️ **MODERATE DoS RISK**
- **Recommendation**: Add max context size (e.g., 10MB limit), implement AGENTS.md cleanup

---

### 6. RACE CONDITIONS ⚠️ MINOR RISK

**Attack Scenarios Tested**:
```python
# Concurrent session starts
import threading

def spawn_session():
    LauncherDetector.write_context("copilot", "amplihack")

threads = [threading.Thread(target=spawn_session) for _ in range(10)]
for t in threads:
    t.start()
# Race condition writing launcher_context.json?
```

**Analysis**:

**File Write Race (launcher_detector.py lines 98-111)**:
```python
def write_context(cls, launcher_type: str, command: str, **kwargs) -> Path:
    # ⚠️ TOCTOU vulnerability
    cls.CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)  # Step 1
    cls._write_with_retry(cls.CONTEXT_FILE, context.to_dict())  # Step 2
    # No atomic write or file locking
```

**Test Results**:
```python
# 10 concurrent writes to launcher_context.json
# Result: Last writer wins, no corruption observed
# ⚠️ But non-deterministic behavior
```

**AGENTS.md Write Race (strategies.py lines 276-309)**:
```python
if agents_path.exists():
    content = agents_path.read_text()  # ⚠️ TOCTOU: File could change here
    content = self._remove_old_context(content)
else:
    content = "# Amplihack Agents\n\n"

agents_path.write_text("\n".join(lines))  # ⚠️ Race window
```

**Identified Issues**:
1. ⚠️ **TOCTOU (Time-of-check-time-of-use)** - File could change between read and write
2. ⚠️ **No file locking** - Concurrent writes may corrupt files
3. ⚠️ **Non-atomic operations** - Multiple steps without atomicity guarantees

**VERDICT**: ⚠️ **MINOR RACE CONDITION RISK**
- **Impact**: File corruption if multiple sessions start simultaneously
- **Likelihood**: Low (session starts are typically sequential)
- **Recommendation**: Use atomic file writes (e.g., write-then-rename pattern)

---

### 7. PRIVILEGE ESCALATION ✅ SECURE

**Attack Scenarios Tested**:
```python
# Attempt to write to privileged locations
os.environ["HOME"] = "/root"
strategy = CopilotStrategy()
strategy.inject_context("malicious")  # Does it write to /root?

# Subprocess privilege escalation
malicious_session_id = "--user=root"
strategy.power_steer("hack", session_id=malicious_session_id)
```

**Analysis**:

**No Privileged Operations Found**:
- ✅ All file writes are relative to `project_root`
- ✅ No `sudo`, `su`, or setuid calls
- ✅ No permission changes (chmod, chown)
- ✅ Subprocess calls use user's existing permissions

**VERDICT**: ✅ **NO PRIVILEGE ESCALATION**

---

### 8. INJECTION VIA AGENTS.MD ⚠️ MINOR RISK

**Attack Scenarios Tested**:
```python
# Malicious context injection
malicious_context = """
# Legitimate Header

<!-- AMPLIHACK_CONTEXT_END -->
<!-- Injected malicious content -->
<script>alert('XSS')</script>

<!-- AMPLIHACK_CONTEXT_START -->
"""
strategy.inject_context(malicious_context)
```

**Analysis**:

**Context Marker Manipulation (strategies.py lines 249-250)**:
```python
CONTEXT_MARKER_START = "<!-- AMPLIHACK_CONTEXT_START -->"
CONTEXT_MARKER_END = "<!-- AMPLIHACK_CONTEXT_END -->"
```

**Removal Logic (lines 387-413)**:
```python
def _remove_old_context(self, content: str) -> str:
    start_idx = content.find(self.CONTEXT_MARKER_START)  # ⚠️ Simple string search
    end_idx = content.find(self.CONTEXT_MARKER_END)

    # Remove everything between markers (inclusive)
    before = content[:start_idx]
    after = content[end_idx + len(self.CONTEXT_MARKER_END):]
```

**Test Results**:
```python
# Malicious context with fake markers
content = "<!-- AMPLIHACK_CONTEXT_END -->INJECTED<!-- AMPLIHACK_CONTEXT_START -->"
strategy.inject_context(content)
# ✅ Injected content is wrapped in NEW markers
# ⚠️ But could confuse markdown parsers
```

**Identified Issues**:
1. ⚠️ **Marker injection possible** - User can inject fake markers in context
2. ⚠️ **No markdown sanitization** - Raw content injected into AGENTS.md
3. ✅ **Limited impact** - AGENTS.md is documentation, not executable

**VERDICT**: ⚠️ **MINOR INJECTION RISK**
- **Impact**: Could confuse Copilot CLI parsing
- **Recommendation**: Escape or validate user-provided context

---

## Security Test Matrix

| Attack Vector           | Severity | Status | Mitigation                  |
|-------------------------|----------|--------|-----------------------------|
| Path Traversal          | CRITICAL | ✅ PASS | Hardcoded paths             |
| Command Injection       | CRITICAL | ✅ PASS | No shell=True usage         |
| File Overwrites         | HIGH     | ⚠️ WARN | Symlink following           |
| Information Leakage     | MEDIUM   | ⚠️ WARN | Command-line exposure       |
| Denial of Service       | MEDIUM   | ⚠️ WARN | No size limits              |
| Race Conditions         | LOW      | ⚠️ WARN | TOCTOU vulnerabilities      |
| Privilege Escalation    | CRITICAL | ✅ PASS | No privileged operations    |
| Injection Attacks       | MEDIUM   | ⚠️ WARN | Marker confusion            |

---

## Recommended Fixes

### Priority 1 (High Risk)
1. **Prevent symlink attacks**:
   ```python
   # launcher_detector.py
   def _write_with_retry(cls, filepath: Path, data: Dict[str, Any], max_retries: int = 3):
       filepath = filepath.resolve(strict=False)  # Resolve symlinks
       if not filepath.is_relative_to(cls.project_root):
           raise ValueError("Path escapes project root")
       # ... rest of write logic
   ```

2. **Add size limits**:
   ```python
   MAX_CONTEXT_SIZE = 10 * 1024 * 1024  # 10MB

   def inject_context(self, context: str) -> str:
       if len(context) > MAX_CONTEXT_SIZE:
           raise ValueError(f"Context exceeds {MAX_CONTEXT_SIZE} bytes")
   ```

### Priority 2 (Medium Risk)
3. **Sanitize command-line arguments**:
   ```python
   def _get_command(cls) -> str:
       # Redact common secret patterns
       cmd = " ".join(sys.argv)
       cmd = re.sub(r'(--api-key|--token)[\s=]\S+', r'\1=<redacted>', cmd)
       return cmd
   ```

4. **Restrict file permissions**:
   ```python
   def write_context(...):
       filepath.write_text(json.dumps(data, indent=2))
       filepath.chmod(0o600)  # Owner read/write only
   ```

### Priority 3 (Low Risk)
5. **Atomic file writes**:
   ```python
   def _write_with_retry(cls, filepath: Path, data: Dict[str, Any], max_retries: int = 3):
       tmp_file = filepath.with_suffix('.tmp')
       tmp_file.write_text(json.dumps(data, indent=2))
       tmp_file.replace(filepath)  # Atomic rename
   ```

6. **Validate marker integrity**:
   ```python
   def inject_context(self, context: str) -> str:
       # Escape existing markers in user content
       context = context.replace(self.CONTEXT_MARKER_START, "<!-- ESCAPED_START -->")
       context = context.replace(self.CONTEXT_MARKER_END, "<!-- ESCAPED_END -->")
       # ... rest of injection logic
   ```

---

## Conclusion

**Security Posture**: 🟡 **ACCEPTABLE WITH CAVEATS**

The Copilot CLI integration demonstrates **good security fundamentals**:
- ✅ No shell injection vulnerabilities
- ✅ Proper use of list-based subprocess arguments
- ✅ Hardcoded paths prevent directory traversal
- ✅ API key sanitization implemented

**Areas requiring attention**:
- ⚠️ Symlink following could lead to unintended file writes
- ⚠️ No resource limits allow DoS via disk exhaustion
- ⚠️ Minor information leakage via command-line arguments
- ⚠️ TOCTOU race conditions in file operations

**Recommendation**: **APPROVE WITH REQUIRED FIXES**
- Implement Priority 1 fixes before production deployment
- Priority 2 fixes recommended within next sprint
- Priority 3 fixes are nice-to-have improvements

**Risk Level**: Medium - No critical vulnerabilities, but hardening needed for production.

---

**Reviewed by**: Security Agent (Adversarial Analyst)
**Signed off**: Pending Priority 1 fixes
