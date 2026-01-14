# User Preferences Template

Customize this file to configure default agent behavior for your development environment.

---

## Instructions

1. Copy this file to your project's `.amplifier/` directory or `~/.amplifier/`
2. Customize sections below based on your preferences
3. Agents will automatically apply these preferences

---

## Default Agent Behavior

```yaml
# Primary workflow when task type is ambiguous
default_workflow: development  # Options: qa, investigation, development

# Agent autonomy level
autonomy: high  # Options: low (ask often), medium (ask for major decisions), high (execute autonomously)

# When to create branches
auto_branch: true  # Create feature branches automatically for development work

# Commit behavior
auto_commit: false  # If true, commit after each successful change
commit_style: conventional  # Options: conventional, simple, descriptive
```

---

## Core Preferences

### Verbosity

```yaml
verbosity: normal  # Options: minimal, normal, detailed, verbose

# Minimal: Just results, no explanation
# Normal: Results with brief context
# Detailed: Full explanation of approach
# Verbose: Step-by-step narration (debugging mode)
```

### Communication Style

```yaml
tone: direct  # Options: direct, conversational, formal

# Direct: Facts and actions, minimal pleasantries
# Conversational: Friendly but focused
# Formal: Professional documentation style
```

### Code Style

```yaml
# Language-specific preferences
python:
  formatter: ruff
  type_hints: always  # Options: always, public_only, never
  docstrings: google  # Options: google, numpy, sphinx, none
  line_length: 88

javascript:
  formatter: prettier
  semicolons: false
  quotes: single

# General preferences
prefer_explicit: true  # Explicit over implicit code
prefer_functional: false  # OOP vs functional style
max_function_length: 50  # Lines before suggesting split
```

---

## Workflow Configuration

### Investigation Workflow

```yaml
investigation:
  # How deep to explore before reporting
  depth: moderate  # Options: shallow, moderate, deep, exhaustive
  
  # What to include in investigation reports
  include:
    - code_structure
    - dependencies
    - patterns_found
    - potential_issues
    - recommendations
```

### Development Workflow

```yaml
development:
  # Pre-implementation checks
  always_check:
    - existing_patterns  # Look for similar code first
    - test_coverage     # Check what tests exist
    - dependencies      # Review related modules
  
  # Post-implementation
  always_do:
    - run_tests        # Run affected tests
    - lint_check       # Run linter
    - type_check       # Run type checker (if applicable)
```

### Code Review

```yaml
review:
  focus_areas:
    - security         # Security vulnerabilities
    - performance      # Performance issues
    - maintainability  # Code clarity and structure
    - testing          # Test coverage and quality
  
  severity_threshold: warning  # Options: info, warning, error
  # Info: All suggestions
  # Warning: Skip style-only suggestions
  # Error: Only blocking issues
```

---

## Auto-Update Settings

### Knowledge Base

```yaml
# Automatically update discoveries.md with learnings
auto_update_discoveries: true

# Categories to track
track_categories:
  - patterns_discovered
  - gotchas_encountered
  - optimizations_found
  - api_quirks
```

### Project Documentation

```yaml
# Auto-update project docs when code changes
auto_update_docs: false

# Which docs to maintain
maintain:
  - README.md         # Keep usage examples current
  - CHANGELOG.md      # Update with changes
  - API.md           # Update API documentation
```

---

## Learned Patterns

This section is auto-populated as agents learn your preferences.

```yaml
# Example entries (auto-generated):
learned:
  - pattern: "User prefers descriptive variable names over short ones"
    confidence: high
    source: "Corrected 'idx' to 'index' 3 times"
  
  - pattern: "User wants tests in same PR as implementation"
    confidence: high
    source: "Requested tests added 5 times"
  
  - pattern: "User prefers flat module structure"
    confidence: medium
    source: "Restructured nested modules 2 times"
```

---

## Environment Hints

Help agents understand your environment:

```yaml
environment:
  # Operating system (auto-detected, but can override)
  os: auto  # Options: auto, macos, linux, windows
  
  # Shell preference
  shell: zsh  # Options: bash, zsh, fish, powershell
  
  # Editor for file references
  editor: vscode  # Affects how file links are formatted
  
  # Package managers
  python_packages: uv  # Options: pip, uv, poetry, conda
  node_packages: pnpm  # Options: npm, yarn, pnpm
  
  # Containerization
  container_runtime: docker  # Options: docker, podman, none
```

---

## Project-Specific Overrides

Add project-specific preferences that override global settings:

```yaml
# Example: Different settings for different repo types
project_overrides:
  # For Python packages
  "*/python-*":
    python:
      docstrings: numpy
      type_hints: always
  
  # For quick scripts
  "*/scripts/*":
    verbosity: minimal
    auto_commit: true
```

---

## Notes

- Preferences in project `.amplifier/` override `~/.amplifier/`
- Not all agents support all preferences
- Invalid preferences are silently ignored (check agent docs for support)
- Use `amplifier config validate` to check your configuration
