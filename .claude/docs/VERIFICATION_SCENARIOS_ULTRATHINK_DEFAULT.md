# Verification Scenarios: Ultrathink Default Behavior

## Purpose

This document defines comprehensive behavioral verification scenarios for testing Issue #1942: Making ultrathink-orchestrator the default behavior for development and investigation tasks.

## Feature Summary

**Feature**: Ultrathink-orchestrator as Default Behavior
**Version**: 2.0.0
**Implementation**: Documentation-driven (no code changes)

**Expected Behavior**:
| Task Type | Claude's Action |
|-----------|----------------|
| Q&A | Responds directly (no orchestration) |
| Operations | Responds directly (no orchestration) |
| Investigation | Invokes /ultrathink automatically |
| Development | Invokes /ultrathink automatically |

## Verification Scenarios

### Scenario 1: Q&A Task - Direct Response Expected

**Objective**: Verify Claude responds directly to simple Q&A questions without invoking ultrathink

**Test Input**:

```
User: "What is the amplihack philosophy?"
```

**Expected Behavior**:

- Claude reads .claude/context/PHILOSOPHY.md
- Claude provides direct answer
- NO ultrathink invocation
- NO workflow file reading
- Response completes in single turn

**Success Criteria**:

- ✅ Direct answer provided
- ✅ No ultrathink orchestration triggered
- ✅ No workflow files read
- ✅ Response time < 30 seconds
- ✅ User gets immediate answer

**Verification Method**:

- Monitor tool calls for absence of Skill(ultrathink-orchestrator)
- Monitor for absence of workflow file reads
- Confirm response provides answer directly

---

### Scenario 2: Operations Task - Direct Execution Expected

**Objective**: Verify Claude executes operations tasks directly without orchestration

**Test Input**:

```
User: "Delete all .pyc files in the project"
```

**Expected Behavior**:

- Claude uses Bash tool with find/rm commands
- Direct execution without ultrathink
- NO workflow invocation
- Completes operation immediately

**Success Criteria**:

- ✅ Operation executed directly
- ✅ No ultrathink invocation
- ✅ No workflow overhead
- ✅ Task completes efficiently

**Verification Method**:

- Monitor for direct Bash tool usage
- Confirm no Skill(ultrathink-orchestrator) call
- Verify efficient execution pattern

---

### Scenario 3: Investigation Task - Ultrathink Invoked

**Objective**: Verify Claude automatically invokes ultrathink for investigation tasks

**Test Input**:

```
User: "Investigate how the memory system works in amplihack"
```

**Expected Behavior**:

- Claude detects investigation keywords: "investigate", "how", "works"
- Claude automatically invokes Skill(ultrathink-orchestrator)
- Ultrathink reads INVESTIGATION_WORKFLOW.md
- Systematic 6-phase investigation executes
- Knowledge-archaeologist agent deployed
- Findings documented comprehensively

**Success Criteria**:

- ✅ Ultrathink invoked automatically
- ✅ INVESTIGATION_WORKFLOW.md followed
- ✅ Systematic exploration conducted
- ✅ Multiple agents deployed for deep analysis
- ✅ Final report provided with findings

**Verification Method**:

- Monitor for Skill(ultrathink-orchestrator) invocation
- Confirm INVESTIGATION_WORKFLOW.md read
- Verify knowledge-archaeologist agent usage
- Check for comprehensive investigation report

---

### Scenario 4: Development Task - Ultrathink Invoked

**Objective**: Verify Claude automatically invokes ultrathink for development tasks

**Test Input**:

```
User: "Add a feature to export memory graphs as PNG images"
```

**Expected Behavior**:

- Claude detects development keywords: "add", "feature"
- Claude automatically invokes Skill(ultrathink-orchestrator)
- Ultrathink reads DEFAULT_WORKFLOW.md
- All 22 workflow steps tracked in TodoWrite
- Systematic development process followed
- PR created with proper testing

**Success Criteria**:

- ✅ Ultrathink invoked automatically
- ✅ DEFAULT_WORKFLOW.md followed
- ✅ All 22 steps tracked
- ✅ Agents deployed at each step (architect, builder, reviewer)
- ✅ PR created and mergeable

**Verification Method**:

- Monitor for Skill(ultrathink-orchestrator) invocation
- Confirm DEFAULT_WORKFLOW.md read
- Verify TodoWrite shows all 22 steps
- Check agent usage (architect, builder, reviewer, tester)
- Verify PR creation with all required steps

---

### Scenario 5: Bypass with Explicit Command

**Objective**: Verify explicit commands bypass ultrathink and execute directly

**Test Input**:

```
User: "/fix import errors in the codebase"
```

**Expected Behavior**:

- Claude recognizes explicit /fix command
- Fix-agent executes directly
- NO ultrathink invocation
- Fast, focused fix workflow used

**Success Criteria**:

- ✅ /fix command recognized
- ✅ No ultrathink invocation
- ✅ Fix-agent executes directly
- ✅ Efficient targeted fix completed

**Verification Method**:

- Monitor for direct fix-agent usage
- Confirm no Skill(ultrathink-orchestrator) call
- Verify fast execution pattern

---

### Scenario 6: Bypass with "Without Ultrathink" Request

**Objective**: Verify explicit bypass request prevents ultrathink invocation

**Test Input**:

```
User: "Implement user authentication without ultrathink"
```

**Expected Behavior**:

- Claude recognizes "without ultrathink" override
- Direct implementation without orchestration
- No workflow file reading
- User request honored

**Success Criteria**:

- ✅ Bypass request recognized
- ✅ No ultrathink invocation
- ✅ Direct implementation executed
- ✅ User control preserved

**Verification Method**:

- Monitor for absence of Skill(ultrathink-orchestrator)
- Confirm direct implementation approach
- Verify user override respected

---

### Scenario 7: Hybrid Task - Investigation + Development

**Objective**: Verify Claude handles tasks with both investigation and development keywords appropriately

**Test Input**:

```
User: "Investigate the authentication system and fix the session timeout bug"
```

**Expected Behavior**:

- Claude detects both investigation and development keywords
- Claude invokes ultrathink
- Investigation phase executes first (INVESTIGATION_WORKFLOW)
- Development phase follows (DEFAULT_WORKFLOW)
- Systematic hybrid workflow

**Success Criteria**:

- ✅ Ultrathink invoked for hybrid task
- ✅ Investigation conducted first
- ✅ Development work follows investigation
- ✅ Both phases tracked systematically
- ✅ Final deliverable includes both understanding and fix

**Verification Method**:

- Monitor for Skill(ultrathink-orchestrator) invocation
- Verify both workflows referenced
- Confirm sequential execution (investigation → development)
- Check deliverables include both investigation report and bug fix

---

## Testing Methodology

### Manual Testing Process

1. **Fresh Session**: Start new Claude Code session with PR branch checked out
2. **Clear Context**: Ensure no prior context influences behavior
3. **Input Test Scenario**: Provide exact test input to Claude
4. **Observe Behavior**: Monitor tool calls, file reads, agent invocations
5. **Verify Criteria**: Check all success criteria met
6. **Document Results**: Record actual vs expected behavior

### Automated Testing (Future)

Consider implementing automated behavioral tests using:

- Claude Code SDK test framework
- Behavioral assertion checking
- Tool call pattern matching
- Response time measurement

### Test Environment

**Requirements**:

- Fresh Claude Code session
- PR branch checked out: `feat/issue-1942-ultrathink-default`
- No stale context from previous sessions
- Access to all referenced files (PHILOSOPHY.md, workflow files)

## Success Metrics

**Feature considered successful when**:

- All 7 scenarios pass verification
- No false positives (Q&A/Operations don't trigger ultrathink)
- No false negatives (Investigation/Development do trigger ultrathink)
- Bypass mechanisms work reliably
- User experience improved (appropriate automation, preserved control)

## Known Limitations

1. **Documentation-Driven Implementation**: Relies on Claude following documentation guidance
2. **No Code Enforcement**: No runtime checks enforce behavior
3. **Model Variability**: Different Claude models may interpret guidance differently
4. **Context Sensitivity**: Heavy context may influence classification

## Revision History

- **v1.0.0** (2026-01-16): Initial verification scenarios created for PR 1943
  - 7 comprehensive scenarios defined
  - Testing methodology documented
  - Success criteria established
