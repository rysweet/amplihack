# Session Learning Skill

Cross-session learning system that preserves insights and injects relevant past knowledge.

## Quick Start

The skill works automatically via hooks:

- **At session stop**: Extracts learnings from the conversation
- **At session start**: Injects relevant learnings based on your task

Manual management:

```
/amplihack:learnings show         # Show all learnings
/amplihack:learnings show errors  # Show error-related learnings
/amplihack:learnings search import # Search for 'import' across all categories
```

## How It Works

### 1. Learning Extraction (Stop Hook)

When a session ends, the skill:

1. Analyzes the transcript for significant insights
2. Identifies error patterns, solutions, workflow tips
3. Extracts keywords, summary, and detailed insight
4. Stores in structured YAML files by category

### 2. Learning Injection (Session Start)

When a session starts, the skill:

1. Parses your initial prompt for keywords
2. Matches against stored learnings
3. Injects the top 3 most relevant learnings as context

### 3. Learning Categories

| Category       | What It Stores                       |
| -------------- | ------------------------------------ |
| `errors`       | Error patterns and their solutions   |
| `workflows`    | Process insights and shortcuts       |
| `tools`        | Tool usage patterns and gotchas      |
| `architecture` | Design decisions and trade-offs      |
| `debugging`    | Debugging strategies and root causes |

## File Structure

```
.claude/data/learnings/
  errors.yaml        # Error patterns
  workflows.yaml     # Workflow insights
  tools.yaml         # Tool patterns
  architecture.yaml  # Design decisions
  debugging.yaml     # Debug strategies
```

## YAML Format

Each learning follows this structure:

```yaml
learnings:
  - id: "err-001"
    created: "2025-11-25T12:00:00Z"
    keywords:
      - "import"
      - "circular"
    summary: "Circular imports cause ImportError"
    insight: |
      When module A imports from B and B imports from A,
      Python raises ImportError. Move shared code to third module.
    example: |
      # Extract shared types to types.py
      # Both modules import from types.py
    confidence: 0.9
    times_used: 3
```

## Relation to Existing Systems

| System           | Best For                          | Format   |
| ---------------- | --------------------------------- | -------- |
| DISCOVERIES.md   | Major findings with full context  | Markdown |
| PATTERNS.md      | Proven reusable patterns          | Markdown |
| Session Learning | Quick insights for auto-injection | YAML     |

All three systems are complementary:

- Session Learning captures quick insights automatically
- DISCOVERIES.md is for detailed write-ups of significant findings
- PATTERNS.md is for proven, reusable solutions with code examples

## Manual Commands

### Show Learnings

```
/amplihack:learnings show
/amplihack:learnings show errors
/amplihack:learnings show workflows
```

### Search Learnings

```
/amplihack:learnings search <query>
```

### Add Learning Manually

```
/amplihack:learnings add
```

Then follow the prompts to add category, keywords, summary, insight.

### View Statistics

```
/amplihack:learnings stats
```

## How Matching Works

Simple keyword overlap scoring:

1. Extract keywords from your task description
2. Compare against learning keywords
3. Calculate overlap score (0-1)
4. Rank by: overlap \* confidence \* recency
5. Return top 3 matches

No complex ML - just effective text matching.

## Best Practices

### Good Learning Examples

**Error Pattern:**

```yaml
keywords: [import, circular, dependency]
summary: "Circular imports cause module not found errors"
insight: "Move shared code to a separate module that both can import from"
```

**Workflow Insight:**

```yaml
keywords: [git, worktree, parallel, development]
summary: "Use git worktrees for parallel feature development"
insight: "Create worktree per feature to avoid branch switching overhead"
```

### When to Manually Add

- After solving a tricky problem
- When discovering a non-obvious tool behavior
- When finding a pattern that will definitely recur

### When to Skip

- Trivial typos or syntax errors
- Already documented in DISCOVERIES.md
- Too project-specific to reuse

## Limitations

1. **Keyword-based matching** - May miss conceptual similarities
2. **Local storage** - Doesn't sync across machines
3. **No auto-cleanup** - Review periodically for stale learnings

## Troubleshooting

**Learnings not being injected?**

- Check that `~/.amplihack/.claude/data/learnings/` directory exists
- Verify YAML files are valid
- Ensure keywords in learning match your task

**Too many irrelevant matches?**

- Be more specific with keywords
- Remove low-confidence learnings
- Use `/amplihack:learnings search` to check what's stored

## Contributing

To improve this skill:

1. Use it and provide feedback
2. Suggest better matching algorithms
3. Report false positives/negatives
4. Propose new learning categories
