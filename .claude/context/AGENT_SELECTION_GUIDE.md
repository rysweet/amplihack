# Agent Selection Guide

**AI Context**: This guide helps Claude Code's orchestrator select the correct agent when multiple agents have overlapping capabilities.

**Import**: This file should be imported at session start for AI behavioral guidance.

## Architect Selection

**Multiple architect variants exist** - Choose the right one for your task:

### architect (core)
**Use when**: General design, problem decomposition, module specifications
**Capabilities**: Problem analysis, system design, module specs, pre-commit validation
**Example**: "Design authentication system" → architect

### amplifier-cli-architect
**Use when**: CLI applications, hybrid code/AI systems
**Capabilities**: CONTEXTUALIZE/GUIDE/VALIDATE modes, ccsdk_toolkit integration
**Example**: "Design CLI for data processing" → amplifier-cli-architect

### zen-architect
**Use when**: Philosophy compliance reviews, simplicity validation
**Capabilities**: A-F grading, regenerability assessment, philosophy violation detection
**Example**: "Validate this architecture for simplicity" → zen-architect

### visualization-architect
**Use when**: Architecture diagrams, visual documentation
**Capabilities**: ASCII diagrams, Mermaid charts, system visualization
**Example**: "Create system diagram" → visualization-architect

**Decision Matrix**:
```
Need architecture help?
├─ General design/problem analysis? → architect (core)
├─ CLI application architecture? → amplifier-cli-architect
├─ Philosophy compliance review? → zen-architect
└─ Visual documentation needed? → visualization-architect
```

---

## Overlapping Agent Pairs

This guide clarifies when to use overlapping agents that serve different but related purposes.

## patterns vs ambiguity

**70% overlap in functionality** - Both handle diverse perspectives, but different approaches:

### patterns
**Use when**: Finding signal in diversity, emergent pattern recognition
**Approach**: Orchestrates diversity to discover unifying patterns
**Output**: Pattern catalogs, synthesis of multiple viewpoints
**Example**: "Analyze these 5 different approaches and find the common pattern"

### ambiguity
**Use when**: Preserving uncertainty, mapping unknowns, multiple valid interpretations
**Approach**: Preserves contradictions as valuable knowledge
**Output**: Tension maps, uncertainty documentation, ambiguity preservation
**Example**: "Document why both approaches are valid and preserve the trade-offs"

**Decision Matrix**:
```
Need to handle diverse perspectives?
├─ Want to find unifying patterns? → patterns
└─ Want to preserve contradictions? → ambiguity
```

---

## analyzer vs knowledge-archaeologist

**Different temporal focus** - Both analyze code, but different time dimensions:

### analyzer
**Use when**: Current-state analysis, immediate understanding
**Modes**: TRIAGE (quick overview), DEEP (detailed analysis), SYNTHESIS (integration)
**Focus**: What the code IS now
**Output**: Current architecture, dependencies, complexity metrics
**Example**: "Analyze this module and explain how it works"

### knowledge-archaeologist
**Use when**: Historical context, evolution understanding, git archaeology
**Modes**: Temporal analysis, lineage tracing, paradigm shift detection
**Focus**: How the code EVOLVED and WHY
**Output**: Temporal layers, evolution history, abandoned approaches, decision context
**Example**: "Why did we choose this pattern? What alternatives were tried?"

**Decision Matrix**:
```
Need code understanding?
├─ Current state, how it works now? → analyzer
└─ Historical context, why it evolved? → knowledge-archaeologist
```

---

## Fix Workflow Agents

**Different stages of development** - Three agents for different failure points:

### pre-commit-diagnostic
**Use when**: Pre-commit hooks fail locally (BEFORE push)
**Stage**: Development → Commit (blocked)
**Handles**: Formatting, linting, type checking, local quality gates
**Trigger**: "Pre-commit failed", "Can't commit", "Hooks failing"
**Output**: Fixes all issues to make code committable

### ci-diagnostic-workflow
**Use when**: CI checks fail remotely (AFTER push)
**Stage**: Commit → CI Pipeline (failing)
**Handles**: Build failures, test failures, CI-specific issues
**Trigger**: "CI failing", "Fix CI", "Make PR mergeable"
**Output**: Iterates until PR is mergeable (never auto-merges)

### fix-agent
**Use when**: General fix needed, pattern unclear, or quick resolution wanted
**Stage**: Any (auto-detects pattern and scope)
**Handles**: All common patterns (import, CI, test, config, quality, logic)
**Modes**: QUICK (<5min template), DIAGNOSTIC (root cause), COMPREHENSIVE (full workflow)
**Trigger**: "Fix this", specific error patterns
**Output**: Pattern-specific fixes using templates or deep analysis

**Decision Matrix**:
```
Something broken?
├─ Pre-commit hooks blocking commit? → pre-commit-diagnostic
├─ CI failing after push? → ci-diagnostic-workflow
└─ General fix or unclear stage? → fix-agent (auto-detects)
```

**Integration Protocol**:
1. **Local Development**: Use `pre-commit-diagnostic` for commit blockers
2. **After Push**: Use `ci-diagnostic-workflow` for CI failures
3. **Anytime**: Use `fix-agent` for general fixes (it will route to appropriate workflow)

---

## Fault Tolerance Agents

**Different consensus strategies** - All three are fault-tolerance patterns with distinct approaches:

### fallback-cascade
**Strategy**: Graceful degradation (optimal → pragmatic → minimal)
**Use when**: Need reliability with fallbacks, external API calls
**Cost**: 1.1-2x (only on failures)
**Example**: "Generate docs with fallback if API unavailable"

### n-version-validator
**Strategy**: N independent solutions, select best through comparison
**Use when**: Critical code needing high correctness (security, core algorithms)
**Cost**: 3-4x execution time
**Example**: "Implement JWT validation with N-version approach"

### multi-agent-debate
**Strategy**: Multiple perspectives debate to consensus
**Use when**: Complex decisions, architectural trade-offs
**Cost**: 2-3x execution time
**Example**: "Should we use PostgreSQL or Redis?"

**Decision Matrix**:
```
Need fault tolerance?
├─ Reliability with fallbacks? → fallback-cascade
├─ Critical correctness needed? → n-version-validator
└─ Complex decision consensus? → multi-agent-debate
```

---

## When in Doubt

**General Guidelines**:
- Start with the **simpler** agent (architect > zen-architect, analyzer > knowledge-archaeologist)
- Use **specialized** agents only when you need their specific features
- **Combine** agents when you need multiple perspectives (e.g., architect + zen-architect)
- Check **CLAUDE.md** for full agent catalog and delegation triggers

**Still Unclear?** Use the `ambiguity` agent to help you decide!
