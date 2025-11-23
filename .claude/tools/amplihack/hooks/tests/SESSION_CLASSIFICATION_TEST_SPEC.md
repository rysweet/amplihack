# Session Classification Test Specification

## Test Philosophy

### Test-Driven Development Approach

All tests are written to **FAIL FIRST**, defining expected behavior before implementation. This ensures:

- Clear requirements definition
- No over-engineering
- Implementation guided by tests
- Confidence that tests actually verify behavior

### Testing Principles

1. **Behavior over Implementation** - Tests verify what the system does, not how it does it
2. **Clear Test Names** - Test names describe the scenario being tested
3. **Single Assertion Focus** - Each test validates one specific behavior
4. **Fail-Open Philosophy** - Edge cases default to safe behavior (INFORMATIONAL)
5. **No Test Stubs** - All tests fully implemented and executable

## Test Structure

### Test Classes

#### 1. TestSessionClassification

Tests core session type detection logic.

**Test Categories**:

- Basic session type detection (4 types × 3 scenarios = 12 tests)
- Selective consideration application (4 types × 2 scenarios = 8 tests)
- Edge cases and boundaries (5 tests)
- Environment overrides (2 tests)
- Backward compatibility (2 tests)
- Heuristic validation (4 tests)

#### 2. TestConsiderationMapping

Tests consideration-to-session-type mapping logic.

**Test Categories**:

- Consideration filtering per session type (4 tests)
- Specific consideration inclusion/exclusion (integrated)

## Test Data Strategy

### Transcript Fixtures

Tests use minimal transcript structures that represent realistic scenarios:

```python
# DEVELOPMENT session
[
    {"type": "user", "message": {"content": "Add feature X"}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Write", "input": {"file_path": "src/new.py"}}
    ]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "pytest tests/"}}
    ]}},
]

# INFORMATIONAL session
[
    {"type": "user", "message": {"content": "What skills are available?"}},
    {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "I have the following skills..."}
    ]}},
]
```

### Test Data Principles

- **Minimal** - Only include necessary messages
- **Realistic** - Match actual transcript format
- **Focused** - Each test has specific focus
- **Reusable** - Common patterns extracted (but kept inline for clarity)

## Session Type Detection Tests

### DEVELOPMENT Session Tests

#### test_detect_development_session_with_pr_and_ci

**Scenario**: Complete development workflow with PR and CI
**Expected**: Session type = "DEVELOPMENT"
**Key Indicators**:

- Write tool on code file (src/auth.py)
- Test execution (pytest)
- PR creation (gh pr create)

#### test_detect_development_session_without_pr

**Scenario**: Code changes and tests but no PR yet
**Expected**: Session type = "DEVELOPMENT"
**Key Indicators**:

- Edit tool on code file
- Test execution
- No PR operations

#### test_mixed_session_prioritizes_development

**Scenario**: Session starts as Q&A, transitions to development
**Expected**: Session type = "DEVELOPMENT"
**Rationale**: Development indicators override informational

### INFORMATIONAL Session Tests

#### test_detect_informational_session_qa_only

**Scenario**: Pure Q&A with no tool usage
**Expected**: Session type = "INFORMATIONAL"
**Key Indicators**:

- Question content
- Text-only responses
- No tool operations

#### test_detect_informational_session_with_read_tools

**Scenario**: Q&A with Read tools but no modifications
**Expected**: Session type = "INFORMATIONAL"
**Key Indicators**:

- Read tool usage
- No Write/Edit operations
- Explanatory content

#### test_single_read_tool_is_informational

**Scenario**: Single file read with no follow-up
**Expected**: Session type = "INFORMATIONAL"
**Rationale**: Single read is likely informational query

### MAINTENANCE Session Tests

#### test_detect_maintenance_session_docs_and_config

**Scenario**: Documentation and configuration updates only
**Expected**: Session type = "MAINTENANCE"
**Key Indicators**:

- Write/Edit on .md files
- Write/Edit on .yml files
- No code file changes

#### test_git_commit_cleanup_is_maintenance

**Scenario**: Git commits without code changes
**Expected**: Session type = "MAINTENANCE"
**Key Indicators**:

- Git operations
- No Write/Edit on code files
- Cleanup keywords

### INVESTIGATION Session Tests

#### test_detect_investigation_session_read_only

**Scenario**: Multiple read/search operations with analysis
**Expected**: Session type = "INVESTIGATION"
**Key Indicators**:

- Multiple Read operations
- Grep/search tools
- No Write/Edit operations
- Analysis keywords

#### test_multiple_reads_with_analysis_is_investigation

**Scenario**: Pattern searching across multiple files
**Expected**: Session type = "INVESTIGATION"
**Key Indicators**:

- Grep operations
- Multiple Read operations
- No modifications

## Selective Consideration Application Tests

### Design Goal

Different session types should have different considerations applied to prevent false positives.

### Test Pattern

```python
def test_<session_type>_session_skips_<consideration_category>_checks(self):
    # 1. Create transcript for session type
    # 2. Run power steering check
    # 3. Verify decision = "approve"
    # 4. Verify specific considerations not blocking
```

### Key Tests

#### test_informational_session_skips_pr_checks

**Validates**: PR checks (unrelated_changes, pr_description, review_responses) not applied
**Why**: INFORMATIONAL sessions don't have PRs

#### test_informational_session_skips_ci_checks

**Validates**: CI checks (ci_status, branch_rebase) not applied
**Why**: INFORMATIONAL sessions don't push code

#### test_informational_session_skips_testing_checks

**Validates**: Testing checks (local_testing, interactive_testing) not applied
**Why**: INFORMATIONAL sessions don't modify code

#### test_development_session_applies_all_checks

**Validates**: All considerations active for DEVELOPMENT
**Why**: Development sessions need full workflow validation

## Edge Cases and Boundary Tests

### Empty Transcript

**Test**: `test_empty_transcript_defaults_to_informational`
**Behavior**: Fail-open to INFORMATIONAL
**Rationale**: Safe default prevents blocking empty sessions

### Single Tool Operation

**Test**: `test_single_read_tool_is_informational`
**Behavior**: Classify as INFORMATIONAL
**Rationale**: Single read likely informational query

### Mixed Sessions

**Test**: `test_mixed_session_prioritizes_development`
**Behavior**: Development indicators take precedence
**Rationale**: Conservative - apply full checks if any development

## Environment Override Tests

### Valid Override

**Test**: `test_environment_override_session_type`
**Setup**: Set AMPLIHACK_SESSION_TYPE=INFORMATIONAL
**Expected**: Detection overridden by environment variable
**Use Case**: User explicitly declares session type

### Invalid Override

**Test**: `test_invalid_environment_override_ignored`
**Setup**: Set AMPLIHACK_SESSION_TYPE=INVALID_TYPE
**Expected**: Fall back to automatic detection
**Rationale**: Fail-safe behavior

## Backward Compatibility Tests

### Missing Method Handling

**Test**: `test_backward_compatibility_no_session_type_method`
**Scenario**: Code without detect_session_type method
**Expected**: No crash, existing behavior maintained
**Rationale**: Phase 1 systems should still work

### Existing Q&A Detection

**Test**: `test_existing_qa_detection_still_works`
**Scenario**: \_is_qa_session method still functions
**Expected**: Returns True for Q&A sessions
**Rationale**: Don't break existing detection

## Heuristics Validation Tests

### Code File Extensions

**Test**: `test_development_indicators_code_file_extensions`
**Validates**: .py, .js, .ts files trigger DEVELOPMENT
**Coverage**: All common code extensions

### Documentation Files

**Test**: `test_maintenance_indicators_doc_files_only`
**Validates**: .md, .txt files trigger MAINTENANCE
**Coverage**: Common documentation formats

### Search Patterns

**Test**: `test_investigation_indicators_grep_patterns`
**Validates**: Multiple Grep operations trigger INVESTIGATION
**Threshold**: 2+ search operations

### Question Density

**Test**: `test_informational_indicators_question_marks`
**Validates**: High question density (>50%) triggers INFORMATIONAL
**Coverage**: Various question patterns

## Consideration Mapping Tests

### Mapping Validation

Tests verify that `get_applicable_considerations()` returns correct subset for each session type.

#### test_get_applicable_considerations_for_development

**Expected**: All considerations returned (full workflow)

#### test_get_applicable_considerations_for_informational

**Expected**: Minimal set (objective_completion, agent_unnecessary_questions)
**Excluded**: PR, CI, testing, workflow checks

#### test_get_applicable_considerations_for_maintenance

**Expected**: Documentation and organization checks
**Excluded**: Testing, CI checks

#### test_get_applicable_considerations_for_investigation

**Expected**: Investigation docs check included
**Excluded**: Workflow, CI, testing checks

## Test Execution Strategy

### Phase 1: Verify Tests Fail

```bash
python3 test_session_classification.py
# Expected: All tests fail with AttributeError (methods don't exist)
```

### Phase 2: Implement Core Detection

Implement `detect_session_type()` method

```bash
python3 test_session_classification.py
# Expected: Detection tests pass, mapping tests still fail
```

### Phase 3: Implement Consideration Mapping

Implement `get_applicable_considerations()` method

```bash
python3 test_session_classification.py
# Expected: All tests pass
```

### Phase 4: Integration Testing

Run alongside existing power steering tests

```bash
python3 test_power_steering_checker.py
python3 test_session_classification.py
# Expected: All tests pass, no regressions
```

## Success Criteria

### Test Metrics

- **31 tests total** (2 test classes)
- **100% pass rate** after implementation
- **0 regressions** in existing tests
- **<1 second** total execution time

### Coverage Metrics

- **4 session types** fully covered
- **21 considerations** mapped correctly
- **5 edge cases** handled
- **2 override mechanisms** validated

### Quality Metrics

- **Clear test names** describing scenarios
- **Single responsibility** per test
- **No test dependencies** (can run in any order)
- **Deterministic results** (no random behavior)

## Known Limitations

### Out of Scope

1. **LLM-based classification** - Future enhancement
2. **Session type transitions** - Mid-session type changes
3. **Confidence scores** - Classification certainty metrics
4. **Performance testing** - Large transcript handling
5. **User learning** - Adaptive classification

### Acceptable Trade-offs

1. **Heuristic-based** - Simple rules over ML
2. **Conservative** - Prefer DEVELOPMENT over INFORMATIONAL when ambiguous
3. **Static mapping** - Fixed consideration sets per type
4. **No feedback loop** - No learning from user corrections

## Test Maintenance

### When to Update Tests

- New session types added
- New considerations created
- Classification logic changed
- Edge cases discovered

### How to Add Tests

1. Identify scenario
2. Write failing test
3. Verify test fails
4. Implement feature
5. Verify test passes
6. Update this document

## Related Documentation

- `/Users/ryan/src/MicrosoftHackathon2025-AgenticCoding/worktrees/feat/issue-1492-power-steering-session-classification/.claude/tools/amplihack/hooks/tests/TEST_COVERAGE_ANALYSIS.md` - Coverage details
- Issue #1492 - Original problem statement
- `power_steering_checker.py` - Implementation target
