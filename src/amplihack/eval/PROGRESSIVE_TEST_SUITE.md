# Progressive Test Suite for Agent Learning Evaluation

## Overview

The Progressive Test Suite evaluates agent learning capabilities across 6 levels of increasing cognitive complexity, from simple recall to sophisticated reasoning about contradictions and updates.

**Philosophy**: Measure true learning capability, not just memorization. Each level requires different cognitive skills.

## Test Levels

### Level 1: Single Source Direct Recall (Baseline)
**Cognitive Skill**: Basic memory retrieval

**Example Content**: Single article about 2026 Winter Olympics medal standings

**Question Types**:
- "How many total medals does Norway have?"
- "Which country is in second place?"

**Expected Performance**: 100% (baseline - already passing)

**Reasoning**: If agent can't pass L1, it has fundamental memory problems.

---

### Level 2: Multi-Source Synthesis
**Cognitive Skill**: Combining information from multiple sources

**Example Content**: Three separate articles:
- Article A: Medal standings by country
- Article B: Individual athlete achievements
- Article C: Historical context

**Question Types**:
- "How does Italy's 2026 performance compare to their previous best?" (needs A + C)
- "Which country's individual athletes contributed most?" (needs A + B)
- "What makes 2026 historically significant for Italy?" (needs all three)

**Expected Performance**: 70-90%

**Reasoning**: Requires reading across sources and connecting related facts.

---

### Level 3: Temporal Reasoning
**Cognitive Skill**: Tracking changes over time and computing differences

**Example Content**: Three articles from different days showing medal count progression

**Question Types**:
- "How many medals did Norway win between Day 7 and Day 9?" (26-18=8)
- "Which country improved their gold medal count the most?" (compare deltas)
- "Describe the trend in Italy's performance" (acceleration pattern)

**Expected Performance**: 50-70%

**Reasoning**: Requires understanding temporal relationships and performing calculations.

---

### Level 4: Procedural Learning
**Cognitive Skill**: Learning and applying step-by-step procedures

**Example Content**: Flutter development setup guide with 9 steps and troubleshooting

**Question Types**:
- "What command creates a new Flutter project?" (recall)
- "What should you do if flutter doctor shows issues?" (conditional logic)
- "Describe the complete workflow from installation to testing" (sequence)
- "If I want to create 'weather_app' and add http package, what commands?" (apply to new input)

**Expected Performance**: 40-60%

**Reasoning**: Requires understanding procedures, not just facts. Must apply learned process to new scenarios.

---

### Level 5: Contradiction Handling
**Cognitive Skill**: Detecting and reasoning about conflicting information

**Example Content**: Two conflicting articles:
- Source A: "1.2 billion viewers (IOC preliminary data)"
- Source B: "800 million viewers (independent analysts)"

**Question Types**:
- "How many people watched?" (must acknowledge contradiction)
- "Why might the sources disagree?" (methodology differences)
- "Which source is more reliable and why?" (source credibility)

**Expected Performance**: 30-50%

**Reasoning**: Most AI agents struggle with contradictions. Current agent likely returns one source's data without noting the conflict.

---

### Level 6: Incremental Learning
**Cognitive Skill**: Updating knowledge when new information arrives

**Example Content**: Two-phase learning:
- Phase 1 (Feb 15): "Klaebo has 9 Olympic golds"
- Phase 2 (Feb 17): "Update: Klaebo won 10th gold in sprint"

**Question Types** (asked AFTER Phase 2):
- "How many golds does Klaebo have?" (must say 10, not 9)
- "How did Klaebo's record change?" (9→10, won sprint)
- "Describe complete trajectory" (integrate both phases)

**Expected Performance**: 20-40%

**Reasoning**: Tests whether agent updates existing knowledge or just appends. Many agents fail to properly update.

---

## Usage

### Run Complete Suite

```bash
python -m amplihack.eval.progressive_test_suite \
  --output-dir ./eval_progressive \
  --agent-name progressive-test-agent
```

### Run Specific Levels

```bash
python -m amplihack.eval.progressive_test_suite \
  --output-dir ./eval_l1_l2 \
  --agent-name test-agent \
  --levels L1 L2
```

### Run Single Level

```bash
python -m amplihack.eval.progressive_test_suite \
  --output-dir ./eval_l6_only \
  --agent-name test-agent \
  --levels L6
```

## Output Structure

```
eval_progressive/
├── summary.json              # Overall results
├── L1/
│   ├── learning_phase.log    # Learning subprocess output
│   ├── testing_phase.log     # Testing subprocess output
│   └── scores.json           # Graded answers
├── L2/
│   └── ...
├── L3/
│   └── ...
├── L4/
│   └── ...
├── L5/
│   └── ...
└── L6/
    ├── learning_phase1.log   # Initial learning
    ├── learning_phase2.log   # Update learning
    ├── testing_phase.log
    └── scores.json
```

## Test Content Philosophy

### Why February 2026 Winter Olympics?

**Reason**: Content that is NOT in LLM training data (cutoff January 2025).

**Benefits**:
1. Agent cannot rely on pre-training
2. Forces true learning from provided sources
3. Eliminates confabulation/hallucination detection issues
4. Real-world plausible content (Olympics did happen, just data is synthetic)

### Content Authenticity

All test content uses realistic 2026 Winter Olympics scenarios:
- Real countries, real sports, realistic medal counts
- Real athletes (Johannes Klaebo, Federica Brignone)
- Real venues (Milan-Cortina)
- Plausible but invented specific numbers and dates

This creates a fair test environment where success requires learning, not guessing.

## Integration with Agent Development

### Current Agent Status (as of this test creation)

**Expected Baseline**:
- L1: 100% (already passing in existing tests)
- L2-L6: Unknown, likely 20-50% average

### Agent Improvement Targets

After agent improvements (better retrieval, reasoning, update handling):
- L1: 100% (maintain)
- L2: 85-95% (multi-source synthesis)
- L3: 70-85% (temporal reasoning)
- L4: 60-75% (procedural learning)
- L5: 50-70% (contradiction handling)
- L6: 60-80% (incremental learning)

### Development Workflow

1. **Baseline**: Run progressive suite on current agent
2. **Identify Weakest Level**: Focus improvement efforts
3. **Implement Fix**: Improve retrieval/reasoning/update logic
4. **Re-evaluate**: Run suite again, measure improvement
5. **Iterate**: Move to next weakest level

## Extending the Test Suite

### Adding New Levels

To add Level 7:

1. Define test content in `test_levels.py`:
```python
LEVEL_7 = TestLevel(
    level_id="L7",
    level_name="Your New Cognitive Skill",
    description="What this tests",
    articles=[...],
    questions=[...]
)
```

2. Add to `ALL_LEVELS` list

3. Update grader prompt if needed (new cognitive category)

4. No changes needed to `progressive_test_suite.py` (auto-discovers from `ALL_LEVELS`)

### Adding Questions to Existing Levels

Edit the corresponding level in `test_levels.py` and add to the `questions` list.

## Technical Details

### Subprocess Isolation

Each level runs in two subprocesses:
1. **Learning subprocess**: Stores articles in memory
2. **Testing subprocess**: Fresh process, retrieves from memory only

**Why**: Ensures agent uses persistent memory, not just in-process state.

### Memory Backend

Uses `amplihack-memory-lib` by default. The agent must:
- Store experiences during learning phase
- Retrieve experiences during testing phase
- Handle updates correctly (for L6)

### Grading

Uses LLM-based semantic grading (Claude Sonnet 4.5):
- Understands semantic equivalence
- Handles paraphrasing
- Adjusts expectations by cognitive level
- Returns 0.0-1.0 score + reasoning

## Success Criteria

### Agent is "Ready" when:

- **L1**: 100% (non-negotiable baseline)
- **L2**: ≥85% (multi-source is critical)
- **L3**: ≥70% (temporal reasoning is important)
- **L4**: ≥60% (procedural is nice-to-have)
- **L5**: ≥50% (contradiction handling is advanced)
- **L6**: ≥60% (update handling is critical for long-running agents)

### Current Agent (Pre-Improvement)

Likely scores:
- L1: 100% ✓
- L2: 30-50% (lacks cross-source synthesis)
- L3: 20-40% (no temporal reasoning)
- L4: 20-40% (no procedure modeling)
- L5: 10-30% (no contradiction detection)
- L6: 10-30% (likely appends instead of updating)

**Overall**: ~30-40% average (L2-L6)

### Improved Agent (Target)

Target scores after improvements:
- L1: 100% ✓
- L2: 90% ✓
- L3: 75% ✓
- L4: 65% ✓
- L5: 60% ✓
- L6: 70% ✓

**Overall**: ~75% average (L2-L6)

This represents a **135% improvement** in learning capability.

## Files

- `test_levels.py`: Test content definitions (articles, questions)
- `progressive_test_suite.py`: Test runner and orchestration
- `agent_subprocess.py`: Learning and testing subprocess implementation
- `grader.py`: LLM-based semantic grading
- `PROGRESSIVE_TEST_SUITE.md`: This documentation

## Related

- Original eval harness: `harness_runner.py`
- Multi-source collector: `multi_source_collector.py`
- Quiz generator: `quiz_generator.py`
