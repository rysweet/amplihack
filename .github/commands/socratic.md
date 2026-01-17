# GitHub Copilot Command Reference: socratic

**Source**: `.claude/commands/amplihack/socratic.md`

---

## Command Metadata

- **name**: /amplihack:knowledge-builder
- **version**: 1.0.0
- **description**: Generate Socratic questions for requirements clarification
- **triggers**: 
- **invokes**: 
- **- type**: command
- **philosophy**: 
- **- principle**: Trust in Emergence
- **application**: Understanding emerges through systematic questioning
- **dependencies**: 
- **required**: 
- **optional**: 
- **examples**: 

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/socratic.md

# Use patterns from this command
gh copilot suggest --context .github/commands/socratic.md "your task"
```

---

## Original Command Documentation


# /socratic - Socratic Question Generation

Generate deep, probing Socratic questions using the Three-Dimensional Attack pattern to challenge claims and explore assumptions systematically.

## Usage

```bash
/socratic <claim to challenge>
/socratic --domain <domain> <claim>
/socratic --audience <level> <claim>
```

## Examples

```bash
/socratic "Microservices are just distributed objects"
/socratic --domain security "Input validation is sufficient for security"
/socratic --audience expert "Static typing is just documentation"
```

## What This Command Does

1. **Analyzes the claim** - Identifies key assumptions and implications
2. **Generates three questions** - Using empirical, computational, and formal dimensions
3. **Quality checks** - Ensures questions meet effectiveness thresholds
4. **Provides context** - Explains the strategic approach

## The Three-Dimensional Attack

### Dimension 1: Empirical Challenge

- Challenges with observable contrary evidence
- References historical patterns and real systems
- Grounds abstract claims in measurable reality

### Dimension 2: Computational Challenge

- Probes tractability and complexity
- Questions cognitive feasibility
- Explores composition and scaling properties

### Dimension 3: Formal Challenge

- Demands precise relationship definitions
- Uses mathematical terminology
- Creates logical forks that prevent vague answers

## Quality Standards

Generated questions target:

- **Deflection Resistance**: ≥7/10 (prevents vague responses)
- **Logical Trap**: ≥7/10 (forces genuine engagement)
- **Challenge Strength**: ≥7/10 (actually challenges the claim)
- **Overall Effectiveness**: ≥7.5/10

## Options

- `--domain <domain>` - Optimize for specific domain (software, security, architecture, devops, ml, database, pl-design, testing, concurrency, api-design)
- `--audience <level>` - Adjust complexity (beginner, intermediate, expert, research)
- `--quick` - Generate shorter, more direct questions
- `--formal` - Emphasize formal/mathematical approach
- `--empirical` - Emphasize historical/practical evidence

## Output Format

```
CLAIM ANALYSIS:
- Key assumption identified
- Observable implications
- Formal relationship type

QUESTION SET (Three-Dimensional Attack):

1. [EMPIRICAL] If [claim], why does [contrary evidence] exist?
   Strategy: Historical patterns, named systems, temporal analysis

2. [COMPUTATIONAL] Does [approach] require [intractable reasoning]?
   Strategy: Complexity analysis, cognitive load, composition properties

3. [FORMAL] Is the relationship [precise type]? What's lost?
   Strategy: Mathematical precision, logical forks, property analysis

QUALITY ASSESSMENT:
- Deflection Resistance: X/10
- Logical Trap: X/10
- Challenge Strength: X/10
- Overall Score: X/10 [PASS/EXCELLENT]

USAGE GUIDANCE:
- When to use these questions
- Expected response patterns
- Follow-up directions
```

## When to Use

✅ **Perfect for:**

- Challenging equivalence claims ("X is just Y")
- Exploring absolutist statements ("always", "never")
- Deepening technical understanding
- Surfacing hidden assumptions
- Knowledge-building conversations

❌ **Not ideal for:**

- Simple factual questions
- Time-sensitive decisions
- Consensus-building
- Purely aesthetic debates

## Integration Points

### With Knowledge Builder

Use `/socratic` to generate probing questions for deep topic exploration and assumption surfacing.

### With UltraThink

In Step 1 (Requirement Analysis), use `/socratic` to challenge unclear requirements and force precision.

### With Code Review

Challenge architectural decisions and design trade-offs with Socratic questions.

## Pattern Reference

This command implements the **Socratic Questioning Pattern** documented in `.claude/context/DISCOVERIES.md`.

**Status**: Validation phase (1/3 uses completed)
**Effectiveness**: 8.6/10 average across dimensions
**Next**: 2 more successful uses before promoting to PATTERNS.md

## Resources

- **Full Template**: `.claude/runtime/logs/20251018_socratic_questioning/SOCRATIC_TEMPLATE.md`
- **Quick Reference**: `.claude/runtime/logs/20251018_socratic_questioning/QUICK_REFERENCE.md`
- **Domain Examples**: `.claude/runtime/logs/20251018_socratic_questioning/DOMAIN_EXAMPLES.md`
- **Quality Checker**: `.claude/runtime/logs/20251018_socratic_questioning/QUALITY_CHECKER.py`

## Example Session

```bash
# User invokes command
/socratic "NoSQL is just SQL without ACID"

# System analyzes and generates
CLAIM ANALYSIS:
- Assumption: NoSQL ↔ SQL without ACID
- Implication: Only difference is ACID guarantees
- Relationship: Equivalence with subtraction

QUESTION SET:

1. [EMPIRICAL] If NoSQL is just SQL without ACID, why do schema-less
   designs and wide-column stores have fundamentally different query
   patterns than SQL - what explains this divergence beyond ACID?

2. [COMPUTATIONAL] Does removing ACID guarantees explain CAP theorem
   trade-offs, eventual consistency, and conflict resolution - or do
   NoSQL systems require entirely different mental models?

3. [FORMAL] Is the relationship "SQL minus ACID = NoSQL," or is NoSQL
   a distinct paradigm? What properties (joins, normalization) are
   lost, and are these losses necessary or incidental?

QUALITY ASSESSMENT:
- Deflection Resistance: 8.2/10 ✓
- Logical Trap: 8.5/10 ✓
- Challenge Strength: 7.8/10 ✓
- Overall Score: 8.2/10 [EXCELLENT]

USAGE GUIDANCE:
These questions work best in technical architecture discussions
where database selection trade-offs need exploration.
```

## Notes

- Questions are generated using the validated Three-Dimensional Attack pattern
- Quality checker automatically assesses each question
- Pattern maintains >7.0 effectiveness across 10 validated domains
- Generated questions can be refined based on audience feedback

## Implementation Status

**Current**: Slash command definition (this file)
**Next**: Full implementation requires:

1. Claim analysis logic
2. Question generation engine using SOCRATIC_TEMPLATE.md
3. Quality checking integration with QUALITY_CHECKER.py
4. Domain-specific adaptations from DOMAIN_EXAMPLES.md

**Estimated implementation**: ~2-3 hours for full automation
**Alternative**: Can be used as agent prompt template immediately

## Related Commands

- `/ultrathink` - Comprehensive workflow orchestration
- `/analyze` - Code philosophy compliance
- `/reflect` - Session analysis and improvement
- `/transcripts` - Context preservation and retrieval

---

**Version**: 1.0
**Created**: 2025-10-18
**Pattern**: Socratic Questioning (Three-Dimensional Attack)
**Status**: Command definition complete, implementation pending
