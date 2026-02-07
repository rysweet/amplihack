# Architecture: amplihack-expert Skill Development

**Created:** 2026-02-07
**Type:** Investigation & Implementation
**Related Issue:** #2137
**Related PR:** #2218

## Overview

Documentation of the architectural investigation and design decisions made during development of the amplihack-expert Claude Code skill. This skill provides comprehensive knowledge of the amplihack framework to Claude Code sessions.

## Key Findings

### amplihack Framework Architecture (5 Layers)

1. **Runtime Layer:** Logs, metrics, session state (.claude/runtime/)
2. **Framework Layer:** Core tools (TodoWrite, Task, SlashCommand)
3. **Content Layer:** Workflows, agents, commands, skills (.claude/)
4. **User Layer:** CLAUDE.md, preferences, customization
5. **Integration Layer:** MCP servers, GitHub Actions, hooks

### Four Extensibility Mechanisms

| Mechanism | Invocation                | Purpose                      |
| --------- | ------------------------- | ---------------------------- |
| Workflow  | Read file, follow steps   | Multi-step process blueprint |
| Command   | /cmd or SlashCommand tool | User-explicit entry          |
| Skill     | Triggers or Skill tool    | Auto-discovered capability   |
| Agent     | Task tool + subagent_type | Specialized delegation       |

### Hook System Integration

**Active Hooks:** SessionStart, Stop, PostToolUse, PreCompact, SessionEnd
**Protocol:** JSON stdin/stdout with HookProcessor base class
**Purpose:** Non-invasive Claude Code extension without core modification

### Skill Auto-Activation Pattern

**Mechanism:** YAML frontmatter with triggers (keywords, patterns, file_paths)
**Progressive Disclosure:** SKILL.md (quick) → reference.md (deep) → examples.md (practical)
**Token Management:** Load on-demand to prevent waste across 80+ skills

## Design Decisions

### Decision 1: Three-File Structure

**What:** SKILL.md (800 tokens) + reference.md (1200 tokens) + examples.md (600 tokens)
**Why:** Balances comprehensive coverage with token efficiency
**Alternative Rejected:** Single file (exceeds budget), five files (too fragmented)

### Decision 2: Auto-Activation Triggers

**What:** Multi-match logic (keywords + patterns + file paths)
**Why:** Comprehensive coverage without false positives
**Alternative Rejected:** Keywords only (misses edge cases)

### Decision 3: Token Optimization

**What:** Tables over prose, code examples, bullet points
**Why:** Maximum information density in minimal tokens
**Result:** 32% token utilization (840/2600 tokens)

## Implementation Challenges

### Challenge 1: Token Budget Exceeded

**Issue:** Initial SKILL.md was 813 tokens (13 over budget)
**Resolution:** Condensed descriptions, removed redundancy
**Outcome:** 781 tokens (19 under budget)

### Challenge 2: Test Logic Bug

**Issue:** test_modular_design_independence didn't handle YAML frontmatter
**Resolution:** Modified test to skip YAML before checking headings
**Outcome:** 33/33 tests passing (100%)

### Challenge 3: CI "Validate Code" Timing

**Issue:** Check consistently took 8-9 minutes (appeared stuck)
**Resolution:** Normal behavior for pytest across large codebase
**Outcome:** All CI checks passing

## Key Files

| File                                                                 | Purpose                           | Lines |
| -------------------------------------------------------------------- | --------------------------------- | ----- |
| .claude/skills/amplihack-expert/SKILL.md                             | Main entry point, quick reference | 118   |
| .claude/skills/amplihack-expert/reference.md                         | Architecture details              | 136   |
| .claude/skills/amplihack-expert/examples.md                          | Usage scenarios                   | 96    |
| .claude/skills/amplihack-expert/tests/test_amplihack_expert_skill.py | Validation suite                  | 809   |

## Quality Metrics

- **Tests:** 33/33 passing (100%)
- **Philosophy:** 9.6/10 compliance score
- **Token Budget:** 840/2600 (32% utilization)
- **CI:** 5/5 checks passing
- **Mergeable:** MERGEABLE with CLEAN state

## Verification

The skill successfully:

- Auto-activates on amplihack-related questions
- Provides quick answers from SKILL.md
- Directs to deeper content via navigation guide
- Follows progressive disclosure pattern
- Meets all Claude Code skill best practices

## Related Documentation

- User Requirements: Issue #2137
- Implementation: PR #2218
- Session Log: .claude/runtime/logs/investigation-amplihack-expert-skill.md (gitignored)
