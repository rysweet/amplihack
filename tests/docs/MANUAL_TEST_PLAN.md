# Manual Documentation Testing Plan

This document provides human verification tests that complement automated testing.
Perform these tests BEFORE and AFTER the documentation reorganization.

## Test Status Legend

- ⬜ Not started
- 🟨 In progress
- ✅ Passed
- ❌ Failed

---

## Pre-Reorganization Baseline (Expected: Many Failures)

Run these tests to establish baseline. **These SHOULD fail** - that's why we're reorganizing!

### Test 1: New User Experience ⬜

**Objective**: Verify a new user can get started quickly.

**Steps**:

1. Open `docs/index.md` in browser
2. Can you find "Get Started" section within 5 seconds? ⬜
3. Can you find "Prerequisites" link? ⬜
4. Can you find "Installation" guide? ⬜
5. Can you find "Quick Start" tutorial? ⬜

**Expected Pre-Reorg**: 🟨 Some links may be broken or hard to find
**Expected Post-Reorg**: ✅ All links clear and functional

**Actual Result (Pre)**:
```
[Record observations here]
```

**Actual Result (Post)**:
```
[Record observations here]
```

---

### Test 2: Goal-Seeking Agent Discoverability ⬜

**Objective**: Verify goal-seeking agents are prominently linked (user requirement).

**Steps**:

1. Open `docs/index.md`
2. Search for "goal" or "autonomous agents" ⬜
3. Is there a clear section dedicated to goal-seeking agents? ⬜
4. Are there multiple links to goal-seeking agent docs? ⬜
5. Click first goal-seeking link - does it work? ⬜

**Expected Pre-Reorg**: ❌ May be buried or missing
**Expected Post-Reorg**: ✅ Prominently featured with working links

**Actual Result (Pre)**:
```
[Record observations here]
```

**Actual Result (Post)**:
```
[Record observations here]
```

---

### Test 3: Navigation Efficiency ⬜

**Objective**: Verify docs are accessible within 3 clicks.

**Steps**:

1. Start at `docs/index.md`
2. Find documentation for: `/ultrathink` command
   - Clicks required: ___ ⬜
3. Find documentation for: DDD workflow
   - Clicks required: ___ ⬜
4. Find documentation for: Neo4j memory system
   - Clicks required: ___ ⬜
5. Find documentation for: Creating custom agents
   - Clicks required: ___ ⬜

**Expected Pre-Reorg**: 🟨 4-5 clicks for some topics
**Expected Post-Reorg**: ✅ ≤3 clicks for all topics

**Actual Result (Pre)**:
```
/ultrathink: ___ clicks
DDD workflow: ___ clicks
Neo4j memory: ___ clicks
Custom agents: ___ clicks
```

**Actual Result (Post)**:
```
/ultrathink: ___ clicks
DDD workflow: ___ clicks
Neo4j memory: ___ clicks
Custom agents: ___ clicks
```

---

### Test 4: Link Integrity ⬜

**Objective**: Verify no broken links in common user paths.

**Steps**:

1. Open `docs/index.md`
2. Click 10 random links from index ⬜
3. For each link that works, click 2 more links from that page ⬜
4. Record any broken links

**Expected Pre-Reorg**: ❌ Several broken links expected
**Expected Post-Reorg**: ✅ Zero broken links

**Broken Links Found (Pre)**:
```
1.
2.
3.
...
```

**Broken Links Found (Post)**:
```
[Should be empty]
```

---

### Test 5: Breadth of Coverage ⬜

**Objective**: Verify all major features are documented and linked.

**Steps**:

Search for these features in `docs/index.md`:

1. Workflows (DEFAULT_WORKFLOW, INVESTIGATION, DDD) ⬜
2. Core commands (/ultrathink, /analyze, /improve, /fix) ⬜
3. Agents (architect, builder, tester) ⬜
4. Goal-seeking agents ⬜
5. Memory systems (Neo4j) ⬜
6. Skills ⬜
7. Remote sessions ⬜
8. Testing & Quality ⬜
9. Security ⬜
10. Troubleshooting ⬜

**Expected Pre-Reorg**: 🟨 Some may be missing or buried
**Expected Post-Reorg**: ✅ All clearly linked

**Coverage Results (Pre)**:
```
Workflows: [✅/❌]
Commands: [✅/❌]
Agents: [✅/❌]
Goal-seeking: [✅/❌]
Memory: [✅/❌]
Skills: [✅/❌]
Remote sessions: [✅/❌]
Testing: [✅/❌]
Security: [✅/❌]
Troubleshooting: [✅/❌]
```

**Coverage Results (Post)**:
```
Workflows: [✅/❌]
Commands: [✅/❌]
Agents: [✅/❌]
Goal-seeking: [✅/❌]
Memory: [✅/❌]
Skills: [✅/❌]
Remote sessions: [✅/❌]
Testing: [✅/❌]
Security: [✅/❌]
Troubleshooting: [✅/❌]
```

---

### Test 6: Information Architecture ⬜

**Objective**: Verify logical grouping and clear hierarchy.

**Steps**:

1. Open `docs/index.md`
2. Are topics grouped logically? (e.g., Getting Started, Core Concepts, etc.) ⬜
3. Is there a clear hierarchy (H1 → H2 → H3)? ⬜
4. Are related topics near each other? ⬜
5. Is there visual separation between major sections? ⬜

**Expected Pre-Reorg**: 🟨 Some organization issues
**Expected Post-Reorg**: ✅ Clear, logical structure

**Observations (Pre)**:
```
[Record observations here]
```

**Observations (Post)**:
```
[Record observations here]
```

---

### Test 7: Search Keywords ⬜

**Objective**: Verify key terms are findable via browser search (Ctrl+F).

**Steps**:

Open `docs/index.md` and search for:

1. "goal-seeking" or "goal agent" ⬜
2. "workflow" ⬜
3. "memory" ⬜
4. "agent" ⬜
5. "command" ⬜
6. "install" ⬜
7. "troubleshoot" ⬜

**Expected Pre-Reorg**: 🟨 May miss some terms
**Expected Post-Reorg**: ✅ All terms findable

**Search Results (Pre)**:
```
goal-seeking: [Found/Not Found]
workflow: [Found/Not Found]
memory: [Found/Not Found]
agent: [Found/Not Found]
command: [Found/Not Found]
install: [Found/Not Found]
troubleshoot: [Found/Not Found]
```

**Search Results (Post)**:
```
goal-seeking: [Found/Not Found]
workflow: [Found/Not Found]
memory: [Found/Not Found]
agent: [Found/Not Found]
command: [Found/Not Found]
install: [Found/Not Found]
troubleshoot: [Found/Not Found]
```

---

## Post-Reorganization Validation (Expected: All Pass)

After reorganization, re-run ALL tests above and verify:

### Success Criteria

- ✅ All links functional (Test 4)
- ✅ All major features covered (Test 5)
- ✅ New user can get started in ≤3 clicks (Test 1)
- ✅ Goal-seeking agents prominently featured (Test 2)
- ✅ All topics accessible in ≤3 clicks (Test 3)
- ✅ Logical information architecture (Test 6)
- ✅ All key terms findable (Test 7)

### Final Sign-Off

**Tester Name**: _______________
**Date**: _______________
**Overall Result**: [✅ PASS / ❌ FAIL]

**Notes**:
```
[Any additional observations or recommendations]
```

---

## Continuous Testing

After initial reorganization, run these tests:

### Weekly Health Check

1. Run automated tests: `pytest tests/docs/test_documentation_structure.py -v`
2. Spot-check 5 random links from index.md
3. Search for one new feature and verify it's linked

### Before Each Release

1. Full automated test suite
2. Complete Manual Test Plan (all 7 tests)
3. User feedback survey (if available)

---

## Troubleshooting Test Failures

### If Links Are Broken

1. Run link validator: `pytest tests/docs/test_documentation_structure.py::TestLinkValidation -v`
2. Check validator output for specific broken links
3. Fix or remove broken links
4. Re-run tests

### If Orphans Found

1. Run orphan detector: `pytest tests/docs/test_documentation_structure.py::TestOrphanDetection -v`
2. For each orphan, either:
   - Add link from relevant parent document
   - Delete if truly obsolete
   - Move to archive/ directory if historical

### If Coverage Missing

1. Run coverage checker: `pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_feature_coverage -v`
2. Add missing features to index.md
3. Link to detailed documentation
4. Re-run tests

### If Navigation Too Deep

1. Run depth checker: `pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_navigation_depth -v`
2. For deep documents:
   - Add direct link from index.md or
   - Add link from intermediate document closer to index
3. Re-run tests

---

## Test Execution Log

### Pre-Reorganization Run

**Date**: _______________
**Automated Tests**: [✅ PASS / ❌ FAIL]
**Manual Tests**: [✅ PASS / ❌ FAIL]
**Failures**: _______________

### Post-Reorganization Run

**Date**: _______________
**Automated Tests**: [✅ PASS / ❌ FAIL]
**Manual Tests**: [✅ PASS / ❌ FAIL]
**Failures**: _______________

---

## Notes for Future Maintainers

1. **These tests should FAIL initially** - that's expected and good!
2. Tests passing means reorganization was successful
3. Run automated tests in CI/CD pipeline
4. Manual tests catch UX issues automation misses
5. Update tests when adding major new features
6. Keep test execution time < 30 seconds
7. Document any test failures in DISCOVERIES.md
