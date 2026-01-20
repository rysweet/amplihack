# DISCOVERIES Archive

**Archived**: 2025-11-25

This file contains historical discoveries that have been resolved, superseded, or are no longer actively referenced. They're preserved here for historical context and git archaeology.

**To restore an entry**: If a pattern re-emerges or becomes relevant again, move it back to DISCOVERIES.md.

---

## Table of Contents

1. [Project Initialization (2025-01-16)](#project-initialization-2025-01-16)
2. [Anti-Sycophancy Guidelines (2025-01-17)](#anti-sycophancy-guidelines-implementation-2025-01-17)
3. [Enhanced Agent Delegation (2025-01-17)](#enhanced-agent-delegation-instructions-2025-01-17)
4. [Agent Priority Hierarchy Flaw (2025-01-23)](#agent-priority-hierarchy-critical-flaw-2025-01-23)
5. [Pre-commit Hooks Over-Engineering (2025-09-17)](#pre-commit-hooks-over-engineering-2025-09-17)
6. [CI Failure Resolution Process (2025-09-17)](#ci-failure-resolution-process-analysis-2025-09-17)
7. [Context Preservation Success (2025-09-23)](#context-preservation-implementation-success-2025-09-23)
8. [Reflection System Data Flow Fix (2025-09-26)](#reflection-system-data-flow-fix-2025-09-26)
9. [Claude-Trace UVX Argument Issue (2025-09-26)](#claude-trace-uvx-argument-passthrough-issue-2025-09-26)

---

## Project Initialization (2025-01-16)

**Status**: Historical - foundational context

### Issue

Setting up the agentic coding framework with proper structure and philosophy.

### Solution

Created comprehensive `.claude` directory structure with context files, agent definitions, command system, hook system, and runtime directories.

### Key Learnings

1. Structure enables AI effectiveness
2. Philosophy guides decisions
3. Patterns prevent wheel reinvention
4. Agent specialization works

---

## Anti-Sycophancy Guidelines Implementation (2025-01-17)

**Status**: Resolved - now codified in TRUST.md

### Issue

Sycophantic AI behavior erodes user trust.

### Solution

Created TRUST.md with 7 anti-sycophancy rules. Added to standard imports in CLAUDE.md.

### Key Learnings

Trust comes from honesty, not harmony. Directness builds credibility.

---

## Enhanced Agent Delegation Instructions (2025-01-17)

**Status**: Resolved - now in CLAUDE.md

### Issue

CLAUDE.md had minimal guidance on when to use specialized agents.

### Solution

Added "GOLDEN RULE" emphasizing orchestration, specific delegation triggers for all agents, parallel execution examples.

### Key Learnings

Explicit triggers drive usage. Orchestration mindset matters. Documentation drives behavior.

---

## Agent Priority Hierarchy Critical Flaw (2025-01-23)

**Status**: Resolved - USER_REQUIREMENT_PRIORITY.md created

### Issue

Agents were overriding explicit user requirements in favor of philosophy.

### Solution

Created USER_REQUIREMENT_PRIORITY.md with mandatory hierarchy. Updated critical agents with requirement preservation checks.

### Key Learnings

User explicit requirements are sacred. Philosophy guides HOW, not WHAT.

---

## Pre-commit Hooks Over-Engineering (2025-09-17)

**Status**: Resolved

### Issue

Initial pre-commit had 11+ hooks and 5 config files, violating ruthless simplicity.

### Solution

Reduced to 7 essential hooks. Deleted custom philosophy checker, detect-secrets, complex pytest hook.

### Key Learnings

Start minimal, grow as needed. Philosophy enforcement belongs in review, not automation.

---

## CI Failure Resolution Process Analysis (2025-09-17)

**Status**: Lessons captured, aged out

### Issue

Complex CI debugging took 45 minutes due to version mismatches and merge conflicts.

### Solution

Multi-agent orchestration approach. Identified CI Version Mismatch and Silent Pre-commit Hook Failure patterns.

### Key Learnings

Agent orchestration works for debugging. Environment parity is critical. Pattern recognition accelerates resolution.

---

## Context Preservation Implementation Success (2025-09-23)

**Status**: Resolved - system implemented

### Issue

Original user requests lost during context compaction.

### Solution

Four-component system: Context Preservation, Enhanced Session Start Hook, PreCompact Hook, Transcript Management.

### Key Learnings

Proactive preservation beats reactive recovery. Session-level context injection is most effective.

---

## Reflection System Data Flow Fix (2025-09-26)

**Status**: Resolved

### Issue

AI-powered reflection failing silently with "No session messages found".

### Solution

Fixed interface contract - stop.py now passes messages directly to reflection.py.

### Key Learnings

Data flow mismatches between legacy and new systems cause silent failures.

---

## Claude-Trace UVX Argument Passthrough Issue (2025-09-26)

**Status**: Resolved

### Issue

UVX argument passthrough failing for claude-trace integration.

### Solution

Modified `build_claude_command()` in launcher/core.py to handle claude-trace's `--run-with chat` requirement.

### Key Learnings

Different tools require different argument structures. Test real deployment scenarios.

---

## End of Archive

For current discoveries, see [DISCOVERIES.md](./DISCOVERIES.md).
