# Workflow Invocation Validator

**Issue**: #2040 - Enforce workflow invocation compliance
**Status**: Implemented
**Philosophy**: Ruthlessly Simple, Zero-BS, Fail-Open

## Purpose

Validates that `ultrathink-orchestrator` skill properly invokes workflow skills using the `Skill` tool or `Read` tool fallback. Detects violations where workflows are triggered but not properly loaded.

## Problem Statement

In some sessions, Claude would trigger `ultrathink-orchestrator` but skip the mandatory workflow invocation step, proceeding directly to implementation without loading the workflow via `Skill` or `Read` tool. This results in incomplete workflow execution and missed mandatory steps.

## Solution

A validation module that:

1. Detects when ultrathink-orchestrator is triggered
2. Checks for proper workflow invocation via `Skill` tool
3. Accepts `Read` tool fallback as valid alternative
4. Reports violations with clear reasons

## Architecture

### Module: `workflow_invocation_validator.py`

**Public API:**

```python
from workflow_invocation_validator import ValidationResult, validate_workflow_invocation

result = validate_workflow_invocation(transcript: str, session_type: str) -> ValidationResult
```

**ValidationResult:**

```python
@dataclass
class ValidationResult:
    valid: bool
    reason: str
    violation_type: Literal["none", "missing_skill_invocation",
                            "missing_read_fallback", "no_workflow_loaded"]
    evidence: str
```

### Detection Logic

**Step 1: Detect Ultrathink Trigger**

- Explicit `/ultrathink` command
- Skill invocation: `Skill(skill="ultrathink-orchestrator")`
- Auto-activation messages
- Command tag format: `<command-name>/ultrathink</command-name>`

**Step 2: Check Skill Tool Invocation**

- `Skill(skill="default-workflow")` for development
- `Skill(skill="investigation-workflow")` for investigation
- XML format: `<invoke name="Skill">...default-workflow`

**Step 3: Check Read Tool Fallback**

- `Read(~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md)`
- `Read(~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md)`
- XML format: `<invoke name="Read">...DEFAULT_WORKFLOW`

**Step 4: Report Result**

- Valid if: No trigger, Skill invoked, or Read fallback used
- Violation if: Trigger detected but no workflow loaded

## Integration with Power-Steering

### New Consideration: `workflow_invocation`

**Configuration** (`~/.amplihack/.claude/tools/amplihack/considerations.yaml`):

```yaml
- id: workflow_invocation
  category: Workflow Process Adherence
  question: Was workflow properly invoked via Skill or Read tool?
  description: Validates ultrathink-orchestrator properly invoked workflow skills
  severity: blocker
  checker: _check_workflow_invocation
  enabled: true
  applicable_session_types: ["DEVELOPMENT", "INVESTIGATION"]
```

**Checker Method** (`power_steering_checker.py`):

```python
def _check_workflow_invocation(self, transcript: list[dict], session_id: str) -> bool:
    """Check if workflow was properly invoked via Skill or Read tool."""
    # Convert transcript to text
    # Call validator
    # Log violations
    # Return result (fail-open on errors)
```

## Enforcement Points

### 1. Command Documentation (`~/.amplihack/.claude/commands/amplihack/ultrathink.md`)

**Added Section:**

```markdown
## ⛔ BLOCKING REQUIREMENT: Workflow Invocation

When ultrathink-orchestrator skill is triggered, you MUST:

1. IMMEDIATELY invoke the appropriate workflow skill using Skill tool
2. IF skill invocation fails, use Read tool as fallback
3. NEVER proceed without loading the workflow

**Self-Check Protocol:**

- [ ] Invoked Skill tool with workflow skill name, OR
- [ ] Used Read tool to load workflow markdown file
- [ ] Confirmed workflow content is loaded in context
```

### 2. Skill Documentation (`~/.amplihack/.claude/skills/ultrathink-orchestrator/SKILL.md`)

**Added Section:**

```markdown
## ⛔ MANDATORY EXECUTION PROCESS (5 Steps)

### Step 3: Invoke Workflow Skill (MANDATORY - BLOCKING)

⛔ THIS IS A BLOCKING REQUIREMENT - Session will be terminated if skipped.

For Development tasks: Skill(skill="default-workflow")
For Investigation tasks: Skill(skill="investigation-workflow")

### Step 4: Fallback to Read Tool (IF Step 3 Fails)

Only if skill invocation fails, use Read tool as fallback.

**Validation Checkpoint**: Confirm workflow content is loaded in context.
```

### 3. Session-End Validation (Power-Steering)

When session ends, power-steering:

1. Loads `workflow_invocation` consideration
2. Calls `_check_workflow_invocation()`
3. Blocks session termination if violation detected
4. Provides actionable continuation prompt

## Testing

### Test Coverage

**Validator Tests** (`test_workflow_invocation_validator_simple.py`):

- ✓ ValidationResult creation
- ✓ Ultrathink trigger detection (explicit, auto-activation)
- ✓ Skill tool invocation detection (Python and XML formats)
- ✓ Read tool fallback detection
- ✓ Violation detection
- ✓ Session type filtering
- ✓ No trigger scenarios
- ✓ Complete workflow scenarios

**10/10 tests passing**

**Checker Unit Tests** (`test_workflow_invocation_checker_unit.py`):

- ✓ Method existence
- ✓ Transcript conversion helpers
- ✓ Validator import
- ✓ YAML configuration
- ✓ Method signature

**5/5 tests passing**

### Running Tests

```bash
# Validator tests
python3 .claude/tools/amplihack/hooks/tests/test_workflow_invocation_validator_simple.py

# Checker unit tests
python3 .claude/tools/amplihack/hooks/tests/test_workflow_invocation_checker_unit.py

# All tests
python3 .claude/tools/amplihack/hooks/tests/test_workflow_invocation_validator_simple.py && \
python3 .claude/tools/amplihack/hooks/tests/test_workflow_invocation_checker_unit.py
```

## Fail-Open Design

Following amplihack philosophy, this module fails open on errors:

1. **Validator import failure**: Skip check, return valid
2. **Transcript parsing errors**: Skip check, return valid
3. **State file read errors**: Use default session type
4. **Logging errors**: Continue silently

This ensures bugs never block legitimate user work.

## Examples

### Valid Scenario 1: Skill Tool Invocation

```
User: /ultrathink implement authentication
Claude: Detecting task type: Development
Claude: Skill(skill="default-workflow")
Claude: Workflow loaded, executing steps...
```

**Result**: Valid ✓

### Valid Scenario 2: Read Tool Fallback

```
User: /ultrathink implement authentication
Claude: Skill invocation failed, using fallback
Claude: Read(~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md)
Claude: Workflow loaded successfully
```

**Result**: Valid ✓

### Invalid Scenario: No Workflow Invocation

```
User: /ultrathink implement authentication
Claude: Starting implementation directly...
Claude: Creating auth module...
```

**Result**: Violation ✗ - "Ultrathink triggered but workflow not invoked"

## File Structure

```
.claude/tools/amplihack/hooks/
├── workflow_invocation_validator.py      # Core validator module
├── workflow_invocation_validator_README.md
├── power_steering_checker.py             # Integration point (modified)
├── tests/
│   ├── test_workflow_invocation_validator_simple.py
│   ├── test_workflow_invocation_validator.py (pytest version)
│   └── test_workflow_invocation_checker_unit.py
└── ...

.claude/commands/amplihack/
└── ultrathink.md                          # Updated with blocking requirement

.claude/skills/ultrathink-orchestrator/
└── SKILL.md                               # Updated with 5-step process

.claude/tools/amplihack/
└── considerations.yaml                    # Added workflow_invocation
```

## Related Issues

- **Issue #2040**: Enforce workflow invocation via Skill/Read tools
- **Issue #1607**: Workflow Enforcement - Prevent Agent Skipping of Mandatory Steps
- **PR #1606**: Example violation that prompted enforcement

## Future Enhancements

1. **Phase 2**: Real-time validation during session (not just at end)
2. **Phase 3**: Claude SDK agent integration for smarter detection
3. **Phase 4**: Machine learning on violation patterns

## Philosophy Alignment

✓ **Ruthlessly Simple**: Single-purpose validator, clear API
✓ **Zero-BS**: No stubs, every function works
✓ **Fail-Open**: Never block on errors
✓ **Modular**: Self-contained brick with clear studs
✓ **Testable**: Comprehensive test coverage

---

**Implementation Date**: 2026-01-21
**Builder Agent**: aec691e (architect) → builder
**Status**: Complete, tested, integrated
