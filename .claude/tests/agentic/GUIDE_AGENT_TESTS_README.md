# Guide Agent Tutorial Testing Suite

Comprehensive test scenarios for the enhanced guide agent tutorial system using gadugi-agentic-test framework.

## Test Scenarios

### Level 1: Basic Tutorial Navigation
**File**: `guide-agent-tutorial-basic.yaml`
**Duration**: ~3 minutes
**Purpose**: Verify basic invocation, section listing, and navigation commands

**Tests**:
- Guide agent invokes successfully
- All 7 sections listed
- Skill assessment presented
- Navigation menu shown
- All 5 platforms mentioned
- Cross-references present

**Run**:
```bash
gadugi-agentic-test run .claude/tests/agentic/guide-agent-tutorial-basic.yaml
```

### Level 2: Interactive Navigation
**File**: `guide-agent-interactive-navigation.yaml`
**Duration**: ~5 minutes
**Purpose**: Test user interaction flow, section jumping, and navigation commands

**Tests**:
- Section navigation (Section 1, 2, 3, 5, 6)
- Menu command functionality
- Continue command progression
- Help command assistance
- Cross-references validated
- Progressive content delivery

**Run**:
```bash
gadugi-agentic-test run .claude/tests/agentic/guide-agent-interactive-navigation.yaml
```

### Level 2: Advanced Features
**File**: `guide-agent-advanced-features.yaml`
**Duration**: ~7 minutes
**Purpose**: Test goal structuring workshop, progressive disclosure, advanced content

**Tests**:
- Advanced user direct section access
- Goal structuring workshop (interactive)
- Progressive disclosure ([BEGINNER] vs [ADVANCED])
- All platforms with examples
- Lock/unlock, auto mode coverage
- Fault-tolerant workflows explained
- Zero-BS compliance (no TODOs/placeholders)

**Run**:
```bash
gadugi-agentic-test run .claude/tests/agentic/guide-agent-advanced-features.yaml --verbose
```

### Level 3: Comprehensive Journey
**File**: `guide-agent-comprehensive-tutorial.yaml`
**Duration**: ~10 minutes
**Purpose**: Complete end-to-end tutorial journey from beginner to advanced

**Tests**:
- Full beginner-to-advanced progression
- All 7 sections accessed sequentially
- Goal structuring workshop integration
- Platform-specific examples for all platforms
- Documentation cross-references functional
- Philosophy compliance (Zero-BS)
- Navigation command suite

**Run**:
```bash
gadugi-agentic-test run .claude/tests/agentic/guide-agent-comprehensive-tutorial.yaml --save-evidence
```

## Prerequisites

### Install gadugi-agentic-test
```bash
pip install gadugi-agentic-test
```

### Verify Installation
```bash
gadugi-agentic-test --version
```

### Set API Key
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Running All Tests

```bash
# Run all guide agent tests
gadugi-agentic-test run .claude/tests/agentic/guide-agent-*.yaml

# With verbose output
gadugi-agentic-test run .claude/tests/agentic/guide-agent-*.yaml --verbose

# Save evidence artifacts
gadugi-agentic-test run .claude/tests/agentic/guide-agent-*.yaml --save-evidence
```

## Test Coverage

### Functional Coverage
- ✅ Guide agent invocation
- ✅ Skill assessment (beginner/intermediate/advanced)
- ✅ All 7 tutorial sections
- ✅ Navigation commands (Section N, Continue, Menu, Help)
- ✅ Platform support (5 platforms)
- ✅ Progressive disclosure
- ✅ Goal structuring workshop
- ✅ Documentation cross-references

### Content Coverage
- ✅ Section 1: Welcome & Setup
- ✅ Section 2: First Workflow
- ✅ Section 3: Workflows (all 8 types)
- ✅ Section 4: Prompting Techniques
- ✅ Section 5: Continuous Work (auto, lock modes)
- ✅ Section 6: Goal Agents
- ✅ Section 7: Advanced Topics

### Quality Coverage
- ✅ Zero-BS compliance (no TODOs/stubs)
- ✅ Philosophy alignment
- ✅ User experience flow
- ✅ Error-free navigation

## Evidence Artifacts

After running with `--save-evidence`, check:

```
./evidence/guide-agent-*/
├── execution.log         # Full test execution log
├── output-captures/      # Agent responses at each step
├── screenshots/          # Terminal state captures
└── report.html          # HTML test report
```

## Success Criteria

**All tests should**:
- Exit with code 0
- Complete within timeout
- Find all expected content
- Verify no TODOs/placeholders
- Confirm all 7 sections accessible
- Validate cross-references

## Troubleshooting

### Test Timeout
Increase timeout multiplier in scenario environment:
```yaml
environment:
  timeout_multiplier: 2.0
```

### API Key Issues
Verify key is set:
```bash
echo $ANTHROPIC_API_KEY
```

### Guide Agent Not Found
Ensure you're in amplihack worktree with v2.0.0 guide agent:
```bash
grep "^version:" .claude/agents/amplihack/core/guide.md
```

## Integration with Step 13

These tests satisfy DEFAULT_WORKFLOW Step 13 (Mandatory Local Testing) by:

1. **Interactive Testing**: Simulates real user interactions
2. **Multiple Scenarios**: Basic, intermediate, and comprehensive flows
3. **Evidence-Based**: Captures artifacts for verification
4. **Outside-In**: Tests from user perspective
5. **Regression Prevention**: Ensures no functionality breaks

## Next Steps

After tests pass:
1. Review evidence artifacts in `./evidence/`
2. Include test results in PR description
3. Add test scenarios to CI pipeline (optional)
4. Update test suite as tutorial evolves

---

**Testing Philosophy**: These tests verify the guide agent works like a user would experience it, ensuring the tutorial system delivers on its promise to guide users from basics to advanced mastery.
