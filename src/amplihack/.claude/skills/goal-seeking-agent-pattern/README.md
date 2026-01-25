# Goal-Seeking Agent Pattern Skill

## Overview

This skill guides architects on when and how to use goal-seeking agents as a design pattern. Goal-seeking agents are autonomous AI systems that execute multi-phase objectives by understanding high-level goals, planning execution, making decisions, and adapting behavior based on runtime conditions.

## What You'll Learn

- **Pattern Recognition**: Identify when goal-seeking agents are appropriate vs traditional agents
- **Design Framework**: Use 5-question decision tree to evaluate applicability
- **Architecture**: Understand components (goal definition, execution plan, phases, skills)
- **Integration**: Leverage `goal_agent_generator` module for implementation
- **Real Examples**: Study amplihack examples (AKS SRE, CI diagnostics, fix-agent)
- **Trade-Offs**: Evaluate costs and benefits of autonomous agents

## Quick Start

### Is Goal-Seeking Right for Your Problem?

Answer these 5 questions:

1. **Well-defined objective but flexible path?** (Multiple approaches to success)
2. **Multiple phases with dependencies?** (3-5+ phases, some parallel)
3. **Autonomous recovery valuable?** (Failures are expected, multiple strategies)
4. **Context affects approach?** (Environment, state, trade-offs vary)
5. **Complexity justified?** (Frequent, time-consuming, high-value)

**All 5 YES**: Use goal-seeking agent
**4 YES, 1 NO**: Probably use goal-seeking agent
**3 YES, 2 NO**: Consider simpler agent or hybrid
**2 YES, 3 NO**: Traditional agent likely better
**0-1 YES**: Script or simple automation

### Building Your First Agent

```bash
# 1. Write goal prompt
cat > my-goal.md << 'EOF'
# Goal: Automated Security Audit

Check application for security issues:
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure dependencies
- Missing security headers

Generate report with severity levels and remediation steps.
EOF

# 2. Generate agent
amplihack goal-agent-generator create \
  --prompt my-goal.md \
  --output .claude/agents/goal-driven/security-auditor

# 3. Execute agent
amplihack goal-agent-generator execute \
  --agent-path .claude/agents/goal-driven/security-auditor \
  --auto-mode
```

## Core Concepts

### Goal-Seeking vs Traditional Agents

| Characteristic       | Goal-Seeking Agent                    | Traditional Agent                   |
| -------------------- | ------------------------------------- | ----------------------------------- |
| **Input**            | High-level objective                  | Step-by-step instructions           |
| **Decision Making**  | Autonomous (adapts to context)        | Prescribed (follows fixed workflow) |
| **Failure Handling** | Self-recovering (tries alternatives)  | Manual intervention required        |
| **Complexity**       | Multi-phase with dependencies         | Single-phase or linear              |
| **Reusability**      | High (same agent, different contexts) | Low (context-specific)              |

### Architecture Components

**1. Goal Definition**: Structured representation of objective

- Primary goal (what to achieve)
- Domain (security, data, automation, etc.)
- Constraints (time, resources, safety)
- Success criteria (how to verify)
- Complexity level (simple, moderate, complex)

**2. Execution Plan**: Multi-phase plan with dependencies

- 3-5 phases (not too granular, not too coarse)
- Phase dependencies (sequential, parallel, conditional)
- Duration estimates
- Success indicators per phase

**3. Skills**: Capabilities needed for execution

- Map capabilities to existing agents/tools
- Define delegation targets
- Specify implementation type (native or delegated)

**4. Agent Bundle**: Complete executable package

- Assembled from goal, plan, and skills
- Auto-mode configuration
- Metadata and versioning

## When to Use Goal-Seeking Agents

### Pattern Indicators

**Workflow Variability**: Same objective, different approaches based on context

```
Example: Release workflow varies by environment (staging vs production),
change type (hotfix vs feature), current system state (healthy vs degraded)
```

**Multi-Phase Complexity**: Objective requires 3-5+ phases with dependencies

```
Example: Data pipeline with phases (collection → transformation → validation → publishing)
Each phase depends on previous, some can run in parallel
```

**Autonomous Recovery**: Failures are expected, multiple recovery strategies exist

```
Example: CI diagnostic workflow tries multiple fix strategies until success
```

**Adaptive Decision Making**: Need to evaluate trade-offs at runtime

```
Example: Fix agent selects QUICK/DIAGNOSTIC/COMPREHENSIVE mode based on problem analysis
```

**Domain Expertise**: Requires specialized knowledge to coordinate actions

```
Example: AKS SRE automation combines Azure, Kubernetes, networking, and security knowledge
```

## Integration with goal_agent_generator

### Programmatic API

```python
from amplihack.goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)

# Step 1: Analyze goal
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text("Your goal here")

# Step 2: Generate plan
planner = ObjectivePlanner()
plan = planner.generate_plan(goal_def)

# Step 3: Synthesize skills
synthesizer = SkillSynthesizer()
skills = synthesizer.synthesize(plan)

# Step 4: Assemble agent
assembler = AgentAssembler()
bundle = assembler.assemble(goal_def, plan, skills, bundle_name="my-agent")

# Step 5: Package for deployment
packager = GoalAgentPackager()
packager.package(bundle, output_dir=".claude/agents/goal-driven/my-agent")
```

### CLI Usage

```bash
# Create agent from prompt file
amplihack goal-agent-generator create \
  --prompt ./prompts/my-goal.md \
  --output .claude/agents/goal-driven/my-agent

# Create agent from inline prompt
amplihack goal-agent-generator create \
  --inline "Automate CI failure diagnosis" \
  --output .claude/agents/goal-driven/ci-fixer

# List generated agents
amplihack goal-agent-generator list

# Execute agent
amplihack goal-agent-generator execute \
  --agent-path .claude/agents/goal-driven/my-agent \
  --auto-mode \
  --max-turns 15
```

## Real Amplihack Examples

### Example 1: AKS SRE Automation (Issue #1293)

**Problem**: Manual AKS cluster operations are time-consuming and error-prone

**Solution**: Goal-seeking agent that:

- Audits security (RBAC, network policies, Key Vault)
- Validates networking (ingress, DNS, load balancers)
- Verifies monitoring (Container Insights, alerts)
- Checks compliance (Azure Policy, quotas)
- Generates actionable report

**Key Features**:

- Parallel execution of security/networking/monitoring checks
- Azure + Kubernetes domain expertise
- Adaptive investigation depth based on findings
- Automated remediation suggestions

**Location**: `~/.amplihack/.claude/agents/amplihack/specialized/azure-kubernetes-expert.md`

### Example 2: CI Diagnostic Workflow

**Problem**: CI failures require manual diagnosis and fix iteration

**Solution**: Goal-seeking agent that:

- Monitors CI status after push
- Diagnoses failures (test, lint, type errors)
- Applies targeted fixes
- Pushes updates and waits for CI re-run
- Iterates until all checks pass (max 5 iterations)

**Key Features**:

- Iterative fix loop with max iterations
- Pattern matching for common failures
- Smart waiting with exponential backoff
- Never auto-merges (stops at mergeable state)

**Location**: `~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md`

### Example 3: Pre-Commit Diagnostic

**Problem**: Pre-commit hooks fail with unclear errors

**Solution**: Goal-seeking agent that:

- Identifies failed hooks (ruff, black, mypy, etc.)
- Checks tool version mismatches
- Applies hook-specific fixes
- Re-runs hooks to verify
- Ensures all hooks pass before commit

**Key Features**:

- Fast local iteration (no CI wait)
- Tool version management
- Hook-specific fix templates
- 80% automated resolution

**Location**: `~/.amplihack/.claude/agents/amplihack/specialized/pre-commit-diagnostic.md`

### Example 4: Fix-Agent Pattern Matching

**Problem**: Different issues require different fix approaches

**Solution**: Goal-seeking agent that:

- Analyzes issue type and complexity
- Selects fix mode (QUICK/DIAGNOSTIC/COMPREHENSIVE)
- Applies mode-appropriate strategy
- Escalates complexity if initial mode fails

**Key Features**:

- Context-aware mode selection
- Template-based fixes (80% coverage)
- Pattern recognition from usage data
- Right-sized approach (no over-engineering)

**Location**: `~/.amplihack/.claude/agents/amplihack/specialized/fix-agent.md`

## Design Checklist

When designing goal-seeking agents, verify:

### Goal Definition

- [ ] Objective is clear and well-defined
- [ ] Success criteria are measurable
- [ ] Constraints are explicit
- [ ] Domain is identified
- [ ] Complexity is estimated

### Phase Design

- [ ] Decomposed into 3-5 phases
- [ ] Dependencies are explicit
- [ ] Parallel opportunities identified
- [ ] Success indicators per phase
- [ ] Duration estimates provided

### Error Handling

- [ ] Retry strategies defined
- [ ] Alternative strategies identified
- [ ] Escalation criteria clear
- [ ] Graceful degradation options

### Quality Standards

- [ ] Success criteria verified
- [ ] Failure scenarios tested
- [ ] State persisted across phases
- [ ] Progress reported clearly
- [ ] Philosophy compliant (simplicity, modularity)

## Common Pitfalls

### Over-Engineering

**Problem**: Building autonomous agent for simple task
**Solution**: Use decision framework (5 questions) to validate need

### Under-Specifying Success Criteria

**Problem**: Agent doesn't know when to stop
**Solution**: Define measurable, verifiable success criteria

### Ignoring Failure Scenarios

**Problem**: Agent fails ungracefully, no recovery
**Solution**: Design retry, alternative, and degradation strategies

### Missing Escalation Criteria

**Problem**: Agent loops infinitely or makes unsafe decisions
**Solution**: Define hard limits (max iterations, timeout, safety boundaries)

### Insufficient Testing

**Problem**: Agent works in happy path, breaks on edge cases
**Solution**: Test success, failure, and edge cases thoroughly

## Learning Path

**Beginner**: Build single-phase agent

- Example: File formatter that formats code and reports results
- Focus: Goal definition, success criteria, basic error handling

**Intermediate**: Build multi-phase agent

- Example: Test generator + runner that creates and executes tests
- Focus: Phase dependencies, parallel execution, state management

**Advanced**: Build autonomous recovery agent

- Example: CI fixer that diagnoses and iterates fixes
- Focus: Error recovery, alternative strategies, escalation

**Expert**: Build production goal-seeking agent

- Example: Deployment pipeline with full automation
- Focus: All concepts, integration with existing agents, observability

## Resources

### Documentation

- **Full Skill**: `~/.amplihack/.claude/skills/goal-seeking-agent-pattern/SKILL.md` (comprehensive guide)
- **Examples**: `~/.amplihack/.claude/skills/goal-seeking-agent-pattern/examples/` (3 detailed scenarios)
- **Templates**: `~/.amplihack/.claude/skills/goal-seeking-agent-pattern/templates/` (goal prompt, integration guide)
- **Tests**: `~/.amplihack/.claude/skills/goal-seeking-agent-pattern/tests/` (validation test suite)

### Code

- **Module**: `src/amplihack/goal_agent_generator/` (implementation)
- **API**: `PromptAnalyzer`, `ObjectivePlanner`, `SkillSynthesizer`, `AgentAssembler`, `GoalAgentPackager`
- **CLI**: `amplihack goal-agent-generator` (command-line interface)

### Real Agents

- **AKS Expert**: `~/.amplihack/.claude/agents/amplihack/specialized/azure-kubernetes-expert.md`
- **CI Diagnostic**: `~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md`
- **Pre-Commit**: `~/.amplihack/.claude/agents/amplihack/specialized/pre-commit-diagnostic.md`
- **Fix Agent**: `~/.amplihack/.claude/agents/amplihack/specialized/fix-agent.md`

## Getting Help

**Questions about pattern applicability?**

- Use decision framework (Section 2 of SKILL.md)
- Review problem indicators (Section 2 of SKILL.md)

**Need design guidance?**

- Check design checklist (Section 6 of SKILL.md)
- Study architecture pattern (Section 3 of SKILL.md)

**Integration issues?**

- Read integration guide (templates/integration_guide.md)
- Review API examples (Section 4 of SKILL.md)

**Want to see real examples?**

- Study amplihack examples (Section 5 of SKILL.md)
- Read example scenarios (examples/ directory)

## Next Steps

1. **Evaluate your problem**: Use 5-question decision framework
2. **Review examples**: Study real amplihack agents
3. **Start simple**: Build single-phase agent first
4. **Iterate**: Add complexity based on real needs
5. **Share learnings**: Document patterns and discoveries

---

**Remember**: Goal-seeking agents should be ruthlessly simple, focused on clear objectives, and adaptive to context. Start simple, add complexity only when justified, and always verify against success criteria.
