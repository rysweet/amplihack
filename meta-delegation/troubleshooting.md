# Meta-Delegation Troubleshooting

**Common problems and solutions for meta-agentic task delegation.**

---

## Quick Diagnosis

Start here to identify your issue:

### Symptom Checklist

- [Delegation times out](#delegation-timeout)
- [Subprocess fails to start](#subprocess-fails-to-start)
- [Low success scores](#low-success-scores)
- [Missing evidence](#missing-evidence)
- [Platform not found](#platform-not-found)
- [Permission errors](#permission-errors)
- [Out of memory errors](#out-of-memory-errors)
- [Partial results](#partial-results-unexpected)
- [Evidence export fails](#evidence-export-fails)
- [Persona behavior unexpected](#persona-behavior-unexpected)

---

## Common Issues

### Delegation Timeout

**Symptom:**

```
DelegationTimeout: Execution exceeded 30 minutes
  elapsed_minutes: 30.5
  timeout_minutes: 30
```

**Causes:**

1. Task is too complex for the timeout
2. Agent is stuck in a loop
3. Platform CLI is hanging

**Solutions:**

#### Solution 1: Increase Timeout

```python
# For complex tasks, allow more time
result = run_meta_delegation(
    goal="Complex architecture design",
    success_criteria="...",
    timeout_minutes=60  # Increase from default 30
)
```

#### Solution 2: Check Partial Results

```python
from amplihack.meta_delegation import run_meta_delegation, DelegationTimeout

try:
    result = run_meta_delegation(goal="...", success_criteria="...")
except DelegationTimeout as e:
    # Check what was completed
    if e.partial_result:
        print(f"Evidence collected: {len(e.partial_result.evidence)}")
        # Review evidence to see progress
        for item in e.partial_result.evidence:
            print(f"  - {item.type}: {item.path}")
```

#### Solution 3: Break Into Smaller Tasks

```python
# Instead of one large task
result = run_meta_delegation(
    goal="Design and implement complete system",
    success_criteria="..."
)

# Break into phases
design = run_meta_delegation(
    goal="Design system architecture",
    success_criteria="Architecture doc with clear boundaries",
    timeout_minutes=20
)

implementation = run_meta_delegation(
    goal="Implement system following architecture",
    success_criteria="Working code with tests",
    context=design.get_evidence_by_type("architecture_doc")[0].content,
    timeout_minutes=30
)
```

#### Solution 4: Check Execution Log

```python
result = run_meta_delegation(...)

# Check if agent is stuck
log_lines = result.execution_log.split('\n')
last_20 = log_lines[-20:]

# Look for repeating patterns
if any(line.count("Retrying") > 5 for line in last_20):
    print("Agent appears stuck in retry loop")
```

---

### Subprocess Fails to Start

**Symptom:**

```
DelegationError: Failed to spawn subprocess
  reason: Command not found: claude
  exit_code: 127
```

**Causes:**

1. Platform CLI not installed
2. Platform not in PATH
3. Missing dependencies

**Solutions:**

#### Solution 1: Verify Platform Installation

```bash
# Check if platform is available
which claude         # For Claude Code
which gh             # For Copilot (uses gh cli)
which amplifier      # For Amplifier

# If missing, install platform
# Claude Code: Follow Claude installation guide
# Copilot: gh extension install github/gh-copilot
# Amplifier: Follow Amplifier installation guide
```

#### Solution 2: Check PATH

```python
import os
import shutil

# Verify platform in PATH
platform_cmd = "claude"  # or "gh", "amplifier"
if not shutil.which(platform_cmd):
    print(f"ERROR: {platform_cmd} not found in PATH")
    print(f"Current PATH: {os.environ.get('PATH')}")

    # Add platform to PATH if needed
    os.environ['PATH'] = f"/path/to/platform/bin:{os.environ['PATH']}"
```

#### Solution 3: Use Specific Platform Path

```python
from amplihack.meta_delegation import run_meta_delegation

result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    platform="claude-code",
    environment={
        "CLAUDE_CLI_PATH": "/custom/path/to/claude"
    }
)
```

---

### Low Success Scores

**Symptom:**

```
Status: SUCCESS
Success Score: 45/100
Evidence: 3 items
```

Task completed but score is unexpectedly low.

**Causes:**

1. Success criteria too strict or unclear
2. Missing expected evidence types
3. Tests failing
4. Incomplete implementation

**Solutions:**

#### Solution 1: Review Success Criteria

```python
# Too vague - hard to evaluate
success_criteria = "Make it good"

# Better - specific and measurable
success_criteria = """
- Module has add() and subtract() functions
- Functions handle negative numbers
- Has at least 5 test cases
- All tests pass
"""
```

#### Solution 2: Check Evidence Details

```python
result = run_meta_delegation(...)

if result.success_score < 70:
    print(f"Low score: {result.success_score}/100")

    # What's missing?
    print("\nEvidence collected:")
    for item in result.evidence:
        print(f"  {item.type}: {item.path}")

    print("\nExpected evidence types:")
    expected = ["code_file", "test_file", "documentation"]
    for exp_type in expected:
        if not result.get_evidence_by_type(exp_type):
            print(f"  ✗ Missing: {exp_type}")
```

#### Solution 3: Check Test Results

```python
result = run_meta_delegation(...)

# Look for test failures in logs
if "FAILED" in result.execution_log or "ERROR" in result.execution_log:
    print("Tests failed - checking details:")

    # Find test output
    test_results = result.get_evidence_by_type("test_results")
    if test_results:
        print(test_results[0].content)
```

#### Solution 4: Try Different Persona

```python
# If junior_dev produces low scores
result_junior = run_meta_delegation(
    goal="...",
    success_criteria="...",
    persona_type="junior_dev"
)
print(f"Junior dev score: {result_junior.success_score}/100")

# Try qa_engineer for more thoroughness
result_qa = run_meta_delegation(
    goal="...",
    success_criteria="...",
    persona_type="qa_engineer"
)
print(f"QA engineer score: {result_qa.success_score}/100")
```

---

### Missing Evidence

**Symptom:**

```
Status: SUCCESS
Success Score: 75/100
Evidence: 1 item (only execution_log)
```

Task completed but expected artifacts not collected.

**Causes:**

1. Agent didn't create files
2. Files created outside working directory
3. Evidence collector patterns not matching files

**Solutions:**

#### Solution 1: Check Working Directory

```python
import os

result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    working_directory="/tmp/my_delegation"  # Explicit directory
)

# After completion, check directory
if os.path.exists("/tmp/my_delegation"):
    files = os.listdir("/tmp/my_delegation")
    print(f"Files in working directory: {files}")
```

#### Solution 2: Check Execution Log for File Paths

```python
result = run_meta_delegation(...)

# Search log for file creation
import re
file_mentions = re.findall(r"Created|Wrote|Saved.*?(\S+\.\w+)", result.execution_log)
print(f"Files mentioned in log: {file_mentions}")

# Check if files exist but weren't collected
for file_path in file_mentions:
    if not any(e.path == file_path for e in result.evidence):
        print(f"File created but not collected: {file_path}")
```

#### Solution 3: Enable Artifact Preservation

```python
import os

# Keep artifacts after delegation
os.environ["META_DELEGATION_KEEP_ARTIFACTS"] = "true"

result = run_meta_delegation(...)

# Now you can inspect working directory after completion
print(f"Artifacts preserved in: {result.working_directory}")
```

---

### Platform Not Found

**Symptom:**

```
ValueError: Invalid platform: my-platform
  Valid platforms: claude-code, copilot, amplifier
```

**Causes:**

1. Typo in platform name
2. Custom platform not registered

**Solutions:**

#### Solution 1: Check Platform Name

```python
# Incorrect
result = run_meta_delegation(platform="claude")  # Wrong
result = run_meta_delegation(platform="github-copilot")  # Wrong

# Correct
result = run_meta_delegation(platform="claude-code")
result = run_meta_delegation(platform="copilot")
result = run_meta_delegation(platform="amplifier")
```

#### Solution 2: List Available Platforms

```python
from amplihack.meta_delegation import list_platforms

print("Available platforms:")
for platform in list_platforms():
    print(f"  - {platform}")
```

---

### Permission Errors

**Symptom:**

```
DelegationError: Permission denied
  reason: Cannot write to /restricted/directory
```

**Causes:**

1. Insufficient permissions for working directory
2. Protected system directories

**Solutions:**

#### Solution 1: Use User-Writable Directory

```python
import os
import tempfile

# Use temp directory (always writable)
temp_dir = tempfile.mkdtemp(prefix="meta_delegation_")

result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    working_directory=temp_dir
)
```

#### Solution 2: Check Directory Permissions

```bash
# Check permissions on working directory
ls -ld /path/to/working/directory

# Make writable if needed
chmod 755 /path/to/working/directory
```

---

### Out of Memory Errors

**Symptom:**

```
DelegationError: Subprocess killed
  reason: Out of memory (OOM)
  exit_code: 137
```

**Causes:**

1. Large code generation
2. Memory leak in subprocess
3. Insufficient system memory

**Solutions:**

#### Solution 1: Monitor Memory Usage

```python
import psutil
from amplihack.meta_delegation import run_meta_delegation

# Check available memory before delegation
available_mb = psutil.virtual_memory().available / (1024 * 1024)
print(f"Available memory: {available_mb:.0f} MB")

if available_mb < 500:
    print("WARNING: Low memory available")
```

#### Solution 2: Reduce Scope

```python
# Instead of large codebase
result = run_meta_delegation(
    goal="Generate entire application with 20 modules",
    success_criteria="..."
)

# Generate incrementally
for module_name in modules:
    result = run_meta_delegation(
        goal=f"Generate {module_name} module",
        success_criteria="...",
        timeout_minutes=10
    )
```

#### Solution 3: Set Memory Limits

```bash
# Limit subprocess memory (Linux)
export META_DELEGATION_MEMORY_LIMIT="1G"

# Run delegation
python my_delegation.py
```

---

### Partial Results Unexpected

**Symptom:**

```
Status: PARTIAL
Success Score: 65/100
```

Expected SUCCESS but got PARTIAL.

**Causes:**

1. Some success criteria not met
2. Tests partially passing
3. Incomplete implementation

**Solutions:**

#### Solution 1: Review Partial Completion Notes

```python
result = run_meta_delegation(...)

if result.status == "PARTIAL":
    print(f"Partial completion: {result.success_score}/100")
    print(f"\nNotes:\n{result.partial_completion_notes}")

    # What was achieved?
    print("\nCompleted:")
    for item in result.evidence:
        print(f"  ✓ {item.type}: {item.path}")
```

#### Solution 2: Retry with Adjustments

```python
result = run_meta_delegation(
    goal="Complex implementation",
    success_criteria="Feature A, Feature B, Feature C, comprehensive tests"
)

if result.status == "PARTIAL":
    # Check what's missing
    if not result.get_evidence_by_type("test_file"):
        # Retry focusing on tests
        result = run_meta_delegation(
            goal="Add tests to existing implementation",
            success_criteria="Tests for Feature A, B, C with >80% coverage",
            context=result.get_evidence_by_type("code_file")[0].content
        )
```

---

### Evidence Export Fails

**Symptom:**

```python
result.export_evidence("./archive")
# Error: Directory exists but is not empty
```

**Solutions:**

#### Solution 1: Use Unique Directory Names

```python
from datetime import datetime

# Generate unique directory name
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
archive_dir = f"./evidence_{timestamp}"

result.export_evidence(archive_dir)
print(f"Evidence exported to: {archive_dir}")
```

#### Solution 2: Clear Existing Directory

```python
import shutil
import os

archive_dir = "./evidence_archive"

# Remove if exists
if os.path.exists(archive_dir):
    shutil.rmtree(archive_dir)

result.export_evidence(archive_dir)
```

---

### Persona Behavior Unexpected

**Symptom:**

Using `guide` persona but getting implementation without explanations.

**Causes:**

1. Persona selection ignored
2. Goal overrides persona behavior
3. Platform doesn't support persona hints

**Solutions:**

#### Solution 1: Verify Persona Selection

```python
result = run_meta_delegation(
    goal="Explain how OAuth works",
    success_criteria="Clear explanation with examples",
    persona_type="guide"  # Make sure this is specified
)

# Verify persona was used
print(f"Persona used: {result.persona_used}")
```

#### Solution 2: Align Goal with Persona

```python
# Goal doesn't match guide persona
result = run_meta_delegation(
    goal="Implement OAuth quickly",  # Implementation goal
    success_criteria="Working code",
    persona_type="guide"  # Teaching persona - mismatch!
)

# Better alignment
result = run_meta_delegation(
    goal="Teach me OAuth by building a simple example",  # Teaching goal
    success_criteria="Clear explanation, simple working example, step-by-step",
    persona_type="guide"  # Now aligned
)
```

#### Solution 3: Check Persona Effectiveness

```python
# Try same task with different personas
personas = ["guide", "qa_engineer", "architect", "junior_dev"]

for persona in personas:
    result = run_meta_delegation(
        goal="Same task",
        success_criteria="Same criteria",
        persona_type=persona
    )
    print(f"{persona:12} | Score: {result.success_score:3}/100 | Evidence: {len(result.evidence):2}")
```

---

## Diagnostic Tools

### Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("amplihack.meta_delegation")
logger.setLevel(logging.DEBUG)

result = run_meta_delegation(...)
# Will output detailed debug information
```

### Inspect Subprocess State

```python
result = run_meta_delegation(...)

print(f"Subprocess PID: {result.subprocess_pid}")
print(f"Duration: {result.duration_seconds}s")
print(f"Platform: {result.platform_used}")
print(f"Persona: {result.persona_used}")

# Check execution log for errors
if "ERROR" in result.execution_log:
    print("\nErrors found in log:")
    for line in result.execution_log.split('\n'):
        if "ERROR" in line:
            print(f"  {line}")
```

### Validate Environment

```python
from amplihack.meta_delegation import validate_environment

# Check if system is ready for meta-delegation
issues = validate_environment()

if issues:
    print("Environment issues detected:")
    for issue in issues:
        print(f"  ⚠ {issue}")
else:
    print("✓ Environment ready")
```

---

## Performance Tuning

### Optimize for Speed

```python
result = run_meta_delegation(
    goal="Quick implementation needed",
    success_criteria="Basic working code",
    persona_type="junior_dev",  # Fastest persona
    timeout_minutes=15,          # Shorter timeout
    enable_scenarios=False       # Skip scenario generation
)
```

### Optimize for Quality

```python
result = run_meta_delegation(
    goal="Production-ready feature",
    success_criteria="Comprehensive tests, documentation, edge cases handled",
    persona_type="qa_engineer",  # Most thorough persona
    timeout_minutes=60,          # More time allowed
    enable_scenarios=True        # Generate test scenarios
)
```

---

## Getting Help

### Collect Diagnostic Information

```python
result = run_meta_delegation(...)

# Save diagnostic bundle
diagnostic_info = {
    "status": result.status,
    "score": result.success_score,
    "persona": result.persona_used,
    "platform": result.platform_used,
    "duration": result.duration_seconds,
    "evidence_count": len(result.evidence),
    "evidence_types": list(set(e.type for e in result.evidence)),
    "log_excerpt": result.execution_log[-1000:]  # Last 1000 chars
}

import json
with open("diagnostic_report.json", "w") as f:
    json.dump(diagnostic_info, f, indent=2)

print("Diagnostic report saved to: diagnostic_report.json")
```

### Report Issues

When reporting issues, include:

1. **Environment**: Python version, OS, platform version
2. **Goal and Criteria**: What you were trying to do
3. **Actual Result**: Status, score, evidence collected
4. **Expected Result**: What you expected
5. **Logs**: Execution log (or excerpt)
6. **Diagnostic Report**: Output from diagnostic info above

---

## Related Documentation

- [Tutorial](./tutorial.md) - Learn the basics
- [How-To Guide](./howto.md) - Common tasks
- [Reference](./reference.md) - Complete API
- [Concepts](./concepts.md) - Architecture details

---

**Status**: [PLANNED - Implementation Pending]

This troubleshooting guide describes solutions for the meta-delegation system once implemented.
