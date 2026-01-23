# Documentation Guidelines

This document defines the rules for writing high-quality software documentation in the amplihack project. These guidelines synthesize proven practices from the [Diataxis framework](https://diataxis.fr/), [Write the Docs](https://www.writethedocs.org/guide/writing/docs-principles/), and our project's ruthless simplicity philosophy.

## The Eight Rules of Good Documentation

### Rule 1: Location Matters - All Docs in `docs/`

**Principle**: Documentation must be discoverable. Orphan docs are dead docs.

**Requirements**:

- All documentation files go in the `docs/` directory
- Every doc MUST be linked from at least one other document (preferably `docs/index.md`)
- Use subdirectories for logical grouping (e.g., `docs/features/`, `docs/research/`)

**Example - Good**:

```
docs/
  index.md          <- Links to FEATURE_X.md
  FEATURE_X.md      <- Linked from index, discoverable
```

**Example - Bad**:

```
random_notes.md     <- Orphan file, no one will find it
docs/FEATURE_X.md   <- Not linked from anywhere
```

**Validation**: Run `grep -L "FEATURE_X" docs/*.md` - if your doc isn't referenced anywhere, fix it.

---

### Rule 2: Temporal Information Stays Out of the Repo

**Principle**: Repositories are for timeless truths, not point-in-time snapshots.

**What DOES NOT belong in docs/**:

- Status updates ("As of November 2025...")
- Test reports and results
- Meeting notes
- Progress reports
- Plans with dates
- Performance benchmarks (specific runs)

**Where this belongs instead**:
| Information Type | Where It Belongs |
|-----------------|------------------|
| Test results | CI logs, GitHub Actions |
| Status updates | GitHub Issues |
| Progress reports | Pull Request descriptions |
| Meeting decisions | Commit messages |
| Performance data | `~/.amplihack/.claude/runtime/logs/` |

**Example - Bad** (in docs/):

```markdown
## Status Report - November 2025

We completed 80% of the feature...
```

**Example - Good** (in PR description or Issue):

```markdown
## Status: November 2025

Sprint progress: 80% complete
```

---

### Rule 3: Ruthless Simplicity - Say More with Less

**Principle**: The best documentation is the simplest that achieves understanding.

**Requirements**:

- Use plain language accessible to the target audience
- Remove every word that doesn't add value
- Prefer bullet points over prose paragraphs
- One concept per section

**Example - Bad**:

```markdown
In order to effectively utilize the authentication mechanism that has been
implemented within this system, users will need to first ensure that they
have properly configured the appropriate environment variables as described
in the configuration section of this documentation.
```

**Example - Good**:

````markdown
## Authentication Setup

1. Set environment variables:
   ```bash
   export AUTH_TOKEN="your-token"
   ```
````

2. Restart the service

````

**Metrics**:
- Aim for 8th-grade reading level (Flesch-Kincaid)
- If a section exceeds 200 words, consider splitting

---

### Rule 4: Examples Must Be Real and Runnable

**Principle**: Fake examples teach fake patterns. Real examples work.

**Requirements**:
- All code examples MUST execute without modification
- Include expected output where relevant
- Use real data from the project, not "foo/bar" placeholders
- Test examples as part of CI when possible

**Example - Bad**:
```python
# Example usage (not tested)
result = some_function(foo, bar, baz)
# Returns: something useful
````

**Example - Good**:

```python
# Example: Analyze a Python file
from amplihack.analyzer import analyze_file

result = analyze_file("src/main.py")
print(result.complexity_score)
# Output: 12.5
```

**Exception**: Retcon'd documentation (written before implementation) can use realistic pseudocode, clearly marked:

```python
# [PLANNED - Not yet implemented]
# This will be the interface for the new feature
result = future_feature(input_data)
```

---

### Rule 5: Follow the Diataxis Framework

**Principle**: Different readers need different types of documentation.

**The Four Types**:

| Type            | Purpose         | User State              | Example                             |
| --------------- | --------------- | ----------------------- | ----------------------------------- |
| **Tutorial**    | Learning        | "Show me how"           | `docs/tutorials/getting-started.md` |
| **How-To**      | Problem-solving | "Help me do X"          | `docs/howto/deploy-to-azure.md`     |
| **Reference**   | Information     | "What are the options?" | `docs/reference/api.md`             |
| **Explanation** | Understanding   | "Why is it this way?"   | `docs/concepts/architecture.md`     |

**Requirements**:

- Each document should be ONE type only
- Clearly identify the type in the document or its location
- Don't mix tutorials with reference material

**Example - Good Structure**:

```
docs/
  tutorials/           # Learning-oriented
    getting-started.md
    first-agent.md
  howto/               # Task-oriented
    deploy-to-azure.md
    configure-hooks.md
  reference/           # Information-oriented
    api.md
    configuration.md
  concepts/            # Understanding-oriented
    architecture.md
    philosophy.md
```

---

### Rule 6: Structure for Scanability

**Principle**: Readers scan before they read. Help them find what they need.

**Requirements**:

- Start with the most important information (inverted pyramid)
- Use descriptive headings (not "Introduction", but "What This Does")
- Include a table of contents for docs > 100 lines
- Front-load key concepts in each paragraph

**Example - Bad**:

```markdown
# Introduction

This document will explain various aspects of the system...

## Background

Before we dive in, let's understand the history...
```

**Example - Good**:

```markdown
# Authentication System

The auth system validates user credentials using JWT tokens.

**Quick Start**: See [5-minute setup guide](#quick-start)

## Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
```

---

### Rule 7: Link Liberally, But Locally

**Principle**: Connect related concepts without creating external dependencies.

**Requirements**:

- Link to related docs within the project
- Prefer relative links over absolute URLs
- External links should be to authoritative, stable sources only
- Include context with links (don't just say "click here")

**Example - Bad**:

```markdown
For more info, click [here](./other.md).
See [this page](https://blog.random-person.com/2020/tutorial).
```

**Example - Good**:

```markdown
Learn more about [authentication configuration](./auth-config.md).
Based on [Anthropic's official Agent SDK docs](https://docs.anthropic.com/agent-sdk).
```

---

### Rule 8: Keep It Current or Kill It

**Principle**: Outdated documentation is worse than no documentation.

**Requirements**:

- Include `last_updated` in YAML frontmatter for complex docs
- Set a review schedule for critical docs (quarterly minimum)
- Delete docs that no longer apply (git preserves history)
- Mark deprecated content clearly before removal

**Example - Frontmatter**:

```yaml
---
title: API Reference
last_updated: 2025-11-15
review_schedule: quarterly
owner: platform-team
---
```

**Deprecation Pattern**:

```markdown
> **DEPRECATED**: This feature was removed in v2.0.
> See [New Feature](./new-feature.md) for the replacement.
```

---

## Documentation Checklist

Before submitting documentation, verify:

- [ ] File is in `docs/` directory
- [ ] Linked from `docs/index.md` or another discoverable doc
- [ ] No temporal/point-in-time information
- [ ] Written at appropriate reading level
- [ ] All examples are tested and runnable
- [ ] Follows single Diataxis type
- [ ] Has descriptive headings for scanning
- [ ] Internal links use relative paths
- [ ] External links are to authoritative sources
- [ ] Frontmatter includes metadata (for substantial docs)

---

## Quick Reference

| Do                     | Don't                        |
| ---------------------- | ---------------------------- |
| Put docs in `docs/`    | Scatter docs throughout repo |
| Link from index        | Create orphan documents      |
| Use simple language    | Over-explain or use jargon   |
| Show runnable examples | Use "foo/bar" placeholders   |
| One doc type per file  | Mix tutorials with reference |
| Structure for scanning | Wall of text                 |
| Link with context      | "Click here" links           |
| Delete outdated docs   | Let docs rot                 |

---

## Sources

- [Diataxis Framework](https://diataxis.fr/) - Documentation type system
- [Write the Docs](https://www.writethedocs.org/guide/writing/docs-principles/) - Community best practices
- [GitHub Documentation Guide](https://github.blog/developer-skills/documentation-done-right-a-developers-guide/) - Developer experience
- [Atlassian Documentation Best Practices](https://www.atlassian.com/blog/loom/software-documentation-best-practices) - Real examples
