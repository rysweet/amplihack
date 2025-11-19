# Benchmarking amplihack

Guide for evaluating amplihack's effectiveness and measuring its value proposition.

## TL;DR

**amplihack requires interactive execution** and cannot run in non-interactive sandboxes like eval-recipes. Use alternative evaluation approaches focused on developer experience and workflow value.

## Why Standard Benchmarks Don't Work

### The Permission Model Conflict

**eval-recipes and similar frameworks require**:
- Non-interactive execution (`--disallowedTools "AskUserQuestion"`)
- One-shot task completion
- No human in the loop
- Automated approval for all operations

**Claude Code + amplihack require**:
- Interactive execution
- User approval for file operations
- Iterative development
- Human oversight for safety

**These execution models are fundamentally incompatible.**

### What We Learned from eval-recipes

We successfully integrated amplihack with Microsoft's eval-recipes framework:
- ✅ Infrastructure works perfectly
- ✅ amplihack's .claude/ context loads in Docker
- ✅ Workflow orchestration confirmed active
- ✅ Multi-agent coordination functional
- ❌ **Blocked by permission approvals** → 0/100 scores

**This is a design conflict, not an architecture flaw.**

**See**: https://github.com/rysweet/eval-recipes/blob/main/AMPLIHACK_BENCHMARK_FINDINGS.md

## Alternative Evaluation Approaches

### 1. Developer Velocity Measurement

**Metrics to Track**:
- Time to working PR (with vs without amplihack)
- Number of iterations needed
- Code review cycles
- Time to merge

**How to Measure**:
```bash
# Track development time
time amplihack /ultrathink "Implement feature X"

# Compare with baseline
time claude -p "Implement feature X"
```

**Expected amplihack Advantage**: 30-50% faster with workflow orchestration

### 2. Code Quality Metrics

**Metrics to Track**:
- Test coverage achieved
- Philosophy compliance scores
- Bug rates post-merge
- Code review feedback volume

**How to Measure**:
- Run reviewer agent on outputs
- Track bugs in production
- Measure test coverage
- Count review iterations

**Expected amplihack Advantage**: Higher quality due to systematic review process

### 3. Workflow Completion Rates

**Metrics to Track**:
- Percentage of tasks completing all 15 workflow steps
- Frequency of skipped steps
- Time per workflow step
- Agent utilization rates

**How to Measure**:
- Parse .claude/runtime/logs/ for workflow execution
- Track TodoWrite completion rates
- Measure agent invocation frequency
- Analyze decision logs

**Expected amplihack Advantage**: 90%+ workflow completion vs ad-hoc approaches

### 4. User Satisfaction Studies

**Metrics to Track**:
- Developer confidence in outputs
- Perceived code quality
- Frustration with workflow
- Willingness to recommend

**How to Measure**:
- Post-task surveys
- Likert scale ratings
- Qualitative interviews
- Net Promoter Score

**Expected amplihack Advantage**: Higher satisfaction due to systematic approach

### 5. Terminal Session Analysis

**Approach**: Record actual usage sessions

**Metrics to Track**:
- Commands executed
- Time distribution across workflow steps
- Error recovery patterns
- Context switches

**How to Measure**:
- Screen recordings
- Terminal session logs (asciinema)
- Keystroke analysis
- Workflow trace analysis

**Expected amplihack Advantage**: Visible workflow structure, fewer context switches

## What Makes amplihack Valuable

### Core Differentiator: /ultrathink Workflow Orchestration

**Without /ultrathink**:
- amplihack = vanilla Claude Code + overhead
- No multi-agent coordination
- No systematic approach
- No workflow steps
- **Benchmark proved**: Identical output to vanilla

**With /ultrathink**:
- 15-step workflow (investigation or development)
- Multi-agent coordination
- Systematic quality gates
- Knowledge capture
- **Visible in benchmarks**: TodoWrite active, planning evident

**Recommendation**: /ultrathink should be the DEFAULT (see Issue #1405)

### Value Propositions

1. **Systematic Approach**: 15-step workflow prevents ad-hoc chaos
2. **Multi-Agent Coordination**: Specialized agents for each concern
3. **Quality Gates**: Multiple review stages catch issues early
4. **Knowledge Capture**: Learnings persist in DISCOVERIES.md
5. **Context Preservation**: Never lose requirements or decisions
6. **Philosophy Enforcement**: Ruthless simplicity + modular design

## Measuring These Values

### Workflow Value

**Metric**: Compare outcomes with vs without workflow

**Test**:
```bash
# With workflow (amplihack default)
amplihack /ultrathink "Complex task"

# Without workflow (vanilla)
claude -p "Complex task"
```

**Measure**: Code quality, time to completion, test coverage, philosophy compliance

### Agent Coordination Value

**Metric**: Track agent utilization and output quality

**Test**: Analyze .claude/runtime/logs/ for agent invocations

**Measure**: How often agents used, quality of agent outputs, coordination effectiveness

### Knowledge Capture Value

**Metric**: Reuse rate of captured knowledge

**Measure**: How often DISCOVERIES.md prevents repeat work, pattern reuse frequency

## Current Limitations

### Cannot Use

- ❌ eval-recipes (permission model conflict)
- ❌ Non-interactive sandboxes
- ❌ Automated CI/CD benchmarks (without approval mechanism)
- ❌ One-shot Docker containers
- ❌ Frameworks requiring `--disallowedTools "AskUserQuestion"`

### Can Use

- ✅ Terminal-based user studies
- ✅ Developer velocity measurements
- ✅ Code quality comparisons
- ✅ Workflow completion tracking
- ✅ Screen recordings and demos
- ✅ Qualitative developer feedback

## eval-recipes Integration Status

**Fork**: https://github.com/rysweet/eval-recipes
**Status**: Working agent configuration committed
**Commit**: 8cf5994

**Agent Config**:
- `data/agents/amplihack/agent.yaml` - Environment variables
- `data/agents/amplihack/install.dockerfile` - Context setup
- `data/agents/amplihack/command_template.txt` - Invocation pattern

**Proven Working**:
- Docker build successful
- .claude/ context loads correctly
- Workflow orchestration activates
- User preferences applied
- **Blocked only by permission model**

**Findings**: See `AMPLIHACK_BENCHMARK_FINDINGS.md` in fork

## Recommendations

### For Evaluating amplihack

1. **Focus on Workflow Value**: Measure orchestration effectiveness, not raw execution speed
2. **Use Interactive Studies**: Terminal sessions, user feedback, quality analysis
3. **Compare With-vs-Without /ultrathink**: Show orchestration value empirically
4. **Track Knowledge Reuse**: Measure DISCOVERIES.md impact
5. **Document Success Stories**: Real-world examples of amplihack value

### For Future Benchmarking

1. **Design Interactive Framework**: Build evaluation that works with Claude Code's model
2. **Hybrid Approach**: Automated metrics + human evaluation
3. **Workflow-Centric Metrics**: Measure systematic approach, not just outputs
4. **Long-Term Studies**: Track value over weeks/months, not single tasks

## Resources

- **eval-recipes Fork**: https://github.com/rysweet/eval-recipes
- **Benchmark Findings**: AMPLIHACK_BENCHMARK_FINDINGS.md in fork
- **PR #1386**: Integration attempt and learnings
- **Issue #1405**: Make /ultrathink default
- **Issue #1406**: Add Docker compatibility
- **Investigation Logs**: `.claude/runtime/logs/20251116_201452/`

## Example: Measuring Workflow Value

```python
# Evaluation script
def compare_amplihack_value(task: str):
    # Run with amplihack + ultrathink
    start = time.time()
    result_amplihack = run("amplihack /ultrathink '{task}'")
    time_amplihack = time.time() - start

    # Run with vanilla Claude
    start = time.time()
    result_vanilla = run("claude -p '{task}'")
    time_vanilla = time.time() - start

    # Measure outcomes
    quality_amplihack = reviewer_agent.score(result_amplihack)
    quality_vanilla = reviewer_agent.score(result_vanilla)

    tests_amplihack = count_tests(result_amplihack)
    tests_vanilla = count_tests(result_vanilla)

    print(f"amplihack: {time_amplihack}s, quality: {quality_amplihack}, tests: {tests_amplihack}")
    print(f"vanilla:   {time_vanilla}s, quality: {quality_vanilla}, tests: {tests_vanilla}")
```

**Expected Results**: amplihack takes longer but produces higher quality with better test coverage

---

Generated: 2025-11-17
Based on: eval-recipes benchmarking investigation and execution
