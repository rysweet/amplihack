# Expert Analyst Agent Validation Testing Plan

## Purpose

Validate that all 23 domain expert analyst agents perform correctly on their domain-specific test quizzes and improve any analysts that fail to meet the 70% passing threshold (35/50 per scenario, 175/250 overall).

---

## Testing Methodology

### 1. Automated Testing with Claude Agent SDK (Future)

**Pattern** (from economist quiz):

```python
from claude_agent_sdk import Agent, TestHarness

agent = Agent.load("[discipline]-analyst")
quiz = load_quiz_scenarios("tests/quiz.md")

results = []
for scenario in quiz.scenarios:
    analysis = agent.analyze(scenario.event)
    score = evaluate_analysis(analysis, scenario.expected_elements)
    results.append({"scenario": scenario.name, "score": score})

# Assert quality thresholds
assert sum(r["score"] for r in results) >= 175  # Overall passing
assert sum(1 for r in results if r["score"] >= 35) >= 4  # 4 of 5 pass
```

### 2. Manual Testing (Current Approach)

For each analyst:

**Step 1: Load Skill**

```
Claude, use the [discipline]-analyst skill
```

**Step 2: Run Quiz Scenario**
Present one scenario from the quiz and have the analyst analyze it

**Step 3: Evaluate Against Expected Elements**
Check if analysis includes all expected elements from quiz checklist:

- Domain frameworks applied correctly
- Appropriate methods used
- Evidence-based reasoning
- Clear insights
- Proper terminology

**Step 4: Score Analysis**
Rate on 5 criteria (0-10 each):

- Domain Accuracy
- Analytical Depth
- Insight Specificity
- Historical Grounding
- Reasoning Clarity

**Step 5: If Score < 35/50**
Identify gaps and enhance SKILL.md:

- Add missing frameworks
- Strengthen methodological guidance
- Enhance analysis rubric
- Add more examples
- Enrich reference materials

---

## Validation Schedule

### Phase 1: Core Social Science Analysts (5 agents)

1. **Economist** - Test on Carbon Tax scenario
2. **Political Scientist** - Test on Coalition Formation scenario
3. **Historian** - Test on Revolutionary Crisis scenario
4. **Sociologist** - Test on Remote Work scenario
5. **Anthropologist** - Test on Corporate Culture Clash scenario

### Phase 2: Humanities & Communication (4 agents)

6. **Novelist** - Test on Character Arc scenario
7. **Journalist** - Test on Investigative Reporting scenario
8. **Poet** - Test on Protest Poem scenario
9. **Futurist** - Test on AGI Development scenario

### Phase 3: Natural Sciences (5 agents)

10. **Physicist** - Test on Space Debris scenario
11. **Chemist** - Test on Chemical Plant Explosion scenario
12. **Psychologist** - Test on Social Media Mental Health scenario
13. **Environmentalist** - Test on Coral Reef Collapse scenario
14. **Biologist** - Test on Coral Reef scenario (biological focus)

### Phase 4: Applied Fields (6 agents)

15. **Computer Scientist** - Test on Cryptocurrency Security scenario
16. **Cybersecurity** - Test on Zero-Day Vulnerability scenario
17. **Lawyer** - Test on Employment Discrimination scenario
18. **Indigenous Leader** - Test on Sacred Site scenario
19. **Engineer** - Test on Bridge Failure scenario
20. **Urban Planner** - Test on TOD Proposal scenario

### Phase 5: Philosophy & Ethics (3 agents)

21. **Ethicist** - Test on Autonomous Vehicle Dilemma
22. **Philosopher** - Test on Ship of Theseus scenario
23. **Epidemiologist** - Test on Outbreak Investigation scenario

---

## Scoring Rubric

### Per Scenario (50 points max)

**Domain Accuracy** (0-10):

- 10: Perfect application of frameworks, zero errors
- 8-9: Correct application with minor imprecision
- 6-7: Mostly correct with some conceptual gaps
- 4-5: Significant errors or missing frameworks
- 0-3: Fundamental misunderstanding of domain

**Analytical Depth** (0-10):

- 10: Comprehensive, multi-layered analysis
- 8-9: Thorough analysis hitting all major points
- 6-7: Adequate but missing some depth
- 4-5: Superficial analysis
- 0-3: Minimal or no real analysis

**Insight Specificity** (0-10):

- 10: Specific, actionable, non-obvious insights
- 8-9: Clear, useful insights with some specificity
- 6-7: General insights, limited specificity
- 4-5: Vague or obvious insights
- 0-3: No meaningful insights

**Historical Grounding** (0-10):

- 10: Rich historical/empirical evidence, well-cited
- 8-9: Good use of evidence and precedents
- 6-7: Some evidence, could be stronger
- 4-5: Minimal evidence or citations
- 0-3: No grounding in evidence

**Reasoning Clarity** (0-10):

- 10: Crystal clear logic, easy to follow
- 8-9: Clear reasoning with minor gaps
- 6-7: Mostly clear but some confusion
- 4-5: Unclear or hard to follow
- 0-3: Incoherent or illogical

### Overall Assessment

**Per Scenario**:

- **Passing**: 35-50 (70-100%)
- **Failing**: 0-34 (<70%)

**Overall (5 scenarios)**:

- **Passing**: 175-250 overall AND 4+ scenarios pass
- **Failing**: <175 overall OR <4 scenarios pass

---

## Improvement Protocol

If an analyst scores < 35/50 on any scenario:

### Step 1: Diagnose Gaps

Identify what was missing:

- [ ] Missing theoretical framework?
- [ ] Inadequate methodology?
- [ ] Weak analysis rubric?
- [ ] Insufficient examples?
- [ ] Poor reference materials?
- [ ] Unclear step-by-step process?

### Step 2: Enhance SKILL.md

**Add Missing Frameworks**:

- Research additional theories/methods
- Add to Theoretical Foundations section
- Provide examples of application

**Strengthen Analysis Rubric**:

- Add more specific guidance
- Clarify what to examine
- Enhance question prompts

**Improve Examples**:

- Add examples showing missing capability
- Demonstrate framework application
- Show integration of methods

**Enrich References**:

- Add sources for weak areas
- Include methodology guides
- Provide empirical evidence

### Step 3: Retest

Run the same scenario again and verify improvement

### Step 4: Document Changes

Track what was improved and why in session logs

---

## Testing Checklist

### For Each Analyst

- [ ] Load skill successfully
- [ ] Run 1-2 quiz scenarios
- [ ] Score analysis on 5 criteria
- [ ] Verify passing threshold (35+/50)
- [ ] If failing: Enhance and retest
- [ ] Document test results
- [ ] Mark as validated

### Overall System

- [ ] All 23 analysts tested
- [ ] All meet 70% threshold
- [ ] Consistent quality across domains
- [ ] Test results documented
- [ ] Any improvements committed

---

## Expected Outcomes

### Success Criteria

All 23 analysts should:

- Apply discipline-specific frameworks correctly
- Use appropriate methodologies
- Provide evidence-based analysis
- Generate actionable insights
- Demonstrate domain expertise
- Score 35+/50 on quiz scenarios

### Quality Threshold

**Minimum Acceptable**: 70% (35/50 per scenario)

**Target**: 80%+ (40/50 per scenario)

**Excellent**: 90%+ (45/50 per scenario)

---

## Implementation Timeline

### Phase 1: Preparation (Complete)

- ✅ All 23 test quizzes created
- ✅ Scoring rubric established
- ✅ Evaluation criteria defined

### Phase 2: Testing (Post-Merge)

- [ ] Merge PR #1346
- [ ] Skills loaded in Claude Code
- [ ] Run systematic testing
- [ ] Score all analysts
- [ ] Identify gaps

### Phase 3: Improvement (If Needed)

- [ ] Enhance failing analysts
- [ ] Retest improved agents
- [ ] Document changes
- [ ] Create follow-up PR if significant improvements

### Phase 4: Documentation

- [ ] Create TESTING_RESULTS.md
- [ ] Document scores for all agents
- [ ] Capture lessons learned
- [ ] Update DISCOVERIES.md

---

## Testing Results Template

```markdown
# Analyst Validation Testing Results

## Test Date: [DATE]

### [Analyst Name]

**Scenario Tested**: [Scenario Name]

**Analysis Output**: [Link or summary]

**Scores**:

- Domain Accuracy: X/10
- Analytical Depth: X/10
- Insight Specificity: X/10
- Historical Grounding: X/10
- Reasoning Clarity: X/10
  **Total**: X/50 (X%)

**Result**: PASS/FAIL

**Expected Elements Coverage**:

- [✓] Element 1
- [✓] Element 2
- [✗] Element 3 (missing)

**Improvements Made** (if failing):

- Added [framework] to Theoretical Foundations
- Enhanced Analysis Rubric with [specific guidance]
- Added example demonstrating [capability]

**Retest Score**: X/50 (if retested)
```

---

## Success Metrics

### Individual Analyst

- ✅ Scores 35+/50 on quiz scenarios
- ✅ Applies frameworks correctly
- ✅ Uses domain-appropriate methods
- ✅ Provides evidence-based insights

### Overall System

- ✅ All 23 analysts validated
- ✅ Consistent quality across domains
- ✅ Test coverage: 115 scenarios (23 agents × 5 scenarios)
- ✅ Improvement loop functional (test → enhance → retest)

---

## Notes

- Testing should occur AFTER PR #1346 merges and skills are loaded
- Manual testing is acceptable initially; SDK automation is enhancement
- Focus on validating domain expertise, not perfect scores
- Improvement loop demonstrates system quality and self-improvement capability

**Status**: Plan complete, ready for execution post-merge
**Validation Requirement**: ALL analysts must pass their quizzes
**Quality Standard**: Minimum 70% (35/50), target 80%+ (40/50)
