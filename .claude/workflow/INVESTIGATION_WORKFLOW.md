# Investigation Workflow

This workflow defines the systematic process for conducting investigations with message budget awareness to ensure efficient, thorough analysis without runaway sessions.

## When This Workflow Applies

Use this workflow for:

- Code analysis and understanding tasks
- Architecture investigations
- Performance analysis
- Debugging and root cause analysis
- System design exploration
- Technology evaluation
- Any task requiring deep investigation with unclear completion criteria

## Core Principles

- **Budget Awareness**: Track message counts and stay within complexity-appropriate ranges
- **Checkpoint Evaluation**: Regularly assess progress vs. expected effort
- **User Control**: Provide clear choices when investigations exceed budgets
- **Quality Over Quantity**: Value insight and synthesis over exhaustive documentation
- **Transparency**: Keep user informed of progress and budget status

## The Investigation Workflow

### Step 1: Define Investigation Scope

**Objective**: Establish clear boundaries and success criteria before diving deep.

#### Actions:

- [ ] Identify core question(s) to be answered
- [ ] Define what constitutes a complete answer
- [ ] Assess complexity using 1-13 scale:
  - **1-3**: Simple (single system, clear scope)
  - **4-7**: Medium (2-3 systems, some ambiguity)
  - **8-10**: Complex (4+ systems, significant ambiguity)
  - **11-13**: Very Complex (cross-cutting, architectural)
- [ ] Determine scope (1 system / 2-3 systems / 4+ systems / cross-cutting)
- [ ] Determine depth (overview / detailed / comprehensive)
- [ ] Look up expected message budget in `@.claude/context/INVESTIGATION_MESSAGE_BUDGETS.md`
- [ ] Apply verbosity adjustment from user preferences
- [ ] Document scope and budget in investigation notes

#### Output:

```yaml
investigation:
  question: "[Core question to answer]"
  complexity: [1-13]
  scope: [1 system | 2-3 systems | 4+ systems | cross-cutting]
  depth: [overview | detailed | comprehensive]
  expected_budget: [lower]-[upper] messages
  verbosity_adjusted: [yes/no]
  checkpoint_intervals: [50, 100, 150, 200, 250, 300]
```

### Step 2: Initial Exploration

**Objective**: Gather baseline understanding through quick reconnaissance.

#### Actions:

- [ ] Identify key files, modules, or systems involved
- [ ] Read documentation if available
- [ ] Scan high-level architecture or structure
- [ ] List initial observations and questions
- [ ] Prioritize areas for deeper analysis
- [ ] Estimate if scope assessment was accurate

#### Budget Target:

- Simple: 10-20 messages
- Medium: 15-30 messages
- Complex: 20-40 messages
- Very Complex: 30-60 messages

### Step 3: Deep Dive Analysis

**Objective**: Investigate prioritized areas in detail to answer core questions.

#### Actions:

- [ ] Analyze each prioritized area systematically
- [ ] Trace data flows, call chains, or system interactions
- [ ] Identify patterns, anti-patterns, or issues
- [ ] Document key findings as they emerge
- [ ] Track questions that arise during analysis
- [ ] Connect findings to original questions

#### Budget Target:

- Simple: 15-30 messages
- Medium: 30-60 messages
- Complex: 50-100 messages
- Very Complex: 80-150 messages

### Step 4: Message Budget Checkpoints (ONGOING)

**Objective**: Prevent runaway investigations by tracking progress vs. budget at regular intervals.

**⚠️ CRITICAL**: This step runs continuously throughout the investigation, not as a single sequential step.

#### Checkpoint Triggers

Execute checkpoint evaluation at these message counts:

- **50 messages**
- **100 messages**
- **150 messages**
- **200 messages**
- **250 messages**
- **300 messages**

#### Checkpoint Actions

At each checkpoint interval:

##### 1. Count Current Messages

```python
# Pseudocode for checkpoint logic
current_count = count_session_messages()
complexity = investigation.complexity
verbosity = user_preferences.verbosity
budget_range = get_budget_range(complexity, scope, depth, verbosity)
```

##### 2. Assess Progress Status

**Questions to answer**:

- Have core questions been answered?
  - ✅ Yes → Consider synthesis
  - ❌ No → Why not? What's blocking?
- Is investigation still exploring fundamentals?
  - ✅ Yes → Justified to continue
  - ❌ No → May be over-investigating
- Are we over-investigating edge cases?
  - ✅ Yes → Time to synthesize
  - ❌ No → Continue analysis
- Hitting diminishing returns?
  - ✅ Yes → Prioritize synthesis
  - ❌ No → Continue with value-add areas

**Status Classification**:

- **On Track**: Making progress, within budget
- **Near Completion**: Core questions answered, ready for synthesis soon
- **Needs Refocus**: Exploring areas with low value-add
- **Over Budget**: Exceeded expected upper bound

##### 3. Execute Decision Tree

```
IF current_count > budget_range.upper_bound:
    status = "OVER_BUDGET"
    PROMPT user with continuation options
    WAIT for user decision
    LOG extension decision and justification

ELIF current_count >= checkpoint_interval:
    status = assess_progress_status()  # On Track | Near Completion | etc.
    percentage_used = current_count / budget_range.upper_bound * 100

    LOG checkpoint:
        "Checkpoint: {current_count} messages, {status},
         {percentage_used}% of budget used"

    CONTINUE investigation

ELSE:
    CONTINUE investigation silently
```

##### 4. User Prompt Template (When Over Budget)

```markdown
## 🎯 Investigation Budget Checkpoint

**Current Status**: {current_count} messages ({percentage_over}% over expected budget)

**Task Details**:

- Complexity: {complexity_name} ({complexity}/13)
- Expected Range: {lower}-{upper} messages
- Verbosity Setting: {verbosity}

**Progress Summary**:
{2-3 sentence summary of what's been discovered and what remains}

**Core Questions Status**:

- [✓/○] {question_1}
- [✓/○] {question_2}
- ...

**Your Options**:

**A) Continue Investigation**

- Please specify which areas need deeper analysis
- Estimated additional messages: {estimated}
- New target: ~{new_target} messages

**B) Synthesize Findings Now**

- Summarize current findings and answer questions with available information
- Estimated completion: +{N} messages for synthesis

**C) Adjust Focus**

- Narrow scope to specific high-value aspects
- Please specify priority areas

**My Recommendation**: {agent_suggestion_based_on_progress}

What would you like me to do? (A/B/C)
```

##### 5. Log Checkpoint Events

Append to `.claude/runtime/logs/{session_id}/budget_checkpoints.jsonl`:

```jsonl
{
  "timestamp": "2025-11-05T10:30:00Z",
  "message_count": 100,
  "complexity": 6,
  "budget_range": [
    60,
    120
  ],
  "status": "on_track",
  "percentage_used": 83,
  "progress_summary": "API and database layers analyzed, UI layer in progress"
}
```

#### Budget Extension Protocol

When user chooses to continue beyond budget (Option A):

1. **Acknowledge decision**:

   ```
   "Understood - extending investigation to cover {specified_areas}.
    New target: approximately {new_target} messages."
   ```

2. **Document justification**:
   - Record why extension is valuable
   - User explicitly approved continuation
   - What additional areas will be covered

3. **Update session metadata**:

   ```yaml
   budget_extension:
     granted: true
     reason: "User requested deeper analysis of {areas}"
     original_budget: [60, 120]
     new_target: 180
     timestamp: "2025-11-05T10:45:00Z"
   ```

4. **Set next checkpoint**:
   - Calculate next checkpoint interval beyond current
   - Continue checkpoint monitoring at new target

### Step 5: Synthesis and Findings

**Objective**: Consolidate discoveries into clear, actionable insights.

#### Actions:

- [ ] Organize findings by theme or system
- [ ] Answer each original question explicitly
- [ ] Provide evidence or examples for key points
- [ ] Identify implications or recommendations
- [ ] Highlight areas of uncertainty or need for follow-up
- [ ] Summarize in clear, concise format

#### Output Format:

```markdown
## Investigation Findings

### Core Questions Answered

**Q1: {original_question}**
**A1**: {clear_answer_with_evidence}

**Q2: {original_question}**
**A2**: {clear_answer_with_evidence}

### Key Discoveries

1. **{finding_1_title}**
   - Details: {explanation}
   - Impact: {implications}
   - Evidence: {code_references_or_examples}

2. **{finding_2_title}**
   - Details: {explanation}
   - Impact: {implications}
   - Evidence: {code_references_or_examples}

### Recommendations

1. {actionable_recommendation_1}
2. {actionable_recommendation_2}

### Areas for Future Investigation

- {question_or_area_not_fully_explored}
- {question_or_area_requiring_separate_investigation}

### Budget Summary

- Expected: {lower}-{upper} messages
- Actual: {actual} messages ({percentage}% of upper bound)
- Status: {Within Budget | Over Budget - Extension Approved}
- Efficiency: {insight_per_message_assessment}
```

#### Budget Target:

- Simple: 5-10 messages
- Medium: 10-20 messages
- Complex: 20-30 messages
- Very Complex: 30-50 messages

### Step 6: Validation and Review

**Objective**: Ensure investigation quality and completeness.

#### Actions:

- [ ] Verify all original questions answered
- [ ] Check findings are supported by evidence
- [ ] Ensure recommendations are actionable
- [ ] Validate budget adherence or justify extension
- [ ] Review for clarity and conciseness
- [ ] Confirm user satisfaction with depth and coverage

#### Quality Checklist:

- [ ] Original questions explicitly answered
- [ ] Findings backed by code/data/examples
- [ ] Implications and recommendations clear
- [ ] Budget status documented
- [ ] No over-investigation of edge cases
- [ ] Synthesis is concise and actionable
- [ ] User received value proportional to messages used

## Budget Adherence Guidelines

### Do's ✅

- **Start with scope definition**: Assess complexity accurately before diving in
- **Check budget at intervals**: Use checkpoint system consistently
- **Prioritize high-value areas**: Focus on questions that matter most
- **Synthesize early if possible**: Don't wait until exhaustive completion
- **Respect user verbosity preference**: Apply adjustments consistently
- **Log checkpoint decisions**: Track for continuous improvement
- **Prompt user when over budget**: Transparency and user control

### Don'ts ❌

- **Don't ignore budget warnings**: Checkpoints exist to prevent overruns
- **Don't investigate every edge case**: Focus on common paths and key insights
- **Don't assume more is better**: Quality and insight > quantity of messages
- **Don't continue without user approval**: Stop and ask when over budget
- **Don't sacrifice clarity for brevity**: Stay within budget but maintain quality
- **Don't skip scope definition**: Accurate complexity assessment is critical

## Integration with Other Workflows

### DEFAULT_WORKFLOW.md

- Investigation workflow can be invoked from Step 4 (Research and Design) of default workflow
- Follows same git workflow (worktree, branch, commit, PR)
- Respects same quality gates (philosophy compliance, testing)

### CONSENSUS_WORKFLOWS_OVERVIEW.md

- Can trigger N-version investigation for critical architecture decisions
- Debate workflow useful for investigating trade-offs
- Cascade workflow for resilient information gathering

### USER_PREFERENCES.md

- Reads verbosity preference for budget adjustments
- Respects collaboration style (independent, interactive, guided)
- Applies communication style to synthesis format

## Examples and Best Practices

### Example 1: Simple Investigation (Within Budget)

**Task**: "Explain how the password reset flow works"

**Step 1 - Scope Definition**:

```yaml
complexity: 2/13 (Simple)
scope: 1 system (auth module)
depth: detailed
expected_budget: 30-60 messages (balanced verbosity)
checkpoints: [50]
```

**Step 2 - Initial Exploration** (15 messages):

- Identified password reset endpoint, email service, token generation
- Located user model and reset token storage
- Found email template for reset link

**Step 3 - Deep Dive** (25 messages):

- Traced request flow from endpoint to email send
- Analyzed token generation and validation logic
- Verified security measures (expiration, single-use)

**Checkpoint at 50**: Status = Near Completion, 83% of budget used

**Step 5 - Synthesis** (10 messages):

- Answered core question with flow diagram
- Identified security strengths and one recommendation
- Documented in clear format

**Result**: 50 messages, within budget ✅

### Example 2: Medium Investigation (Checkpoint Trigger)

**Task**: "Analyze performance bottleneck in data processing pipeline"

**Step 1 - Scope Definition**:

```yaml
complexity: 6/13 (Medium)
scope: 2-3 systems (API, worker queue, database)
depth: detailed
expected_budget: 60-120 messages (balanced verbosity)
checkpoints: [100]
```

**Step 2 - Initial Exploration** (25 messages):

- Mapped data flow: API → Queue → Worker → DB
- Identified potential bottlenecks in each layer

**Step 3 - Deep Dive** (60 messages):

- Profiled API endpoint performance
- Analyzed queue throughput and latency
- Identified database query N+1 problem

**Checkpoint at 100**: Status = On Track, 83% of budget used

**Step 5 - Synthesis** (15 messages):

- Identified DB query as primary bottleneck
- Provided optimization recommendations
- Estimated performance improvement

**Result**: 100 messages, within budget ✅

### Example 3: Complex Investigation (Budget Extension)

**Task**: "Design microservices architecture for current monolith"

**Step 1 - Scope Definition**:

```yaml
complexity: 12/13 (Very Complex)
scope: cross-cutting (entire system)
depth: comprehensive
expected_budget: 150-300 messages (balanced verbosity)
checkpoints: [150, 250]
```

**Step 2 - Initial Exploration** (50 messages):

- Analyzed current monolith structure
- Identified bounded contexts
- Mapped dependencies

**Step 3 - Deep Dive** (120 messages):

- Designed service boundaries for 8 microservices
- Analyzed data ownership and consistency
- Identified communication patterns

**Checkpoint at 150**: Status = On Track, 50% of budget used

**Continued Deep Dive** (100 messages):

- Designed API contracts between services
- Planned data migration strategy
- Identified deployment and monitoring needs

**Checkpoint at 250**: Status = On Track, 83% of budget used

**Step 5 - Synthesis** (45 messages):

- Comprehensive migration plan with phases
- Service specifications with contracts
- Risk assessment and mitigation strategies

**Result**: 295 messages, within budget for very complex task ✅

## Continuous Improvement

### Quarterly Budget Tuning

1. **Collect data** from all investigations:
   - Actual message counts vs. budgets
   - User satisfaction ratings
   - Checkpoint effectiveness

2. **Analyze patterns**:
   - Which complexity levels consistently over/under budget?
   - Are checkpoint intervals appropriate?
   - Do verbosity adjustments work as expected?

3. **Update budget matrix**:
   - Adjust ranges based on 80th percentile of actual usage
   - Modify checkpoint intervals if too frequent/rare
   - Refine complexity scale if assessments inaccurate

4. **Document changes**:
   - Update INVESTIGATION_MESSAGE_BUDGETS.md
   - Record tuning rationale and data
   - Communicate changes to users

### Success Metrics Tracking

Monitor these metrics over time:

**Efficiency**:

- Average messages per investigation by complexity
- Percentage of investigations within budget
- Message reduction vs. pre-budget baseline

**Quality**:

- User satisfaction with investigation depth
- Core questions answered rate
- Actionability of recommendations

**User Experience**:

- Checkpoint engagement rate (user responds to prompts)
- Budget extension request rate
- Complaints about investigation length

**System Learning**:

- Complexity assessment accuracy
- Budget range accuracy (variance from actual)
- Checkpoint effectiveness (prevented overruns)

## Related Documents

- `@.claude/context/INVESTIGATION_MESSAGE_BUDGETS.md` - Budget matrix and guidelines
- `@.claude/context/USER_PREFERENCES.md` - Verbosity and collaboration preferences
- `@.claude/workflow/DEFAULT_WORKFLOW.md` - Standard development workflow
- `@.claude/context/PHILOSOPHY.md` - Core development principles

---

**Last Updated**: 2025-11-05
**Version**: 1.0
**Status**: Initial implementation
**Related Issue**: #1106
