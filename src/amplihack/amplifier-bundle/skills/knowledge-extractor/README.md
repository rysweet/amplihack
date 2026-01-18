# Knowledge Extractor Skill

## Quick Start

The knowledge-extractor skill automatically extracts, synthesizes, and preserves organizational knowledge from conversations, debugging sessions, and problem-solving work.

## What It Does

Converts ephemeral session context into persistent knowledge that improves future performance:

1. **Extracts Discoveries**: Problems solved, root causes identified, solutions implemented
2. **Captures Patterns**: Reusable solutions applicable to multiple situations
3. **Identifies Agents**: Repeated workflows that should be automated

## When to Use

### Extract Discoveries (After solving complex problems)

```
Claude, extract what we learned from this debugging session.
Update DISCOVERIES.md with root causes and solutions.
```

### Extract Patterns (After implementing proven solutions)

```
What patterns should we capture from this implementation?
Update PATTERNS.md with reusable approaches.
```

### Identify New Agents (After repeating same workflow 2+ times)

```
We've debugged CI failures multiple times with the same process.
Should we create a new agent to automate this?
```

### Full Knowledge Extraction

```
Perform complete knowledge extraction on this session.
Extract discoveries, patterns, and agent recommendations.
```

## Real-World Examples

### Example 1: Bug Fix Knowledge Extraction

**After debugging pre-commit hook failure** (45 minutes):

```
User: Extract what we learned from fixing the pre-commit issue.

Claude:
1. Analyzes the debugging session
2. Identifies root cause: Cloud sync file locks
3. Finds solution: Exponential backoff retry logic
4. Creates DISCOVERIES.md entry with prevention strategy
5. Suggests new pattern for "Resilient File I/O"
```

**Result**: Next time pre-commit hook fails, developers reference DISCOVERIES.md and fix in 10 minutes instead of 45.

### Example 2: Pattern Discovery

**After implementing module regeneration strategy** (multiple sessions):

```
User: Extract the pattern from this module design approach.

Claude:
1. Analyzes successful implementations
2. Identifies pattern: Brick & studs with __all__ exports
3. Documents reusable approach in PATTERNS.md
4. Includes working examples
5. Notes when/when-not-to-use
```

**Result**: Next module automatically uses brick philosophy without rethinking architecture.

### Example 3: Agent Automation Opportunity

**After debugging CI failures for the 3rd time** (same 5-step process):

```
User: We keep using the same CI debugging process. Should we automate?

Claude:
1. Recognizes repeated workflow (3+ times)
2. Calculates time savings: 45 min → 15 min per failure
3. Recommends new agent: ci-diagnostic-workflow
4. Provides creation plan with scope and boundaries
```

**Result**: New agent automates diagnosis, saves hours per quarter.

## Knowledge Types

### Type 1: Discoveries

**What**: Problems encountered, root causes, solutions
**Where**: DISCOVERIES.md
**When to extract**: After solving any complex bug or issue
**Format**: Issue → Root Cause → Solution → Learning → Prevention

### Type 2: Patterns

**What**: Proven solutions applicable to multiple situations
**Where**: PATTERNS.md
**When to extract**: When solution applies to 2+ different problems
**Format**: Challenge → Solution → Key Points → When to Use

### Type 3: Agents

**What**: Automated workflows for repeated tasks
**Where**: .claude/agents/amplihack/specialized/
**When to extract**: Workflow repeated 2+ times, saves 30+ minutes
**Format**: Problem → Scope → Process → Value

## Quality Standards

### Discoveries Must Have

- ✅ Specific problem (not generic)
- ✅ Root cause identified (why, not just what)
- ✅ Working solution with code examples
- ✅ Generalizable learning
- ✅ Actionable prevention strategy

### Patterns Must Have

- ✅ Clear problem statement
- ✅ Proven track record (used successfully 2+ times)
- ✅ Working code examples
- ✅ Clear when/when-not-to-use guidance
- ✅ Cross-references to related patterns

### Agents Must Justify

- ✅ Repeated 2+ times (not just once)
- ✅ Takes 30+ minutes per execution
- ✅ Well-defined scope and boundaries
- ✅ Clear inputs/outputs
- ✅ Estimated time savings 2x+

## Integration with System

### With DISCOVERIES.md

- Prevents repeating same mistakes
- Immediate availability to all agents
- Acts as searchable knowledge base
- Updated continuously as patterns emerge

### With PATTERNS.md

- Catalog of proven solutions
- Referenced in agent instructions
- Used for documentation and teaching
- Improved over time with usage data

### With Agent System

- New agents fill automation gaps
- Reduce manual effort for common workflows
- Extend orchestration capabilities
- Improve system efficiency

### With Session Reflection

- Automatic extraction at session end
- Preserves learnings before context loss
- Builds organizational memory
- Continuous improvement engine

## Workflow Integration

### Step 1: Session Analysis

Review conversation for learnings, patterns, repeated actions

### Step 2: Pattern Recognition

Identify which knowledge type(s) apply

### Step 3: Knowledge Extraction

Create structured entries in appropriate locations

### Step 4: Quality Verification

Ensure entries meet quality standards

### Step 5: Integration

Make knowledge available to agents/systems

## Common Extraction Scenarios

| Scenario                     | Extract To     | Example                           |
| ---------------------------- | -------------- | --------------------------------- |
| Fixed complex bug            | DISCOVERIES.md | "Pre-commit cloud sync issue"     |
| Repeated workflow 2x         | PATTERNS.md    | "Resilient file I/O"              |
| Debugging same issue 3x      | New Agent      | "ci-diagnostic-workflow"          |
| New implementation success   | PATTERNS.md    | "Module regeneration structure"   |
| Failed approach learned from | DISCOVERIES.md | "Why PBZFT was wrong pattern"     |
| Environment-specific fix     | PATTERNS.md    | "Graceful environment adaptation" |

## Time Savings

### Without Knowledge Extraction

- Debug same issue multiple times: 45 min × N
- Rediscover solutions: 30 min per solution
- Manual workflows: 40 min each

### With Knowledge Extraction

- Reference DISCOVERIES.md: 10 min
- Apply PATTERNS.md solution: 15 min
- Use automated agent: 5 min

**Example**: Extracting knowledge from 1-hour debugging session saves ~4 hours over next quarter through prevention + pattern reuse.

## Getting Started

### Quick Extraction

```
"Extract what we learned from solving this problem."
→ Claude automatically identifies discoveries, patterns, agents
→ Updates appropriate knowledge bases
```

### Targeted Extraction

```
"Extract a pattern for [specific solution]"
→ Claude analyzes and documents pattern
→ Updates PATTERNS.md with working examples
```

### Full System Extraction

```
"Perform complete knowledge extraction"
→ Claude extracts all discoveries, patterns, agent opportunities
→ Updates DISCOVERIES.md, PATTERNS.md
→ Recommends new agents if applicable
```

## Success Metrics

- **Discoveries Used**: % of DISCOVERIES entries preventing mistakes (target 80%+)
- **Patterns Applied**: % of problem-solving using PATTERNS.md (target 70%+)
- **Agent ROI**: % of repeated tasks using agents (target 60%+)
- **Time Saved**: Hours saved through knowledge reuse (target N hours/week)
- **Error Reduction**: Repeat mistakes eliminated (target 95%+)

## Key Principle

Every session creates knowledge worth preserving. Without active extraction, that knowledge is lost when conversation ends. Knowledge extraction converts individual learning into organizational capability.

---

For detailed instructions, see [SKILL.md](./SKILL.md)
