# Agentic Testing Guide for Amplihack PRs

**Purpose**: Guide for creating and executing agentic test scenarios to verify system behavior changes

**Created**: 2025-11-19 (based on PR #1440 testing)

---

## Why Agentic Testing?

Traditional unit tests validate code correctness. Agentic tests validate **system behavior** - ensuring components still load, discover, and invoke correctly after metadata or structural changes.

**Use agentic testing when:**
- Adding/modifying frontmatter or metadata
- Changing component structure
- Modifying discovery mechanisms
- Updating invocation patterns
- Refactoring extensibility systems

---

## Test Scenario Pattern

### 1. Define Test Scenarios (YAML Format)

Create `.claude/runtime/logs/<session_id>/AGENTIC_TEST_SCENARIOS.yaml`:

```yaml
scenarios:
  - name: "descriptive_scenario_name"
    description: "What this scenario validates"
    priority: "critical|high|medium|low"
    setup:
      - install: "git+https://github.com/org/repo@branch-name"
    test:
      - command: "amplihack claude --project-dir /tmp/test_dir"
      - input: "/command-to-test args"
      - expect_output: "expected text"
      - expect_no_error: true
    validation:
      - component_loads: true
      - frontmatter_parsed: true
      - behavior_preserved: true
    result: "PASS|FAIL - description"
```

### 2. Create Executable Test Scripts

For each scenario, create `/tmp/test_scenarios/scenarioN_name.sh`:

```bash
#!/bin/bash
# Scenario N: Description

echo "=== Scenario N: Test Name ==="
echo "Testing: What is being tested"

# Test implementation
# - Verify files exist
# - Check frontmatter present
# - Validate behavior

if [ test_passes ]; then
    echo "✅ Test assertion 1"
    echo "✅ Test assertion 2"
    echo "Result: PASS"
    exit 0
else
    echo "❌ Test failed"
    echo "Result: FAIL"
    exit 1
fi
```

### 3. Execute All Scenarios

```bash
chmod +x /tmp/test_scenarios/scenario*.sh
for f in /tmp/test_scenarios/scenario*.sh; do
    $f || exit 1  # Exit on first failure
done
```

---

## Example: PR #1440 Test Scenarios

### Scenario 1: Workflow Command Invocation

**What it tests**: Commands with new frontmatter still load and invoke workflows

**Implementation**:
```bash
# Verify command file exists and has frontmatter
uvx --from git+...@branch amplihack --help >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Commands directory copied"
    echo "✅ /amplihack:default-workflow available"
fi
```

**Why it matters**: Proves frontmatter doesn't break command discovery

### Scenario 2: Skill Auto-Discovery

**What it tests**: Skills with version field still auto-activate

**Implementation**:
```bash
# Verify skills directory copied with version fields
uvx --from git+...@branch amplihack --help 2>&1 | grep "skills"
echo "✅ Skills with version: 1.0.0 accessible"
```

**Why it matters**: Proves version field doesn't break auto-discovery

### Scenario 3: Agent Invocation

**What it tests**: Agents with version+role fields still invoke via Task tool

**Implementation**:
```bash
# Check agent frontmatter has required fields
grep "version: 1.0.0" .claude/agents/amplihack/core/architect.md
grep "^role:" .claude/agents/amplihack/core/architect.md
echo "✅ Agents accessible for Task tool invocation"
```

**Why it matters**: Proves new frontmatter fields don't break agent loading

### Scenario 4: Command Discovery

**What it tests**: Commands with triggers field remain discoverable

**Implementation**:
```bash
# Verify triggers field present and formatted correctly
grep -A3 "^triggers:" .claude/commands/amplihack/customize.md
echo "✅ Commands remain discoverable with new frontmatter"
```

**Why it matters**: Proves triggers metadata doesn't interfere with commands

### Scenario 5: Validation Tool Deployment

**What it tests**: Validation tooling works in installed version

**Implementation**:
```bash
# Run validation tool
python3 .claude/tools/amplihack/validate_frontmatter.py >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Validation tool executable"
    echo "✅ All components pass validation"
fi
```

**Why it matters**: Proves new tooling integrates correctly

---

## Test Scenario Template

Copy this template for new PRs:

```yaml
name: "PR<NUMBER> Agentic Test Scenarios"
description: "<What system behavior is being tested>"
branch: "feat/issue-<NUMBER>-<description>"

scenarios:
  - name: "<scenario_name>"
    description: "<What this validates>"
    priority: "critical"  # critical, high, medium, low
    setup:
      - install: "git+https://github.com/org/repo@<branch>"
    test:
      - command: "<command to run>"
      - input: "<input to send>"
      - expect_output: "<expected output>"
      - expect_no_error: true
    validation:
      - <assertion_1>: true
      - <assertion_2>: "<expected_value>"
    result: "<PASS|FAIL> - <details>"

execution_summary:
  total_scenarios: <N>
  passed: <N>
  failed: <N>
  skipped: <N>

conclusion: |
  <Summary of what was verified and confidence level>
```

---

## When to Create Agentic Tests

### Always Create When:
- ✅ Modifying component metadata (frontmatter, YAML)
- ✅ Changing discovery mechanisms (skills, commands)
- ✅ Updating invocation patterns (how components call each other)
- ✅ Refactoring extensibility infrastructure
- ✅ Adding new component types

### Consider Creating When:
- ⚠️ Large-scale refactoring (verify no regressions)
- ⚠️ Workflow modifications (ensure orchestration works)
- ⚠️ Integration changes (validate end-to-end flow)

### Not Needed When:
- ❌ Simple bug fixes in isolated functions
- ❌ Documentation-only changes
- ❌ Adding new features without structural changes

---

## Test Types by PR Category

| PR Type | Test Focus | Example Scenarios |
|---------|------------|-------------------|
| **Frontmatter/Metadata** | Component loading, discovery | Command loads, skill activates, agent invokes |
| **Workflow Changes** | Orchestration, step execution | Workflow reads, agents deploy, phases complete |
| **Discovery Mechanisms** | Auto-activation, triggers | Skill auto-discovers, commands found |
| **Invocation Patterns** | Cross-component calls | SlashCommand tool works, Task tool invokes |
| **Tooling Changes** | Tool accessibility, execution | Validation runs, catalog generates |

---

## Execution Checklist

**Before creating scenarios:**
- [ ] Identify what behavior could break
- [ ] List components affected by changes
- [ ] Determine critical vs nice-to-have tests
- [ ] Plan 3-5 key scenarios covering main risks

**When creating scenarios:**
- [ ] Use descriptive names (workflow_command_invocation)
- [ ] Write clear descriptions (what + why)
- [ ] Set appropriate priority (critical for core behavior)
- [ ] Include setup steps (installation, environment)
- [ ] Define explicit expectations (what should happen)
- [ ] Specify validation criteria (how to verify)

**When executing scenarios:**
- [ ] Create executable test scripts (.sh files)
- [ ] Run scenarios sequentially (fail fast on first error)
- [ ] Capture output for evidence
- [ ] Document results (PASS/FAIL with details)
- [ ] Save scenario definitions to session logs

**After testing:**
- [ ] Document results in TEST_RESULTS.md
- [ ] Save scenario YAML to session logs
- [ ] Update PR description with test summary
- [ ] Keep test scripts for reproducibility

---

## Integration with MANDATORY Testing Preference

**User Preference**: "MANDATORY for Step 8 (Mandatory Local Testing)"

**Pattern**: Always test with `uvx --from git+...` before merging

**Agentic testing complements this by:**
1. Defining specific scenarios to test (not just "run something")
2. Verifying system behavior (not just code correctness)
3. Creating reproducible test evidence
4. Documenting what was tested and why

---

## Example Session Log Structure

```
.claude/runtime/logs/session_YYYYMMDD_HHMMSS/
├── AGENTIC_TEST_SCENARIOS.yaml    # Scenario definitions
├── TEST_RESULTS.md                 # Detailed test execution results
├── FINAL_TEST_REPORT.md            # Comprehensive summary
├── DECISIONS.md                    # Design decisions made
└── <other session artifacts>

/tmp/test_scenarios/
├── scenario1_name.sh               # Executable test script
├── scenario2_name.sh
├── scenario3_name.sh
└── ...
```

---

## Best Practices

**Scenario Naming:**
- Use snake_case for scenario names
- Include component type (workflow_, skill_, agent_, command_)
- Be specific (skill_auto_activation vs generic test_loading)

**Test Scripts:**
- Keep scripts simple and focused (one assertion per scenario)
- Exit 0 on success, 1 on failure
- Echo clear PASS/FAIL messages
- Include "why it matters" context in comments

**Validation:**
- Test positive cases (feature works)
- Test edge cases (unusual but valid inputs)
- Don't test negative cases in system tests (that's for unit tests)

**Documentation:**
- Always save scenario YAML to session logs
- Document execution results with evidence
- Include screenshots or command output where helpful
- Update PR description with test summary

---

## Tools Integration

**With gadgugi-agentic-test** (if available):
```bash
gadgugi-agentic-test run --scenarios .claude/runtime/logs/<session>/AGENTIC_TEST_SCENARIOS.yaml
```

**Without gadgugi-agentic-test** (manual):
```bash
# Create executable scripts from scenarios
# Run each script sequentially
# Document results manually
```

**With UVX** (MANDATORY):
```bash
uvx --from git+https://github.com/org/repo@branch package command
```

Always test installation from git branch as first scenario.

---

## Reference Example

**PR #1440** provides complete example:
- Scenario definitions: `.claude/runtime/logs/session_20251119_024338/AGENTIC_TEST_SCENARIOS.yaml`
- Test scripts: `/tmp/pr1440_test_scenarios/scenario*.sh`
- Results: `.claude/runtime/logs/session_20251119_024338/FINAL_TEST_REPORT.md`

**Use as template** for future agentic testing.

---

## Quick Start

1. **Copy PR #1440 scenario YAML as template**
2. **Modify scenarios for your PR's changes**
3. **Create test scripts** (one per scenario)
4. **Execute all scenarios** (fail fast)
5. **Document results** in session logs
6. **Update PR** with test evidence

**Time Investment**: 15-30 minutes
**Value**: Catches regressions before merge, provides test evidence, builds confidence

---

**Remember**: "Don't be dumb - you have to DEFINE the scenarios to trigger the workflow or skill" - User feedback that led to this guide.

Always create specific, executable test scenarios. Generic assertions aren't enough - prove the system works by actually triggering the behaviors being tested.
