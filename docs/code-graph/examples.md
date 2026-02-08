# Code Graph Examples

Real-world usage scenarios and workflows with code graph commands.

## Contents

- [Initial Setup](#initial-setup)
- [Daily Development](#daily-development)
- [Code Review](#code-review)
- [Architecture Documentation](#architecture-documentation)
- [Refactoring](#refactoring)
- [CI/CD Integration](#cicd-integration)
- [Team Onboarding](#team-onboarding)
- [Dependency Analysis](#dependency-analysis)

---

## Initial Setup

### First-Time Graph Creation

**Scenario:** You've just installed amplihack and want to visualize your codebase.

```bash
# Step 1: Navigate to your project
cd ~/projects/myapp

# Step 2: Create the graph database
/code-graph-index

# Output:
# Scanning repository: /home/user/projects/myapp
# Found Python files: 89
# Indexing modules: ████████████████████████ 100%
# Database created: ~/.amplihack/memory_kuzu.db
# Total nodes: 1,247 | Total edges: 1,893

# Step 3: View the graph
/code-graph

# Output:
# Generated: docs/code-graph/code-graph-full.png
# Opening in default viewer...
# ✓ Complete
```

**Result:** You now have:

- Graph database at `~/.amplihack/memory_kuzu.db`
- Visualization at `docs/code-graph/code-graph-full.png`
- Understanding of module dependencies

**Time:** 2-5 minutes depending on codebase size

---

## Daily Development

### After Adding New Feature

**Scenario:** You added a new `billing` module and want to see how it fits into the architecture.

```bash
# Your changes
git status
# Modified: src/api/routes.py
# Added: src/billing/__init__.py
# Added: src/billing/stripe.py
# Added: src/billing/invoices.py

# Update the graph with new files
/code-graph-update

# Output:
# Files to process: 4
# Updating graph: ████████████████████████ 100%
# Changes: 8 nodes added, 12 edges added
# ✓ Database updated

# View updated graph
/code-graph-core

# Output:
# Core modules: 24 (including new billing module)
# Generated: docs/code-graph/code-graph-core.png
# ✓ Complete
```

**What you see:**

- New `billing` module in the graph
- Connections to `api.routes` (caller)
- Dependencies on `database` and `models.invoice`
- No unexpected circular dependencies

**Time:** 30 seconds

---

### Quick Architecture Check

**Scenario:** Before standup meeting, quickly verify your changes don't create circular dependencies.

```bash
# Update graph with today's work
/code-graph-update

# View core architecture
/code-graph-core
```

**In the visualization:**

- Green nodes: No dependency issues
- Red arrows: Circular dependencies (if any)
- Yellow nodes: High coupling (many dependencies)

**Decision:** Refactor `user_service.py` because it has 15 incoming dependencies (yellow node).

**Time:** 1 minute

---

## Code Review

### Preparing PR Visualization

**Scenario:** Creating a PR and want to include architecture diagrams showing your changes.

```bash
# Update graph with PR changes
git checkout feature/user-auth
/code-graph-update

# Generate images without opening viewer
/code-graph-images

# Output:
# Generating full graph: docs/code-graph/code-graph-full.png
# Generating core graph: docs/code-graph/code-graph-core.png
# ✓ Files created: 2
# Total size: 3.1 MB

# Add to PR description
echo "## Architecture Changes" >> pr-description.md
echo "![Core Architecture](../docs/code-graph/code-graph-core.png)" >> pr-description.md
echo "![Full Graph](../docs/code-graph/code-graph-full.png)" >> pr-description.md
```

**PR includes:**

- Before/after architecture comparison
- Visual proof of no circular dependencies
- Impact analysis (which modules affected)

**Reviewer feedback:** "Love the graph! Shows exactly what changed and why it's safe."

**Time:** 2 minutes

---

### Reviewing Someone Else's PR

**Scenario:** Reviewing a large PR and need to understand the architectural impact.

```bash
# Check out the PR branch
gh pr checkout 142

# Rebuild graph for this branch
/code-graph-index

# View changes
/code-graph-core
```

**Questions answered by the graph:**

- Does this PR introduce circular dependencies?
- How many modules are affected?
- Are new dependencies appropriate?
- Is the change localized or system-wide?

**Review comment:** "The graph shows `payment_processor` now depends on `email_service`. Should this go through the event bus instead for decoupling?"

**Time:** 3 minutes

---

## Architecture Documentation

### Creating Documentation Diagrams

**Scenario:** Writing architecture documentation for new team members.

```bash
# Generate high-resolution images
export AMPLIHACK_GRAPH_RESOLUTION="8192x6144"
/code-graph-images

# Output:
# docs/code-graph/code-graph-full.png (high-res)
# docs/code-graph/code-graph-core.png (high-res)

# Create architecture document
cat > docs/architecture/system-overview.md << 'EOF'
# System Architecture

## Core Modules

![Core Architecture](../code-graph/code-graph-core.png)

The system consists of 24 core modules organized in 3 layers:

1. **API Layer**: HTTP routes and handlers
2. **Service Layer**: Business logic
3. **Data Layer**: Database and models

## Full Dependency Graph

![Full Graph](../code-graph/code-graph-full.png)

Complete module dependencies including utilities and tests.
EOF
```

**Documentation includes:**

- Current architecture (auto-generated, always accurate)
- Visual module relationships
- No manual diagram maintenance

**Benefit:** Diagrams update automatically when code changes

**Time:** 5 minutes

---

### Monthly Architecture Review

**Scenario:** Monthly architecture review meeting to identify technical debt.

```bash
# Generate fresh graphs
/code-graph-index
/code-graph-images

# Analyze the full graph for issues
# (Manually review the generated images)
```

**Issues identified in graph:**

- `utils.helpers` imported by 47 modules (God object)
- Circular dependency: `auth` ↔ `session` ↔ `user`
- Test files importing from `src/` (should be independent)

**Action items:**

- Break up `utils.helpers` into focused modules
- Resolve circular dependency with interfaces
- Fix test isolation issues

**Time:** 30 minutes (monthly meeting)

---

## Refactoring

### Before Major Refactoring

**Scenario:** Planning to refactor the authentication system.

```bash
# Baseline graph before refactoring
/code-graph-index
/code-graph

# Identify all dependencies on auth module
# Review graph image: search for "auth" nodes
```

**Graph analysis:**

- `auth` module has 23 incoming dependencies
- `auth` imports: `database`, `models.user`, `crypto`, `session`
- Circular dependency: `auth` → `session` → `auth`

**Refactoring plan:**

1. Break circular dependency first
2. Create `auth.interfaces` for abstract contracts
3. Migrate 23 callers one by one
4. Remove old `auth` module

**Benefit:** Complete picture before touching code

**Time:** 15 minutes

---

### After Major Refactoring

**Scenario:** Completed authentication refactor, verify architecture improved.

```bash
# Rebuild graph with refactored code
/code-graph-index

# Compare core architecture
/code-graph-core
```

**Before (old graph):**

- 1 monolithic `auth` module
- Circular dependency
- 23 incoming edges

**After (new graph):**

- 4 focused modules: `auth.core`, `auth.handlers`, `auth.tokens`, `auth.session`
- No circular dependencies
- Clear layering: handlers → core → tokens

**Validation:** Architecture improved, refactoring successful

**Time:** 2 minutes

---

## CI/CD Integration

### Automated Graph Generation

**Scenario:** Generate graphs automatically on every PR for documentation.

**.github/workflows/docs.yml:**

```yaml
name: Documentation

on: [pull_request]

jobs:
  generate-graphs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install amplihack
        run: pip install amplihack

      - name: Generate code graphs
        run: |
          amplihack --eval "/code-graph-index"
          amplihack --eval "/code-graph-images"

      - name: Upload graph artifacts
        uses: actions/upload-artifact@v4
        with:
          name: code-graphs
          path: docs/code-graph/*.png

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '📊 Code graphs generated! [View artifacts](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})'
            })
```

**Result:** Every PR includes:

- Automated graph generation
- Graph images as artifacts
- PR comment with link to graphs

**Benefit:** Continuous architecture visibility

**Time:** 5 minutes setup (runs automatically)

---

### Detecting Architecture Violations

**Scenario:** Fail CI if PR introduces circular dependencies.

**CI script (`.github/scripts/check-architecture.py`):**

```python
#!/usr/bin/env python3
import sys
import subprocess

# Generate graph
subprocess.run(["amplihack", "--eval", "/code-graph-index"], check=True)

# Check for circular dependencies
# (This is pseudocode - actual implementation would query the database)
result = subprocess.run(
    ["python", "/tmp/code_graph_checker.py", "--check-cycles"],
    capture_output=True
)

if result.returncode != 0:
    print("❌ Circular dependencies detected!")
    print(result.stdout.decode())
    sys.exit(1)

print("✓ No circular dependencies")
```

**CI integration:**

```yaml
- name: Check architecture
  run: .github/scripts/check-architecture.py
```

**Result:** PRs blocked if they introduce architectural issues

**Time:** 10 minutes setup (runs automatically)

---

## Team Onboarding

### New Developer First Day

**Scenario:** New team member needs to understand the codebase.

```bash
# From their machine
cd ~/projects/company-app

# Generate initial graph
/code-graph-index

# Show high-level architecture
/code-graph-core
```

**Walkthrough with graph open:**

1. "Here's our core architecture (point to core graph)"
2. "API layer at top, services in middle, data at bottom"
3. "This module (`user_service`) is what you'll work on"
4. "It depends on: `database`, `models.user`, `auth.tokens`"
5. "These modules depend on it: `api.users`, `api.admin`"

**New developer:** "This makes everything so clear! Can I keep this graph updated?"

**Answer:** "Yes, run `/code-graph-update` after pulling changes."

**Benefit:** Visual understanding beats 1000 words

**Time:** 10 minutes (one-time explanation)

---

### Understanding Legacy Code

**Scenario:** Working on a legacy module no one understands anymore.

```bash
# Generate graph
/code-graph-index

# View full graph
/code-graph

# Search for legacy module in image
# (Visual search for "legacy_processor" node)
```

**Graph reveals:**

- `legacy_processor` imported by 8 modules
- `legacy_processor` imports: 15 different modules
- High coupling (yellow node)
- Main callers: `api.jobs`, `scheduler`, `webhook_handler`

**Strategy:**

1. Start with tests for `legacy_processor`
2. Identify pure functions (no dependencies)
3. Extract to new focused modules
4. Gradually migrate 8 callers

**Benefit:** Systematic understanding of complex legacy code

**Time:** 20 minutes analysis

---

## Dependency Analysis

### Finding Unused Modules

**Scenario:** Identify modules with no incoming dependencies (potentially unused).

```bash
# Generate graph
/code-graph-index

# View full graph
/code-graph

# Look for isolated nodes (no incoming edges)
```

**Candidates for removal:**

- `old_importer.py` - No incoming edges
- `temp_fix.py` - No incoming edges
- `migration_helper.py` - No incoming edges

**Verification:**

```bash
# Check git history
git log --oneline old_importer.py
# Last commit: 2 years ago

# Confirm unused
grep -r "old_importer" src/
# No matches

# Safe to delete
git rm old_importer.py
```

**Benefit:** Data-driven dead code removal

**Time:** 15 minutes

---

### Identifying Dependency Hotspots

**Scenario:** Find modules with too many dependencies (high coupling).

```bash
# Generate graph
/code-graph-index

# View core graph (easier to spot issues)
/code-graph-core
```

**Analysis:**

- `utils.helpers` - 47 incoming edges (red flag!)
- `models.user` - 31 incoming edges (expected for domain model)
- `database` - 28 incoming edges (expected for infrastructure)

**Action:** Refactor `utils.helpers`:

```bash
# Before: 47 modules import utils.helpers
# After split:
# - utils.string_helpers (12 modules)
# - utils.date_helpers (8 modules)
# - utils.validation (15 modules)
# - utils.formatting (12 modules)
```

**Benefit:** Reduced coupling, better modularity

**Time:** 30 minutes analysis + refactoring time

---

### Tracking Technical Debt

**Scenario:** Quarterly review of architectural technical debt.

```bash
# Q1 baseline
/code-graph-index
cp docs/code-graph/code-graph-core.png docs/architecture/q1-baseline.png

# Q2 review (3 months later)
/code-graph-index
cp docs/code-graph/code-graph-core.png docs/architecture/q2-current.png

# Compare images side-by-side
```

**Metrics tracked:**

- Total modules (growth rate)
- Circular dependencies (should decrease)
- Average coupling (should decrease)
- Module cohesion (should increase)

**Report:**

- Q1: 87 modules, 2 circular deps, avg coupling 8.3
- Q2: 94 modules, 0 circular deps, avg coupling 6.1
- **Result:** Architecture improving despite code growth

**Benefit:** Quantitative architecture health tracking

**Time:** 15 minutes quarterly

---

## Advanced Workflows

### Cross-Repository Analysis

**Scenario:** Multiple microservices, visualize dependencies between them.

```bash
# Service A
cd ~/projects/service-a
/code-graph-index
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/graph_service_a.db

# Service B
cd ~/projects/service-b
/code-graph-index
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/graph_service_b.db

# Service C
cd ~/projects/service-c
/code-graph-index
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/graph_service_c.db

# Combine (requires custom script)
python tools/merge_graphs.py \
  ~/.amplihack/graph_service_a.db \
  ~/.amplihack/graph_service_b.db \
  ~/.amplihack/graph_service_c.db \
  --output ~/.amplihack/graph_combined.db

# Visualize combined
export AMPLIHACK_GRAPH_DB="~/.amplihack/graph_combined.db"
/code-graph
```

**Result:** System-wide architecture view across microservices

**Time:** 30 minutes

---

## Common Patterns

### Daily Workflow

```bash
# Morning: Update graph after pulling changes
git pull
/code-graph-update

# During development: Quick checks
/code-graph-core

# Before commit: Verify no issues
/code-graph-update
/code-graph-core

# Before PR: Generate documentation
/code-graph-images
```

### Weekly Workflow

```bash
# Monday: Fresh graph for the week
/code-graph-index

# During week: Incremental updates
/code-graph-update

# Friday: Architecture review
/code-graph-core
```

### On-Demand Workflow

```bash
# When needed: Quick visualization
/code-graph-core

# When investigating: Full detail
/code-graph

# When documenting: High-res export
export AMPLIHACK_GRAPH_RESOLUTION="8192x6144"
/code-graph-images
```

---

## Tips and Tricks

**Tip 1:** Use `/code-graph-core` by default, `/code-graph` only when needed (10x faster)

**Tip 2:** Run `/code-graph-update` before standups for quick architecture checks

**Tip 3:** Include graphs in every PR with `/code-graph-images`

**Tip 4:** Monthly `/code-graph-index` full rebuild to ensure database consistency

**Tip 5:** Export high-res images for presentations with `AMPLIHACK_GRAPH_RESOLUTION`

---

## See Also

- [Quick Start](./quick-start.md) - Get started in 2 minutes
- [Command Reference](./command-reference.md) - Complete command documentation
- [Troubleshooting](./troubleshooting.md) - Problem-solving guide
