# Test Execution Guide: Ultrathink Default Behavior

## Purpose

This guide provides step-by-step instructions for executing real-world behavioral tests for the ultrathink default behavior feature (Issue #1942, PR #1943).

## Prerequisites

- PR #1943 has been merged to main
- Fresh Claude Code installation or session
- Access to amplihack repository

## Test Execution Steps

### Setup Phase

1. **Start Fresh Session**
   ```bash
   # Exit any existing Claude Code sessions
   exit

   # Start new Claude Code session
   claude-code
   ```

2. **Verify Correct Branch**
   ```bash
   # Ensure you're on main with the merged PR
   git checkout main
   git pull origin main

   # Verify the changes are present
   grep -A 5 "Default Behavior" .claude/commands/amplihack/ultrathink.md
   grep -A 10 "Workflow Execution" CLAUDE.md
   ```

3. **Clear Context**
   - Start with empty conversation
   - No prior context that might influence classification

### Test Execution

#### Test 1: Q&A Task (Expected: Direct Response)

**Input to Claude**:
```
What is the amplihack philosophy?
```

**What to Observe**:
- [ ] Claude provides direct answer
- [ ] No ultrathink invocation seen
- [ ] No workflow file reads
- [ ] Quick response (< 30 seconds)

**How to Verify**:
- Watch for absence of "Reading .claude/workflow/" messages
- Watch for absence of Skill(ultrathink-orchestrator) invocation
- Verify answer is direct and immediate

**Expected Result**: ✅ PASS - Direct answer without orchestration

---

#### Test 2: Operations Task (Expected: Direct Execution)

**Input to Claude**:
```
List all Python files in the .claude directory
```

**What to Observe**:
- [ ] Claude executes bash command directly
- [ ] No ultrathink invocation
- [ ] No workflow overhead
- [ ] Immediate execution

**How to Verify**:
- Watch for direct Bash tool usage
- Verify no workflow reading
- Confirm efficient execution

**Expected Result**: ✅ PASS - Direct execution without orchestration

---

#### Test 3: Investigation Task (Expected: Ultrathink Invoked)

**Input to Claude**:
```
Investigate how the agent delegation system works in amplihack
```

**What to Observe**:
- [ ] Claude automatically invokes ultrathink
- [ ] Message: "Reading .claude/workflow/INVESTIGATION_WORKFLOW.md"
- [ ] Systematic investigation phases begin
- [ ] TodoWrite shows investigation steps
- [ ] Multiple agents deployed

**How to Verify**:
- Watch for Skill(ultrathink-orchestrator) or explicit /ultrathink invocation
- Verify INVESTIGATION_WORKFLOW.md is read
- Confirm systematic exploration
- Check for agent usage (knowledge-archaeologist, analyzer)

**Expected Result**: ✅ PASS - Ultrathink invoked for investigation

---

#### Test 4: Development Task (Expected: Ultrathink Invoked)

**Input to Claude**:
```
Add a new command to list all available workflows
```

**What to Observe**:
- [ ] Claude automatically invokes ultrathink
- [ ] Message: "Reading .claude/workflow/DEFAULT_WORKFLOW.md"
- [ ] TodoWrite shows all 22 workflow steps
- [ ] Systematic development process begins
- [ ] Agents deployed (prompt-writer, architect, builder)

**How to Verify**:
- Watch for Skill(ultrathink-orchestrator) invocation
- Verify DEFAULT_WORKFLOW.md is read
- Confirm TodoWrite has 22 steps (Step 0 through Step 21)
- Check agent usage throughout workflow

**Expected Result**: ✅ PASS - Ultrathink invoked for development

---

#### Test 5: Bypass with Explicit Command

**Input to Claude**:
```
/fix import errors in src/memory/
```

**What to Observe**:
- [ ] Claude recognizes /fix command
- [ ] No ultrathink invocation
- [ ] Fix-agent executes directly
- [ ] Fast, focused fix pattern

**How to Verify**:
- Watch for absence of workflow reads
- Verify direct fix-agent usage
- Confirm efficient execution

**Expected Result**: ✅ PASS - Explicit command bypasses ultrathink

---

#### Test 6: Bypass with "Without Ultrathink"

**Input to Claude**:
```
Implement a helper function for file validation without ultrathink
```

**What to Observe**:
- [ ] Claude recognizes override request
- [ ] No ultrathink invocation
- [ ] Direct implementation
- [ ] No workflow reading

**How to Verify**:
- Watch for absence of Skill(ultrathink-orchestrator)
- Verify direct implementation approach
- Confirm user control respected

**Expected Result**: ✅ PASS - User override respected

---

#### Test 7: Hybrid Task

**Input to Claude**:
```
Investigate the workflow system and add support for workflow templates
```

**What to Observe**:
- [ ] Claude invokes ultrathink
- [ ] Investigation phase first
- [ ] Development phase follows
- [ ] Both phases tracked systematically

**How to Verify**:
- Watch for ultrathink invocation
- Verify both investigation and development keywords detected
- Confirm sequential execution

**Expected Result**: ✅ PASS - Hybrid task handled correctly

---

## Results Documentation

### Test Results Template

```markdown
# Ultrathink Default Behavior Test Results

**Test Date**: [Date]
**Tester**: [Name]
**Branch**: main (post-merge of PR #1943)
**Claude Code Version**: [Version]

## Test Results Summary

| Test # | Scenario | Expected | Actual | Status | Notes |
|--------|----------|----------|--------|--------|-------|
| 1 | Q&A Task | Direct | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 2 | Operations | Direct | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 3 | Investigation | Ultrathink | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 4 | Development | Ultrathink | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 5 | Bypass Command | Direct | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 6 | Bypass Request | Direct | [Actual behavior] | [PASS/FAIL] | [Notes] |
| 7 | Hybrid Task | Ultrathink | [Actual behavior] | [PASS/FAIL] | [Notes] |

**Overall Result**: [X/7 tests passed]

## Detailed Findings

### Test 1: Q&A Task
[Detailed observations]

### Test 2: Operations Task
[Detailed observations]

[Continue for all tests...]

## Issues Found

[Document any issues, unexpected behavior, or deviations]

## Recommendations

[Suggest any improvements or fixes needed]
```

## Success Criteria

**Feature is VERIFIED when**:
- All 7 tests pass
- No false positives (Q&A/Operations don't trigger ultrathink)
- No false negatives (Investigation/Development do trigger ultrathink)
- Bypass mechanisms work reliably
- User experience is improved

## Troubleshooting

### Issue: Claude doesn't invoke ultrathink for development tasks

**Possible Causes**:
- Changes not merged to main
- Stale Claude Code cache
- Task description doesn't contain development keywords

**Resolution**:
1. Verify CLAUDE.md has "Workflow Execution" section
2. Verify ultrathink.md has "Default Behavior" section
3. Restart Claude Code session
4. Try clearer development keywords: "implement", "add feature", "build"

### Issue: Claude invokes ultrathink for simple questions

**Possible Causes**:
- Question contains investigation/development keywords
- Classification logic too aggressive

**Resolution**:
1. Use clearer Q&A phrasing: "what is", "explain briefly"
2. Verify task classification keywords in CLAUDE.md
3. Document false positive for further refinement

## Post-Test Actions

1. **Document Results**: Fill out test results template
2. **Report Issues**: Create GitHub issues for any failures
3. **Update Documentation**: Refine classification keywords if needed
4. **Share Findings**: Post test results in PR #1943 comments

## Continuous Verification

**Recommendation**: Run these tests periodically to ensure behavior remains consistent:
- After major Claude Code updates
- After changes to CLAUDE.md or workflow files
- When onboarding new team members (as training verification)

## Notes for Testers

- **Be Patient**: Ultrathink orchestration takes longer (this is expected)
- **Watch for Patterns**: Look for consistent tool call patterns
- **Document Everything**: Even unexpected behavior is valuable data
- **Fresh Context**: Each test should ideally start in fresh conversation
- **Clear Input**: Use exact test inputs for consistency

## Revision History

- **v1.0.0** (2026-01-16): Initial test execution guide created
  - 7 test scenarios with step-by-step instructions
  - Results documentation template
  - Troubleshooting guide
  - Success criteria defined
