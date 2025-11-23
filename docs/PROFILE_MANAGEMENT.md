# Profile Management

Comprehensive guide to amplihack's profile system for optimizing token usage and customizing your development environment.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Basic Usage](#basic-usage)
4. [Creating Custom Profiles](#creating-custom-profiles)
5. [Environment Variable Integration](#environment-variable-integration)
6. [Real-World Examples](#real-world-examples)
7. [Advanced Features](#advanced-features)
   - Profile Inheritance (future)
   - Token Usage Estimates
   - UltraThink Integration
8. [Technical Architecture](#technical-architecture)

---

## Overview

### What Are Profiles?

Profiles are **declarative configurations** that control which commands, context files, agents, and skills are loaded into Claude Code sessions. They enable you to:

- **Reduce token consumption** by 40-60% by loading only what you need
- **Speed up session initialization** by skipping irrelevant components
- **Focus your environment** for specific tasks (coding, research, analysis)
- **Create reproducible workflows** that others can use

### Benefits

| Benefit | Description | Impact |
|---------|-------------|--------|
| **Token Efficiency** | Load only relevant components | 40-60% reduction |
| **Faster Startup** | Skip parsing unnecessary files | 2-3x faster init |
| **Focused Context** | Eliminate noise from irrelevant agents/skills | Better AI responses |
| **Reproducibility** | Share profiles for consistent environments | Team alignment |

### Quick Win

Switch to the `coding` profile and save ~50% tokens immediately:

```bash
/amplihack:profile switch amplihack://profiles/coding
```

This loads only development-focused agents (architect, builder, reviewer, tester) and excludes research-oriented components like knowledge-archaeologist and analyst agents.

---

## Core Concepts

### 1. Profile Definition

A profile is a YAML file that declares which components to include/exclude:

```yaml
version: "1.0"
name: "my-profile"
description: "Custom profile for my workflow"

components:
  commands:
    include: ["ultrathink", "analyze", "fix"]
  agents:
    include: ["architect", "builder", "reviewer"]
  skills:
    include_categories: ["coding", "testing"]
  context:
    include: ["PHILOSOPHY.md", "PATTERNS.md"]
```

### 2. Built-in Profiles

amplihack ships with 3 built-in profiles:

| Profile | Purpose | Token Savings | Use Case |
|---------|---------|---------------|----------|
| **all** | Complete environment (everything) | 0% (baseline) | General use, exploration |
| **coding** | Development-focused | ~50% | Feature development, bug fixes |
| **research** | Investigation-focused | ~45% | Code analysis, learning |

### 3. File Mapping

Profiles map to physical YAML files:

```
amplihack://profiles/coding  → .claude/profiles/coding.yaml
amplihack://profiles/research → .claude/profiles/research.yaml
file:///path/to/custom.yaml   → /path/to/custom.yaml
```

The `amplihack://` scheme resolves to `.claude/profiles/` in your project.

### 4. Profile Activation

Profiles can be activated in 3 ways (priority order):

1. **Environment variable** (highest priority): `AMPLIHACK_PROFILE=amplihack://profiles/coding`
2. **Explicit switch**: `/amplihack:profile switch amplihack://profiles/coding`
3. **Default**: Falls back to `all` profile if none specified

### 5. Token Optimization

Profiles reduce token usage by:

- **Skipping agent definitions** not included in the profile
- **Excluding skill documentation** for unused skills
- **Limiting context files** to only what's needed for the task
- **Filtering commands** to reduce slash command reference bloat

**Example**: The `coding` profile excludes 15+ analyst agents, saving ~12K tokens per session.

---

## Basic Usage

### List Available Profiles

See all built-in profiles:

```bash
/amplihack:profile list
```

**Output:**
```
Available profiles:
  - amplihack://profiles/all (Complete environment)
  - amplihack://profiles/coding (Development-focused)
  - amplihack://profiles/research (Investigation-focused)
```

### Show Current Profile

Check which profile is active:

```bash
/amplihack:profile current
```

**Output:**
```
Current profile: amplihack://profiles/all
Description: Complete amplihack environment - all components loaded
```

### Switch Profiles

Change to a different profile:

```bash
# Switch to coding profile
/amplihack:profile switch amplihack://profiles/coding

# Switch to research profile
/amplihack:profile switch amplihack://profiles/research

# Switch to custom profile
/amplihack:profile switch file:///home/user/.amplihack/my-profile.yaml
```

### Set Profile via Environment Variable

Override the default profile for all sessions:

```bash
# In your ~/.bashrc or ~/.zshrc
export AMPLIHACK_PROFILE=amplihack://profiles/coding

# Or set for a single session
AMPLIHACK_PROFILE=amplihack://profiles/research amplihack launch
```

---

## Creating Custom Profiles

### Step-by-Step Tutorial

#### Step 1: Create Profile Directory

```bash
mkdir -p ~/.amplihack/profiles
```

#### Step 2: Create Profile YAML

Create `~/.amplihack/profiles/minimal.yaml`:

```yaml
version: "1.0"
name: "minimal"
description: "Minimal profile for quick tasks (max token efficiency)"

components:
  commands:
    include:
      - "analyze"
      - "fix"
    exclude:
      - "amplihack:n-version"
      - "amplihack:debate"
      - "amplihack:expert-panel"

  context:
    include:
      - "PHILOSOPHY.md"
      - "PROJECT.md"

  agents:
    include:
      - "builder"
      - "reviewer"
    exclude:
      - "*-analyst"
      - "knowledge-archaeologist"
      - "visualization-architect"

  skills:
    include_categories:
      - "coding"
    exclude_categories:
      - "creative"
      - "research"
      - "analysis"

metadata:
  author: "your-name"
  version: "1.0.0"
  tags: ["minimal", "fast", "tokens"]
  created: "2025-11-23T00:00:00Z"
  updated: "2025-11-23T00:00:00Z"

performance:
  lazy_load_skills: true
  cache_ttl: 3600
```

#### Step 3: Validate Profile

```bash
/amplihack:profile validate file:///home/user/.amplihack/profiles/minimal.yaml
```

#### Step 4: Test Profile

```bash
/amplihack:profile switch file:///home/user/.amplihack/profiles/minimal.yaml
/amplihack:profile current
```

#### Step 5: Compare Token Usage

Check token savings:

```bash
# Before (all profile)
/amplihack:profile switch amplihack://profiles/all
# Note starting token count from Claude Code UI

# After (minimal profile)
/amplihack:profile switch file:///home/user/.amplihack/profiles/minimal.yaml
# Compare token count reduction
```

#### Step 6: Iterate and Refine

Add/remove components based on your workflow:

```yaml
# Add a specific agent you need
agents:
  include:
    - "builder"
    - "reviewer"
    - "security"  # Added for security reviews

# Include only specific commands
commands:
  include:
    - "analyze"
    - "fix"
    - "amplihack:modular-build"  # Added for modular development
```

#### Step 7: Share Profile

Commit profile to your project:

```bash
cp ~/.amplihack/profiles/minimal.yaml .claude/profiles/team-minimal.yaml
git add .claude/profiles/team-minimal.yaml
git commit -m "Add team minimal profile"
```

Now team members can use:

```bash
/amplihack:profile switch amplihack://profiles/team-minimal
```

---

## Environment Variable Integration

### Use Case 1: Default Profile for All Sessions

Set a global default profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
export AMPLIHACK_PROFILE=amplihack://profiles/coding

# All sessions now use coding profile by default
amplihack launch
```

### Use Case 2: Project-Specific Profiles

Use different profiles per project:

```bash
# In project1/.envrc (using direnv)
export AMPLIHACK_PROFILE=amplihack://profiles/coding

# In project2/.envrc
export AMPLIHACK_PROFILE=file://$(pwd)/.claude/profiles/custom.yaml
```

### Use Case 3: Task-Specific Override

Override profile for a single task:

```bash
# Use research profile just for this analysis
AMPLIHACK_PROFILE=amplihack://profiles/research amplihack launch -- -p "analyze this codebase"
```

### Use Case 4: CI/CD Integration

Set profile in CI environment:

```yaml
# .github/workflows/analyze.yml
env:
  AMPLIHACK_PROFILE: amplihack://profiles/coding

steps:
  - name: Run amplihack analysis
    run: amplihack launch -- -p "/analyze src/"
```

---

## Real-World Examples

### Example 1: Coding Profile (Built-in)

**Purpose**: Feature development, bug fixes, code implementation

**File**: `.claude/profiles/coding.yaml`

```yaml
version: "1.0"
name: "coding"
description: "Development-focused profile for coding tasks"

components:
  commands:
    include:
      - "ultrathink"
      - "analyze"
      - "fix"
      - "amplihack:modular-build"
      - "ddd:*"  # All DDD commands

  context:
    include:
      - "PHILOSOPHY.md"
      - "PATTERNS.md"
      - "TRUST.md"
      - "PROJECT.md"

  agents:
    include:
      - "architect"
      - "builder"
      - "reviewer"
      - "tester"
      - "api-designer"
      - "database"
      - "security"
      - "cleanup"
      - "optimizer"
    exclude:
      - "knowledge-archaeologist"
      - "*-analyst"  # Exclude all analyst agents

  skills:
    include_categories:
      - "coding"
      - "testing"
      - "development"
    exclude_categories:
      - "creative"
      - "research"
    include:
      - "outside-in-testing"
      - "design-patterns-expert"

metadata:
  author: "amplihack"
  version: "1.0.0"
  tags: ["development", "coding", "focused"]

performance:
  lazy_load_skills: true
  cache_ttl: 3600
```

**Token Savings**: ~50% (excludes 15+ analyst agents, creative skills)

**When to Use**:
- Implementing new features
- Fixing bugs
- Refactoring code
- Running tests

### Example 2: Research Profile (Built-in)

**Purpose**: Codebase analysis, investigation, learning

**File**: `.claude/profiles/research.yaml`

```yaml
version: "1.0"
name: "research"
description: "Investigation and analysis profile"

components:
  commands:
    include:
      - "amplihack:ultrathink"
      - "amplihack:knowledge-builder"
      - "amplihack:expert-panel"

  context:
    include:
      - "PHILOSOPHY.md"
      - "PROJECT.md"

  agents:
    include:
      - "architect"
      - "analyzer"
      - "knowledge-archaeologist"
      - "patterns"
      - "*-analyst"  # Include ALL analyst agents

  skills:
    include_categories:
      - "research"
      - "analysis"

metadata:
  author: "amplihack"
  version: "1.0.0"
  tags: ["research", "investigation", "analysis"]

performance:
  lazy_load_skills: true
  cache_ttl: 3600
```

**Token Savings**: ~45% (excludes builder, tester, coding-focused agents)

**When to Use**:
- Understanding unfamiliar codebases
- Investigating bugs
- Research and learning
- Architecture reviews

### Example 3: Minimal Profile (Custom)

**Purpose**: Quick fixes, minimal token usage, fast responses

**File**: `~/.amplihack/profiles/minimal.yaml`

```yaml
version: "1.0"
name: "minimal"
description: "Ultra-minimal profile for maximum token efficiency"

components:
  commands:
    include:
      - "fix"
      - "analyze"
    exclude:
      - "amplihack:n-version"
      - "amplihack:debate"
      - "amplihack:expert-panel"
      - "amplihack:knowledge-builder"
      - "ddd:*"

  context:
    include:
      - "PHILOSOPHY.md"

  agents:
    include:
      - "builder"
      - "reviewer"
    exclude:
      - "*"  # Exclude all except explicitly included

  skills:
    include: []  # No skills loaded
    exclude_categories:
      - "*"  # Exclude all categories

metadata:
  author: "custom"
  version: "1.0.0"
  tags: ["minimal", "fast", "tokens"]

performance:
  lazy_load_skills: false  # Don't even prepare skill loading
  cache_ttl: 600  # Short cache for minimal footprint
```

**Token Savings**: ~70% (most aggressive reduction)

**When to Use**:
- Quick bug fixes
- Small code changes
- Low-complexity tasks
- Token-constrained environments

**Trade-offs**:
- No specialized agents
- No skills available
- Limited command set
- Best for simple, well-defined tasks

---

## Advanced Features

### 1. Profile Inheritance

Profiles can extend other profiles (future feature):

```yaml
version: "1.0"
name: "my-coding-plus"
extends: "amplihack://profiles/coding"

components:
  agents:
    include:
      - "visualization-architect"  # Add to base coding profile
```

### 2. Token Usage Estimates

View automatic token usage estimates when showing profile details:

```bash
/amplihack:profile show
# or
/amplihack:profile current
```

**Output:**
```
Profile: amplihack://profiles/coding
Description: Development-focused profile for coding tasks
Version: 1.0

Components:
  Commands: ultrathink, analyze, fix ... (5 total)
  Context: PHILOSOPHY.md, PATTERNS.md, TRUST.md, PROJECT.md
  Agents: architect, builder, reviewer ... (9 total)
  Skills (categories): coding, testing, development

Estimated token usage: ~45,234 tokens
Components: 5 commands, 4 context, 9 agents, 2 skills
```

Token estimates are calculated automatically based on:
- Number of agents included/excluded
- Skills loaded by category
- Context files selected
- Command definitions available

### 3. UltraThink Integration

Profiles automatically optimize UltraThink agent orchestration:

```yaml
# coding profile
agents:
  include:
    - "architect"
    - "builder"
    - "reviewer"

# UltraThink will ONLY orchestrate these 3 agents
# Skips loading/coordinating knowledge-archaeologist, analyst agents, etc.
```

This reduces orchestration complexity and improves response quality by eliminating irrelevant agent context.

---

## Technical Architecture

### 1. File Locations

```
.claude/profiles/          # Built-in profiles
├── all.yaml               # Complete environment
├── coding.yaml            # Development profile
└── research.yaml          # Investigation profile

~/.amplihack/profiles/     # User custom profiles
└── *.yaml                 # Your custom profiles

/path/to/project/.claude/profiles/  # Project-specific profiles
└── *.yaml                          # Team-shared profiles
```

### 2. YAML Schema

Complete profile schema:

```yaml
version: "1.0"              # Required: schema version
name: "profile-name"        # Required: unique identifier
description: "..."          # Required: human-readable description

components:                 # Required: what to load
  commands:
    include: [...]          # List of command names
    exclude: [...]          # List to exclude
    include_all: bool       # Load everything (overrides include/exclude)

  context:
    include: [...]          # List of .md filenames
    exclude: [...]
    include_all: bool

  agents:
    include: [...]          # List of agent names
    exclude: [...]          # Supports wildcards: "*-analyst"
    include_all: bool

  skills:
    include: [...]          # List of skill names
    exclude: [...]
    include_categories: [...] # Categories like "coding", "research"
    exclude_categories: [...]
    include_all: bool

metadata:                   # Optional: documentation
  author: "name"
  version: "1.0.0"
  tags: ["tag1", "tag2"]
  created: "ISO8601"
  updated: "ISO8601"

performance:                # Optional: optimization hints
  lazy_load_skills: bool    # Load skills on-demand (default: true)
  cache_ttl: int            # Seconds to cache profile (default: 3600)
```

### 3. Profile Loader

**Implementation**: `.claude/tools/amplihack/profile_management/loader.py`

**Responsibilities**:
- Parse YAML profiles
- Resolve `amplihack://` URIs to file paths
- Validate profile schema
- Merge include/exclude rules
- Return filtered component lists

**Key Methods**:
```python
class ProfileLoader:
    def load(uri: str) -> Profile
    def validate(profile: Profile) -> List[ValidationError]
    def resolve_uri(uri: str) -> Path
    def filter_components(profile: Profile, all_components: Dict) -> Dict
```

### 4. Hook Integration

**Implementation**: `.claude/tools/amplihack/hooks/claude_power_steering.py`

The power steering hook intercepts session initialization and applies profile filtering:

```python
def initialize_session():
    profile_uri = os.getenv("AMPLIHACK_PROFILE", "amplihack://profiles/all")
    profile = ProfileLoader.load(profile_uri)

    # Filter components before loading into context
    filtered_agents = profile.filter_agents(all_agents)
    filtered_skills = profile.filter_skills(all_skills)
    filtered_commands = profile.filter_commands(all_commands)

    return SessionContext(agents=filtered_agents, skills=filtered_skills, ...)
```

### 5. Command Handler

**Implementation**: `.claude/commands/amplihack/profile.md`

Slash commands delegate to ProfileCLI:

```python
# /amplihack:profile list
from profile_management.cli import ProfileCLI
cli = ProfileCLI()
cli.list_profiles()

# /amplihack:profile switch amplihack://profiles/coding
cli.switch_profile("amplihack://profiles/coding")
```

### 6. Workflow Integration

Profiles integrate with `DEFAULT_WORKFLOW.md`:

- **Step 1 (Clarify)**: Profile affects which clarification agents are available
- **Step 4 (Design)**: Profile determines which architecture agents to use
- **Step 13 (Cleanup)**: Profile controls which review agents run final checks

UltraThink automatically adapts agent orchestration based on active profile.

---

## Related Documentation

- [Profile Command Reference](.claude/commands/amplihack/profile.md) - Slash command usage
- [Built-in Profiles](.claude/profiles/) - Source YAML files
- [UltraThink Integration](.claude/commands/amplihack/ultrathink.md) - Agent orchestration
- [Hook Configuration](HOOK_CONFIGURATION_GUIDE.md) - Power steering setup
- [Token Optimization](../CLAUDE.md#profile-management) - Main documentation reference

---

## Quick Reference

| Task | Command |
|------|---------|
| List profiles | `/amplihack:profile list` |
| Show current | `/amplihack:profile current` |
| Switch profile | `/amplihack:profile switch <uri>` |
| Validate profile | `/amplihack:profile validate <uri>` |
| Set default | `export AMPLIHACK_PROFILE=<uri>` |

| Profile | Token Savings | Use Case |
|---------|---------------|----------|
| all | 0% (baseline) | General use |
| coding | ~50% | Development |
| research | ~45% | Investigation |
| minimal (custom) | ~70% | Quick fixes |

**URIs**:
- Built-in: `amplihack://profiles/<name>`
- Custom: `file:///path/to/profile.yaml`
- Project: `amplihack://profiles/<name>` (if in `.claude/profiles/`)
