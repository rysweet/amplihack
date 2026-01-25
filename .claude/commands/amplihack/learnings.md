---
description: View and manage cross-session learnings
arguments:
  - name: action
    description: "Action to perform: show, search, add, stats"
    required: false
  - name: query
    description: "Category name or search query"
    required: false
---

# /amplihack:learnings Command

Manage cross-session learnings stored in `~/.amplihack/.claude/data/learnings/`.

## Actions

### show [category]

Display learnings from all categories or a specific category.

**Categories:** errors, workflows, tools, architecture, debugging

**Examples:**

- `/amplihack:learnings show` - Show all learnings
- `/amplihack:learnings show errors` - Show only error learnings

### search <query>

Search across all learning categories for matching keywords.

**Examples:**

- `/amplihack:learnings search import` - Find learnings about imports
- `/amplihack:learnings search circular dependency` - Multi-word search

### add

Interactively add a new learning. You will be prompted for:

- Category (errors/workflows/tools/architecture/debugging)
- Keywords (comma-separated)
- Summary (one sentence)
- Insight (detailed explanation)
- Example (optional code)

### stats

Show learning statistics:

- Total learnings per category
- Most used learnings
- Recently added learnings
- Average confidence scores

## Execution

When this command is invoked:

1. **Parse action and query** from arguments
2. **Load learning files** from `~/.amplihack/.claude/data/learnings/`
3. **Execute requested action**:

### For `show`:

```python
# Read all YAML files in learnings directory
# Filter by category if specified
# Format learnings as readable markdown table

For each learning:
  Display:
    - ID and category
    - Keywords (comma-separated)
    - Summary
    - Confidence score
    - Times used
```

### For `search`:

```python
# Extract keywords from query
# Search across all category files
# Score matches by keyword overlap
# Return sorted results with context

For each match:
  Display:
    - Category and ID
    - Match score (percentage)
    - Summary
    - Full insight (if high score)
```

### For `add`:

```python
# Ask user for category
# Ask for keywords (suggest based on context)
# Ask for one-sentence summary
# Ask for detailed insight
# Ask for example (optional)
# Generate unique ID
# Append to appropriate YAML file
# Update last_updated timestamp
```

### For `stats`:

```python
# Load all learning files
# Calculate:
#   - Count per category
#   - Total learnings
#   - Average confidence
#   - Most used (by times_used)
#   - Recently added (last 5 by created date)
# Display formatted statistics
```

## Output Format

### Show Output

```markdown
## Learnings: [Category or All]

| ID      | Keywords         | Summary                            | Confidence |
| ------- | ---------------- | ---------------------------------- | ---------- |
| err-001 | import, circular | Circular imports cause ImportError | 0.9        |
| wf-002  | git, worktree    | Use worktrees for parallel work    | 0.85       |

**Total:** X learnings across Y categories
```

### Search Output

```markdown
## Search Results for: "[query]"

### 1. [Category]: [Summary] (Match: 85%)

**Keywords:** import, circular, dependency
**Insight:** [First 200 chars]...

### 2. [Category]: [Summary] (Match: 60%)

...

**Found:** X matching learnings
```

### Stats Output

```markdown
## Learning Statistics

| Category     | Count | Avg Confidence |
| ------------ | ----- | -------------- |
| errors       | 12    | 0.82           |
| workflows    | 8     | 0.78           |
| tools        | 5     | 0.85           |
| architecture | 3     | 0.90           |
| debugging    | 7     | 0.75           |

**Total:** 35 learnings

### Most Used

1. err-003: "Circular imports cause ImportError" (used 15 times)
2. wf-001: "Use pre-commit before push" (used 12 times)

### Recently Added

1. dbg-007: "Check Docker logs first" (2025-11-25)
2. tool-004: "Use --verbose for debugging" (2025-11-24)
```

## Related Files

- `~/.amplihack/.claude/data/learnings/errors.yaml` - Error patterns
- `~/.amplihack/.claude/data/learnings/workflows.yaml` - Workflow insights
- `~/.amplihack/.claude/data/learnings/tools.yaml` - Tool patterns
- `~/.amplihack/.claude/data/learnings/architecture.yaml` - Design decisions
- `~/.amplihack/.claude/data/learnings/debugging.yaml` - Debug strategies
- `~/.amplihack/.claude/skills/session-learning/SKILL.md` - Full skill documentation
