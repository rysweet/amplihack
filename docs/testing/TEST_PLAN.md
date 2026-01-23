# PM Label-Triggered Delegation - Test Plan

## Overview

This document describes the testing approach for the `pm:delegate`
label-triggered workflow.

**Feature**: GitHub Actions workflow that triggers PM Architect delegation when
`pm:delegate` label is added to an issue or PR.

**Issue**: #1523

## Components

1. **Workflow File**: `.github/workflows/pm-label-delegate.yml`
2. **Delegation Script**:
   `~/.amplihack/.claude/skills/pm-architect/scripts/delegate_response.py`
3. **Label**: `pm:delegate` (will be created if doesn't exist)

## Test Strategy

Since GitHub Actions can only be fully tested in the CI environment, testing
consists of:

1. **Pre-commit Validation** (Completed)
2. **Manual Testing** (After merge)
3. **Integration Testing** (In production)

## Pre-commit Validation ✅

**Status**: PASSED

Validated files:

- `.github/workflows/pm-label-delegate.yml` - YAML syntax valid
- `~/.amplihack/.claude/skills/pm-architect/scripts/delegate_response.py` - Python formatting
  and type checking passed

## Manual Testing Plan

### Test 1: Issue Label Trigger

**Objective**: Verify workflow triggers on issue labeling

**Steps**:

1. Create a test issue with a simple question (e.g., "What is the project
   structure?")
2. Add the `pm:delegate` label to the issue
3. Wait for workflow to complete (check Actions tab)
4. Verify comment is posted with PM Architect response

**Expected Result**:

- Workflow runs successfully
- Comment posted within 5-10 minutes
- Response is relevant and helpful
- Response formatted correctly with header/footer

**Success Criteria**:

- ✅ Workflow completes without errors
- ✅ Comment posted to issue
- ✅ Response quality is reasonable
- ✅ No secrets exposed in logs

### Test 2: PR Label Trigger

**Objective**: Verify workflow triggers on PR labeling

**Steps**:

1. Create a test PR (can be trivial change)
2. Add description asking for review feedback
3. Add the `pm:delegate` label to the PR
4. Wait for workflow to complete
5. Verify comment is posted with PM Architect analysis

**Expected Result**:

- Workflow runs successfully
- Comment posted within 5-10 minutes
- Response analyzes PR appropriately
- Response formatted correctly

**Success Criteria**:

- ✅ Workflow completes without errors
- ✅ Comment posted to PR
- ✅ Response addresses PR context
- ✅ No secrets exposed in logs

### Test 3: Error Handling

**Objective**: Verify graceful error handling

**Steps**:

1. Create issue with extremely long body (>10KB text)
2. Add `pm:delegate` label
3. Verify workflow handles large input gracefully

**Expected Result**:

- Workflow either succeeds or posts error comment
- No workflow crash or timeout
- Error message is helpful if failure occurs

**Success Criteria**:

- ✅ Workflow doesn't crash
- ✅ Error message posted if failure
- ✅ No secrets in error output

### Test 4: Multiple Labels

**Objective**: Verify selective triggering

**Steps**:

1. Create issue
2. Add multiple labels including `pm:delegate`
3. Verify workflow triggers only for `pm:delegate`
4. Remove and re-add `pm:delegate`
5. Verify workflow triggers again

**Expected Result**:

- Workflow only triggers on `pm:delegate` label addition
- Works with other labels present
- Can be re-triggered by removing and re-adding label

## Security Testing

### Security Test 1: API Key Masking

**Check**: Review workflow logs to ensure API key never appears

**Steps**:

1. Run workflow on test issue
2. Download workflow logs
3. Search for any occurrence of API key or patterns that look like keys

**Expected**: No API keys visible in any log output

### Security Test 2: User Input Sanitization

**Check**: Verify malicious user input doesn't break workflow

**Steps**:

1. Create issue with shell-injection-like content (e.g., `$(whoami)`)
2. Add `pm:delegate` label
3. Verify workflow handles input safely

**Expected**: Input treated as literal text, no code execution

### Security Test 3: Permission Boundaries

**Check**: Verify workflow has minimal required permissions

**Review**:

- Workflow has read-only access to repo contents
- Workflow can only write comments (not code changes)
- No elevated permissions granted

**Expected**: Permissions match specification in workflow file

## Performance Testing

### Performance Test 1: Response Time

**Objective**: Measure typical response time

**Steps**:

1. Add `pm:delegate` label to test issue
2. Note timestamp of label addition
3. Note timestamp of response comment
4. Calculate duration

**Expected**: Response within 5-10 minutes for simple queries

### Performance Test 2: Timeout Handling

**Objective**: Verify 30-minute timeout works

**Steps**:

1. (If possible) create scenario that causes long execution
2. Verify workflow terminates at 30-minute mark
3. Verify timeout error is reported

**Expected**: Workflow respects timeout, reports timeout error

## Integration Testing

### Integration Test 1: With Existing PM Workflows

**Objective**: Verify no conflicts with other PM workflows

**Steps**:

1. Have multiple PM workflows active (daily status, roadmap review, triage)
2. Trigger `pm:delegate` workflow
3. Verify all workflows coexist without issues

**Expected**: No workflow conflicts or resource contention

### Integration Test 2: Auto Mode Integration

**Objective**: Verify auto mode spawns correctly

**Steps**:

1. Check `~/.amplihack/.claude/runtime/logs/` for auto mode session logs
2. Verify logs are created when delegation runs
3. Verify logs contain expected content

**Expected**: Auto mode logs created in correct location

## Test Schedule

1. **Immediate** (PR review phase):
   - Security review of workflow file
   - Code review of delegation script
   - Pre-commit validation (DONE)

2. **After PR Merge**:
   - Test 1: Issue label trigger
   - Test 2: PR label trigger
   - Security Test 1-3

3. **Within 24 Hours of Merge**:
   - Test 3: Error handling
   - Test 4: Multiple labels
   - Performance Test 1

4. **Within 1 Week of Merge**:
   - Integration Test 1-2
   - Performance Test 2 (if applicable)

## Success Metrics

Overall feature is successful if:

- ✅ **Reliability**: 95%+ of triggers result in successful response
- ✅ **Security**: No secrets exposed in any logs
- ✅ **Performance**: 90%+ of responses within 10 minutes
- ✅ **Quality**: Responses are relevant and actionable
- ✅ **Stability**: No workflow crashes or hangs

## Rollback Plan

If critical issues discovered:

1. Disable workflow by removing trigger events from YAML
2. Push emergency fix
3. Re-enable after verification

Alternative: Remove `pm:delegate` label from repository to prevent triggering

## Notes

- GitHub Actions cannot be tested locally (no act or similar tool reliable for
  this)
- Real-world testing is required after merge
- Workflow will use actual API credits during testing
- Consider creating test repository for validation before production use

## Sign-off

- [ ] Pre-commit validation passed
- [ ] Security review completed
- [ ] Code review completed
- [ ] Test plan reviewed and approved
- [ ] Ready for merge and testing
