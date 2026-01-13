# Project Context Template

Copy this file to your project's `.amplifier/` directory and customize for your specific project.

---

## Project Overview

```yaml
name: [Your Project Name]
description: [One-line description]
type: [library|application|service|cli|monorepo]
primary_language: [python|typescript|go|rust|etc]
```

### Purpose

[2-3 sentences describing what this project does and why it exists]

### Key Users

- [User type 1]: [What they use this for]
- [User type 2]: [What they use this for]

---

## Architecture

### High-Level Structure

```
project/
├── src/           # [Description]
├── tests/         # [Description]
├── docs/          # [Description]
└── [other dirs]   # [Description]
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| [Name] | `src/[path]` | [What it does] |
| [Name] | `src/[path]` | [What it does] |

### Data Flow

[Brief description of how data flows through the system, or diagram]

---

## Development Standards

### Code Style

```yaml
# Language-specific standards
python:
  formatter: ruff
  linter: ruff
  type_checker: pyright
  min_python: "3.11"

typescript:
  formatter: prettier
  linter: eslint
  
# Test framework
testing: pytest  # or jest, go test, etc
```

### Conventions

- **Naming**: [snake_case, camelCase, etc]
- **Imports**: [Absolute vs relative, grouping]
- **Documentation**: [When required, style]
- **Error Handling**: [Strategy]

### Patterns Used

- [Pattern 1]: [Where and why]
- [Pattern 2]: [Where and why]

### Anti-Patterns to Avoid

- [Anti-pattern 1]: [Why it's problematic here]
- [Anti-pattern 2]: [Why it's problematic here]

---

## Commands Reference

### Development

```bash
# Start development environment
[command]

# Run in development mode
[command]

# Format code
[command]

# Lint code
[command]
```

### Testing

```bash
# Run all tests
[command]

# Run specific test file
[command]

# Run with coverage
[command]
```

### Building

```bash
# Build for development
[command]

# Build for production
[command]

# Clean build artifacts
[command]
```

### Deployment

```bash
# Deploy to staging
[command]

# Deploy to production
[command]
```

---

## Key Files

| File | Purpose | When to Modify |
|------|---------|----------------|
| `[file]` | [Purpose] | [When] |
| `[file]` | [Purpose] | [When] |

---

## Dependencies

### Runtime Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| [name] | [why we use it] | [version constraints, quirks] |

### Development Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| [name] | [why we use it] | [version constraints, quirks] |

### External Services

| Service | Purpose | Local Alternative |
|---------|---------|-------------------|
| [name] | [why we use it] | [how to develop without it] |

---

## Domain Knowledge

### Key Concepts

- **[Term]**: [Definition relevant to this project]
- **[Term]**: [Definition relevant to this project]

### Business Rules

- [Rule 1]: [Explanation]
- [Rule 2]: [Explanation]

### Common Gotchas

- [Gotcha 1]: [What happens and how to avoid]
- [Gotcha 2]: [What happens and how to avoid]

---

## History & Decisions

### Architecture Decisions

| Decision | Date | Rationale |
|----------|------|-----------|
| [Decision] | [Date] | [Why we chose this] |

### Known Technical Debt

| Area | Description | Priority |
|------|-------------|----------|
| [Area] | [What needs fixing] | [High/Medium/Low] |

### Future Plans

- [ ] [Planned feature/improvement]
- [ ] [Planned feature/improvement]

---

## Contacts

| Role | Person | When to Contact |
|------|--------|-----------------|
| [Owner/Lead] | [Name] | [For what questions] |
| [Domain Expert] | [Name] | [For what questions] |

---

## Agent Instructions

### Always

- [Instruction that always applies]
- [Instruction that always applies]

### Never

- [Thing to never do in this project]
- [Thing to never do in this project]

### Preferences

- [Preference specific to this project]
- [Preference specific to this project]

---

## Quick Start for New Contributors

1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Step 4]
5. [Step 5]

### First Tasks

Good first issues for getting familiar with the codebase:
- [Easy task 1]
- [Easy task 2]
