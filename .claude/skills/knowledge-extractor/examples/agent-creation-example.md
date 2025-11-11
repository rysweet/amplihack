# Knowledge Extraction Example: Agent Creation

## Scenario

After diagnosing CI failures for the 3rd time using the same 5-step workflow, each taking 30-45 minutes. Recognition that this should be automated as a specialized agent.

## Session Summary

- **Session 1**: CI version mismatch issue - 45 minutes debug
- **Session 2**: Pre-commit hook failure - 30 minutes debug
- **Session 3**: Merge conflict - 25 minutes debug
- **Pattern recognized**: Same 5-step diagnostic process each time
- **Opportunity**: Automate diagnostic workflow into new agent

## Extraction Process

### Step 1: Identify Repeated Workflow

**Session 1 workflow**:

1. Check CI logs for error patterns (5 min)
2. Verify environment (Python version, tools) (5 min)
3. Compare local vs CI setup (10 min)
4. Identify root cause pattern (15 min)
5. Suggest/implement fix (10 min)

**Session 2 workflow**:

1. Check logs for errors (5 min)
2. Verify environment (5 min)
3. Check merge conflicts (7 min)
4. Identify root cause (10 min)
5. Suggest fixes (3 min)

**Session 3 workflow**:

1. Check logs (4 min)
2. Verify environment (5 min)
3. Check for conflicts (6 min)
4. Identify issue (5 min)
5. Suggest fixes (5 min)

**Recognition**: Same 5-step process, different root causes

### Step 2: Validate ROI

**Frequency**: 2-3 CI failures per week = 8-12 per month
**Time per session**: 25-45 minutes (average 35 minutes)
**Annual time**: 35 min × 10 sessions = 350 minutes = 5.8 hours

**If automated**:

- Phase 1 (Basic checks): 2 min (vs 10 min)
- Phase 2 (Parallel diagnosis): 8 min (vs 20 min)
- Phase 3 (Synthesis): 5 min (vs 5 min)
- **Total**: 15 min (vs 35 min) = 57% time reduction

**Annual savings**: 35 min × 0.43 = 15 min per session × 10 = 150 min = 2.5 hours

**ROI**: ~1 hour agent development → 2.5 hours saved/year → 2.5:1 ROI in first year

### Step 3: Create Agent Recommendation

````markdown
## Recommended Agent: ci-diagnostic-workflow

### Problem

CI failures are diagnosed manually using same 5-step process every time.
Each diagnosis takes 25-45 minutes (average 35 minutes). We encounter
2-3 CI failures per week, representing ~3 hours per month of manual diagnosis.

### Scope

**In Scope**:

- Analyze CI logs for error patterns
- Check environment (Python version, tool versions)
- Detect common issues (merge conflicts, version mismatches, pre-commit hooks)
- Identify root cause
- Suggest fixes (does NOT auto-fix, only suggests)
- Coordinate parallel diagnostic agents for complex issues

**Out of Scope**:

- Auto-fixing issues (too risky without review)
- Merging branches or resolving conflicts
- Changing CI configuration
- Running tests or builds

### Inputs

```python
{
    "pr_number": str,              # GitHub PR number
    "failure_logs": str,           # Complete CI log output
    "branch_info": dict,           # Branch status, merge conflicts
    "environment_info": dict,      # Python version, tool versions
}
```
````

### Process

**Phase 1: Environment Quick Check** (2 minutes)

1. Parse Python version from CI environment
2. Check tool versions (ruff, pytest, etc.)
3. Detect obvious mismatches with local setup
4. Flag if environment is clearly incorrect

**Phase 2: Parallel Diagnostic Analysis** (8 minutes)
Deploy specialized agents in parallel:

- Log Parser: Extract error signatures from CI logs
- Pattern Matcher: Compare against known failure patterns
- Conflict Detector: Identify merge conflicts
- Version Analyzer: Check for version mismatches

**Phase 3: Synthesis and Recommendation** (5 minutes)

1. Combine findings from all analyzers
2. Identify primary root cause
3. Rank alternative explanations
4. Suggest fix strategy with confidence score
5. Provide next steps

### Outputs

```python
{
    "root_cause": {
        "primary": str,            # Main issue identified
        "alternatives": [str],     # Alternative explanations
        "confidence": float,       # 0.0-1.0 confidence in diagnosis
    },
    "fix_strategy": {
        "steps": [str],            # Ordered fix steps
        "estimated_time": int,     # Minutes to fix
        "risk_level": str,         # low/medium/high
    },
    "escalation_needed": bool,     # True if needs human review
    "related_patterns": [str],     # Known issues this matches
}
```

### Workflow Integration

This agent fits after CI check failure:

```
Workflow Step 7: CI Check
  ├─ If passes: Continue
  └─ If fails:
      └─ Delegate to ci-diagnostic-workflow
         └─ Returns diagnosis + suggestions
         └─ Developer reviews and implements fixes
         └─ Re-run CI check
```

### Value Calculation

**Time Savings Per Issue**:

- Manual diagnosis: 35 minutes
- With agent: 15 minutes (setup + review)
- **Savings: 20 minutes per issue = 57% reduction**

**Annual Impact**:

- Issues per year: 10-12 (2-3 per week)
- Time saved: 20 min × 12 = 240 minutes = 4 hours
- **ROI: ~1 hour development → 4 hours saved = 4:1 ratio**

**Secondary Benefits**:

- Faster time-to-fix (quicker PR merging)
- Fewer repeated CI failures (learning from patterns)
- Better documentation of common issues
- Training resource for new team members

### Implementation Strategy

Agent implementation:

1. Create `.claude/agents/amplihack/ci-diagnostic-workflow.md`
2. Leverage existing agents:
   - fix-agent (for automated fixes)
   - analyzer (for log analysis)
   - patterns (for failure recognition)
3. Coordinate through orchestrator
4. Provide clear output for human decision-making

### Quality Metrics

Track effectiveness:

- Average diagnosis time (target: <20 min)
- Root cause accuracy (target: >90%)
- Developer satisfaction (target: >8/10)
- Escalation rate (target: <10%)
- Pattern match hit rate (target: >70%)

### Success Criteria

Agent is successful when:

- [ ] Reduces diagnosis time by 50%+ (35 min → <18 min)
- [ ] Root cause identified correctly 90%+ of time
- [ ] Used for 80%+ of CI failures
- [ ] Developer feedback is positive
- [ ] Saves 3+ hours per month

### Related Knowledge

**Patterns Used**:

- CI Failure Rapid Diagnosis (from PATTERNS.md)
- Parallel Agent Deployment (from PATTERNS.md)
- Specialized Agent Creation (from PATTERNS.md)

**Integration Points**:

- DEFAULT_WORKFLOW.md: Step 7 (CI Check)
- CLAUDE.md: Agent delegation triggers
- DISCOVERIES.md: CI failure patterns

```

### Step 4: Validation Checklist

- ✅ Workflow repeated 3+ times (not just once)
- ✅ Takes 30+ minutes per execution (35 min average)
- ✅ Problem domain is narrow (CI diagnostics)
- ✅ Well-defined inputs and outputs
- ✅ Clear process steps
- ✅ ROI calculation justifies automation (4:1)
- ✅ Integration point identified (Step 7)
- ✅ Success metrics defined

## Implementation Path

### Step 1: Agent Creation
- Create `.claude/agents/amplihack/ci-diagnostic-workflow.md`
- Define clear role and responsibilities
- Specify integration with parallel agent deployment

### Step 2: Integration
- Add to CLAUDE.md agent delegation triggers
- Document in workflow at Step 7
- Test with historical CI failures

### Step 3: Validation
- Run against 5+ historical failures
- Verify root cause identification
- Measure time savings
- Collect feedback

### Step 4: Deployment
- Enable in workflow
- Monitor effectiveness metrics
- Refine based on usage

## Long-Term Value

**Immediate** (first month):
- Reduce CI diagnosis from 35 min → 15 min
- Save ~1 hour per month

**Short-term** (3 months):
- Build pattern database (10+ CI failures)
- Hit rate improves with experience
- Save ~3 hours per month

**Long-term** (1 year):
- Comprehensive CI failure pattern library
- Near-automatic diagnosis for known patterns
- Save ~4 hours per month

## Key Principle

When you recognize a workflow repeated 2-3 times taking 30+ minutes, automation becomes valuable. Extract the workflow as an agent to transform manual work into orchestrated intelligence.
```
