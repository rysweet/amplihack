# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered during development. It serves as a living knowledge base.

**Archive**: Entries older than 3 months are moved to [DISCOVERIES_ARCHIVE.md](./DISCOVERIES_ARCHIVE.md).

## Table of Contents

### Recent (November 2025)

- [Power-Steering Session Type Detection Fix](#power-steering-session-type-detection-fix-2025-11-25)
- [Transcripts System Architecture Validation](#transcripts-system-investigation-2025-11-22)
- [Hook Double Execution - Claude Code Bug](#hook-double-execution-claude-code-bug-2025-11-21)
- [StatusLine Configuration Missing](#statusline-configuration-missing-2025-11-18)
- [Power-Steering Path Validation Bug](#power-steering-path-validation-bug-2025-11-17)
- [Power Steering Branch Divergence](#power-steering-mode-branch-divergence-2025-11-16)
- [Mandatory End-to-End Testing Pattern](#mandatory-end-to-end-testing-pattern-2025-11-10)
- [Neo4j Container Port Mismatch](#neo4j-container-port-mismatch-bug-2025-11-08)
- [Parallel Reflection Workstream Success](#parallel-reflection-workstream-execution-2025-11-05)

### October 2025

- [Pattern Applicability Framework](#pattern-applicability-analysis-framework-2025-10-20)
- [Socratic Questioning Pattern](#socratic-questioning-pattern-2025-10-18)
- [Expert Agent Creation Pattern](#expert-agent-creation-pattern-2025-10-18)

---

## Entry Format Template

```markdown
## [Brief Title] (YYYY-MM-DD)

### Problem

What challenge was encountered?

### Root Cause

Why did this happen?

### Solution

How was it resolved? Include code if relevant.

### Key Learnings

What insights should be remembered?
```

---

## Power-Steering Session Type Detection Fix (2025-11-25)

### Problem

Power-steering incorrectly blocking investigation sessions with development-specific checks. Sessions like "Investigate SSH issues" were misclassified as DEVELOPMENT.

### Root Cause

`detect_session_type()` relied solely on tool-based heuristics. Troubleshooting sessions involve Bash commands and doc updates, matching development patterns.

### Solution

Added **keyword-based detection** with priority over tool heuristics. Check first 5 user messages for investigation keywords (investigate, troubleshoot, diagnose, debug, analyze).

### Key Learnings

**User intent (keywords) is more reliable than tool usage patterns** for session classification.

---

## Transcripts System Investigation (2025-11-22)

### Problem

Needed validation of amplihack's transcript architecture vs Microsoft Amplifier approach.

### Key Findings

- **Decision**: Maintain current 2-tier builder architecture
- **Rationale**: Perfect philosophy alignment (30/30) + proven stability
- **Architecture**: ClaudeTranscriptBuilder + CodexTranscriptsBuilder with 4 strategic hooks
- **5 advantages over Amplifier**: Session isolation, human-readable Markdown, fail-safe architecture, original request tracking, zero external dependencies

### Key Learnings

Independent innovation can be better than adopting external patterns. Session isolation beats centralized state.

---

## Hook Double Execution - Claude Code Bug (2025-11-21)

### Problem

SessionStart and Stop hooks execute **twice per session** with different PIDs.

### Root Cause

**Claude Code internal bug #10871** - Hook execution engine spawns two separate processes regardless of configuration. Our config is correct per schema.

### Solution

**NO CODE FIX AVAILABLE**. Accept duplication as known limitation. Hooks are idempotent, safe but wasteful (~2 seconds per session).

### Key Learnings

1. Configuration was correct - the `"hooks": []` wrapper is required by schema
2. Schema validation prevents incorrect "fixes"
3. Upstream bugs affect downstream projects

**Tracking**: Claude Code GitHub Issue #10871

---

## StatusLine Configuration Missing (2025-11-18)

### Problem

Custom status line feature fully implemented but never configured during installation.

### Root Cause

Both installation templates (install.sh and uvx_settings_template.json) excluded statusLine configuration.

### Solution (Issue #1433)

Added statusLine config to both templates with appropriate path formats.

### Key Learnings

Feature discoverability requires installation automation. Templates should match feature implementations.

---

## Power-Steering Path Validation Bug (2025-11-17)

### Problem

Power-steering fails with path validation error. Claude Code stores transcripts in `~/.claude/projects/` which is outside project root.

### Root Cause

`_validate_path()` too strict - only allows project root and temp directories.

### Solution

Whitelist `~/.claude/projects/` directory in path validation.

### Key Learnings

1. Fail-Open Design is critical
2. Security vs Usability requires balance
3. "Enabled" doesn't always mean "Working"

---

## Power Steering Mode Branch Divergence (2025-11-16)

### Problem

Power steering feature not activating - appeared disabled.

### Root Cause

**Feature was missing from branch entirely**. Branch diverged from main BEFORE power steering was merged.

### Solution

Sync branch with main: `git rebase origin/main`

### Key Learnings

"Feature not working" can mean "Feature not present". Always check git history: `git log HEAD...origin/main`

---

## Mandatory End-to-End Testing Pattern (2025-11-10)

### Problem

Code committed after unit tests and reviews but missing real user experience validation.

### Solution

**ALWAYS test with `uvx --from <branch>` before committing**:

```bash
uvx --from git+https://github.com/org/repo@branch package command
```

This verifies: package installation, dependency resolution, actual user workflow, error messages, config updates.

### Key Learnings

Testing hierarchy (all required):

1. Unit tests
2. Integration tests
3. Code reviews
4. **End-to-end user experience test** (MANDATORY BEFORE COMMIT)

---

## Neo4j Container Port Mismatch Bug (2025-11-08)

### Problem

Startup fails with container conflicts when starting in different directory than where Neo4j container was created.

### Root Cause

`is_our_neo4j_container()` checked container NAME but not ACTUAL ports. `.env` can become stale.

### Solution

Added `get_container_ports()` using `docker port` to query actual ports. Auto-update `.env` to match reality.

### Key Learnings

Container Detection != Port Detection. `.env` files can lie. Docker port command is canonical.

---

## Parallel Reflection Workstream Execution (2025-11-05)

### Context

Successfully executed 13 parallel full-workflow tasks simultaneously using worktree isolation.

### Key Metrics

- 13 issues created (#1089-#1101)
- 13 PRs with 9-10/10 philosophy compliance
- 100% success rate
- ~18 minutes per feature average

### Patterns That Worked

1. **Worktree Isolation**: Each feature in separate worktree
2. **Agent Specialization**: prompt-writer → architect → builder → reviewer
3. **Cherry-Pick for Divergent Branches**: Better than rebase for parallel work
4. **Documentation-First**: Templates reduce decision overhead

### Key Learnings

Parallel execution scales well. Worktrees provide perfect isolation. Philosophy compliance maintained at scale.

---

## Pattern Applicability Analysis Framework (2025-10-20)

### Context

Evaluated PBZFT vs N-Version Programming. PBZFT would be 6-9x more complex with zero benefit.

### Six Meta-Patterns Identified

1. **Threat Model Precision**: Match defense to actual failure mode
2. **Voting vs Expert Judgment**: Expert review for quality, voting for adversarial consensus
3. **Distributed Systems Applicability Test**: Most patterns don't apply to AI (different trust model)
4. **Complexity-Benefit Ratio**: Require >3.0 ratio to justify complexity
5. **Domain Appropriateness Check**: Best practices are domain-specific
6. **Diversity as Error Reduction**: Independent implementations reduce correlated errors

### Key Learnings

- Threat model mismatch is primary source of inappropriate pattern adoption
- Distributed systems patterns rarely map to AI systems
- Always verify failure modes match before importing patterns

**Note**: Consider promoting to PATTERNS.md if framework used 3+ times.

---

## Socratic Questioning Pattern (2025-10-18)

### Context

Developed effective method for deep, probing questions in knowledge-builder scenarios.

### Three-Dimensional Attack Strategy

1. **Empirical**: Challenge with observable evidence
2. **Computational**: Probe tractability and complexity
3. **Formal Mathematical**: Demand precise relationships

### Usage Context

- When: Knowledge exploration, challenging claims, surfacing assumptions
- When NOT: Simple factual questions, time-sensitive decisions

**Status**: 1 successful usage. Needs 2-3 more before promoting to PATTERNS.md.

---

## Expert Agent Creation Pattern (2025-10-18)

### Context

Created Rust and Azure Kubernetes expert agents with 10-20x learning speedup.

### Pattern Components

1. **Focused Knowledge Base**: 7-10 core concepts in Q&A format
2. **Structure**: `Knowledge.md`, `KeyInfo.md`, `HowToUseTheseFiles.md`
3. **Expert Agent**: References knowledge base, defines competencies

### Key Learnings

- Focused beats breadth (7 concepts > 270 generic questions)
- Q&A format superior to documentation style
- Real code examples are essential (2-3 per concept)

**Note**: Consider promoting to PATTERNS.md if used 3+ times.

---

## Remember

- Document immediately while context is fresh
- Include specific error messages
- Show code that fixed the problem
- Update PATTERNS.md when a discovery becomes reusable
- Archive entries older than 3 months to DISCOVERIES_ARCHIVE.md
