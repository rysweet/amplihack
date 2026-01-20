# Agent Bundle Generator - User Guide

## Overview

The Agent Bundle Generator is a powerful feature that transforms natural language descriptions into specialized, zero-install agent bundles. Simply describe what you want an agent to do, and the system generates a complete, executable agent bundle that can be run instantly via `uvx`.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Installation](#installation)
- [Command Reference](#command-reference)
- [Complete Examples](#complete-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Quick Start

### Zero-Install Usage

No installation needed! Run directly from GitHub:

```bash
# Generate an agent bundle
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack bundle generate \
  "Create an agent that monitors my system resources and alerts me when CPU or memory usage is high" \
  --output-dir ~/src/system-monitor

# Run your new agent
uvx --from ~/src/system-monitor system-monitor
```

### Installed Usage

If you've cloned the repository:

```bash
# Generate bundle
amplihack bundle generate "your agent description" --output-dir ~/my-agent

# Run the bundle
cd ~/my-agent && uvx . agent-command
```

---

## Basic Usage

### Step 1: Generate a Bundle

The most basic command takes a natural language prompt and output directory:

```bash
amplihack bundle generate "your agent description" --output-dir ~/my-agent
```

**Example:**

```bash
amplihack bundle generate \
  "Create an agent that formats Python code and runs linting checks" \
  --output-dir ~/python-formatter
```

### Step 2: Test the Bundle (Optional)

Add `--test` flag to validate the generated bundle:

```bash
amplihack bundle generate \
  "Create an agent for database backup automation" \
  --output-dir ~/db-backup \
  --test
```

### Step 3: Run Your Agent

Execute the generated bundle:

```bash
uvx --from ~/python-formatter python-formatter format ./my_code.py
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- `uvx` package manager ([installation guide](https://github.com/astral-sh/uv))
- GitHub account (for distribution features)
- Git (for repository operations)

### Optional Dependencies

- Docker (for containerized execution)
- GitHub CLI (`gh`) for repository management

---

## Command Reference

### `bundle generate`

Generate an agent bundle from a natural language prompt.

**Syntax:**

```bash
amplihack bundle generate <PROMPT> [OPTIONS]
```

**Arguments:**

- `PROMPT` - Natural language description of desired agent behavior

**Options:**

- `--output-dir`, `-o` - Output directory for generated bundle (required)
- `--validate` - Validate bundle structure after generation
- `--test` - Run tests on generated agents before finalizing
- `--complexity` - Complexity level: `simple`, `standard`, `advanced` (default: `standard`)
- `--no-tests` - Skip test generation
- `--no-docs` - Skip documentation generation

**Examples:**

```bash
# Basic generation
amplihack bundle generate "security scanner" --output-dir ~/scanner

# With validation and testing
amplihack bundle generate "code reviewer" --output-dir ~/reviewer --validate --test

# Advanced complexity
amplihack bundle generate "multi-cloud deployment orchestrator" \
  --output-dir ~/deployer \
  --complexity advanced
```

### `bundle package`

Package a generated bundle for distribution.

**Syntax:**

```bash
amplihack bundle package <BUNDLE_PATH> [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to generated bundle directory

**Options:**

- `--format`, `-f` - Package format: `uvx`, `tar.gz`, `zip` (default: `uvx`)
- `--output`, `-o` - Output directory for package

**Examples:**

```bash
# Package as uvx
amplihack bundle package ~/my-agent --format uvx --output ./packages

# Package as tar.gz
amplihack bundle package ~/my-agent --format tar.gz --output ./dist
```

### `bundle distribute`

Distribute a packaged bundle to GitHub.

**Syntax:**

```bash
amplihack bundle distribute <PACKAGE_PATH> [OPTIONS]
```

**Arguments:**

- `PACKAGE_PATH` - Path to packaged bundle file

**Options:**

- `--github` - Distribute to GitHub (default)
- `--release` - Create a GitHub release
- `--public` - Make repository public (default: private)
- `--pypi` - Distribute to PyPI (coming soon)

**Examples:**

```bash
# Distribute to GitHub
amplihack bundle distribute ./packages/my-agent.uvx --github

# Create public release
amplihack bundle distribute ./packages/my-agent.uvx --github --release --public
```

### `bundle pipeline`

Run the complete generation, packaging, and distribution pipeline.

**Syntax:**

```bash
amplihack bundle pipeline <PROMPT> [OPTIONS]
```

**Arguments:**

- `PROMPT` - Natural language description of desired agent behavior

**Options:**

- `--output-dir`, `-o` - Output directory (default: `./output`)
- `--format`, `-f` - Package format: `uvx`, `zip` (default: `uvx`)
- `--distribute`, `-d` - Distribute after packaging
- `--skip-tests` - Skip testing stage
- `--skip-distribute` - Skip distribution stage

**Examples:**

```bash
# Complete pipeline
amplihack bundle pipeline "code quality checker" \
  --output-dir ~/quality-checker \
  --distribute

# Pipeline without distribution
amplihack bundle pipeline "log analyzer" \
  --output-dir ~/analyzer \
  --skip-distribute
```

---

## Complete Examples

### Example 1: WSL Development Environment Maintenance

Create an agent that keeps your WSL development tools up to date:

```bash
# Generate the bundle
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack bundle generate \
  "Build an agent that can run on a WSL windows system and always ensure that I have the latest dev tools including python, rust, golang, uv, node, pnpm, VS Code Insiders, claude code, claude trace etc. The agent should persist in running the install commands and processing the results until all the dev tools are up to date." \
  --output-dir ~/src/wsl-dev-updater

# Run the agent
uvx --from ~/src/wsl-dev-updater wsl-dev-updater update
```

**What This Does:**

- Checks installed versions of all specified tools
- Compares with latest available versions
- Updates outdated tools automatically
- Retries failed installations
- Provides detailed progress reports

### Example 2: GitHub Issue Triage Agent

Create an agent that automatically triages GitHub issues:

```bash
# Generate and distribute in one command
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack bundle pipeline \
  "create an agent that can triage all the issues in my gh repo by analyzing content, applying labels, assigning priorities, and identifying duplicates" \
  --output-dir ~/issue-triager \
  --distribute

# Use the agent
uvx --from github.com/user/issue-triager triage --repo owner/repo-name
```

**Features:**

- Analyzes issue content and title
- Applies appropriate labels automatically
- Assigns priority levels
- Detects duplicate issues
- Suggests assignees based on expertise
- Generates triage reports

### Example 3: Security Audit Agent

Create a comprehensive security scanning agent:

```bash
# Generate with advanced complexity
amplihack bundle generate \
  "create an agent that reviews PRs for security vulnerabilities, checks dependencies for CVEs, validates configurations, and generates detailed security reports" \
  --output-dir ~/security-auditor \
  --complexity advanced \
  --validate \
  --test

# Package for sharing
amplihack bundle package ~/security-auditor --format uvx --output ./packages

# Distribute to team
amplihack bundle distribute ./packages/security-auditor.uvx --github --release --public
```

**Capabilities:**

- Scans code for vulnerability patterns
- Checks dependencies against CVE databases
- Validates security configurations
- Analyzes authentication and authorization
- Generates detailed security reports
- Suggests remediation steps

### Example 4: Documentation Generator

Automated documentation generation from code:

```bash
# Complete pipeline
amplihack bundle pipeline \
  "create an agent that automatically generates and updates API documentation from code comments, including examples, parameter descriptions, and response formats" \
  --output-dir ~/doc-generator \
  --distribute

# Run the documentation generator
uvx --from github.com/user/doc-generator generate --input ./src --output ./docs
```

**Features:**

- Extracts docstrings and comments
- Generates markdown documentation
- Creates API reference pages
- Includes usage examples
- Maintains documentation structure
- Updates on code changes

### Example 5: Code Quality Checker

Daily code quality monitoring:

```bash
# Generate quality checker
amplihack bundle generate \
  "Create an agent for daily code quality checks including linting, security scanning, test coverage analysis, and code complexity metrics" \
  --output-dir ~/quality-checker \
  --test \
  --validate

# Run quality checks
uvx --from ~/quality-checker check --directory ./project
```

**Checks:**

- Linting (PEP8, ESLint, etc.)
- Security vulnerabilities
- Test coverage percentage
- Code complexity metrics
- Duplicate code detection
- Best practice compliance

---

## Best Practices

### Writing Effective Prompts

**Be Specific:**

```bash
# Good ✅
"Create an agent that monitors PostgreSQL database performance by tracking query execution times, connection pool usage, and slow queries, then generates daily reports"

# Too Vague ❌
"Create a database agent"
```

**Include Tools and Technologies:**

```bash
# Good ✅
"Create an agent using pytest and coverage.py to run tests and ensure 80% code coverage"

# Missing Details ❌
"Create a testing agent"
```

**Specify Behavior:**

```bash
# Good ✅
"Create an agent that scans every hour, alerts on failures, retries 3 times, and logs all attempts"

# Incomplete ❌
"Create a monitoring agent"
```

### Complexity Levels

Choose the right complexity for your use case:

**Simple:** Single-purpose, straightforward agents

```bash
--complexity simple
# Example: File formatter, simple validator
```

**Standard:** Multi-step workflows, moderate logic (default)

```bash
--complexity standard
# Example: Code reviewer, issue triager
```

**Advanced:** Complex orchestration, multiple integrations

```bash
--complexity advanced
# Example: CI/CD orchestrator, multi-cloud deployer
```

### Testing Strategy

Always test complex agents:

```bash
# Generate with testing
amplihack bundle generate "complex agent" \
  --output-dir ~/agent \
  --test \
  --validate

# Run additional tests after generation
cd ~/agent && pytest tests/
```

### Version Control

Track your generated bundles:

```bash
# Initialize git in bundle
cd ~/my-agent
git init
git add .
git commit -m "Initial agent bundle generation"

# Push to GitHub
gh repo create my-agent --private
git push -u origin main
```

---

## Troubleshooting

### Common Issues

**Issue: Bundle generation fails with parsing error**

_Solution:_ Refine your prompt to be more specific. Break complex requirements into simpler descriptions.

```bash
# Instead of one complex prompt, use clearer language
amplihack bundle generate \
  "Create an agent with three capabilities: 1) scan files for errors, 2) fix common issues automatically, 3) generate reports" \
  --output-dir ~/agent
```

**Issue: Generated agent missing expected features**

_Solution:_ Increase complexity level or be more explicit in prompt:

```bash
amplihack bundle generate \
  "Create an agent that MUST include error retry logic, logging to files, and email notifications on failures" \
  --output-dir ~/agent \
  --complexity advanced
```

**Issue: Package distribution fails**

_Solution:_ Ensure GitHub credentials are configured:

```bash
# Configure GitHub CLI
gh auth login

# Try distribution again
amplihack bundle distribute ./package.uvx --github
```

**Issue: uvx execution fails**

_Solution:_ Check Python version and uvx installation:

```bash
# Verify Python
python --version  # Should be 3.9+

# Reinstall uvx if needed
pip install --upgrade uv
```

### Debug Mode

Enable detailed logging:

```bash
export AMPLIHACK_DEBUG=1
amplihack bundle generate "agent description" --output-dir ~/agent
```

### Validation

Manually validate bundle structure:

```bash
cd ~/my-agent
# Check required files
ls -la  # Should see: .claude/, src/, tests/, pyproject.toml, manifest.json

# Validate manifest
cat manifest.json | jq .

# Check agent definitions
cat .claude/agents/*.md
```

---

## Advanced Topics

### Custom Templates

Create your own agent templates:

```bash
# Create template directory
mkdir -p ~/.amplihack/templates/my-template

# Add template files
cat > ~/.amplihack/templates/my-template/agent.md <<EOF
# Custom Agent Template
Role: {{role}}
Tools: {{tools}}
Behavior: {{behavior}}
EOF

# Use custom template
amplihack bundle generate "custom agent" \
  --output-dir ~/agent \
  --template my-template
```

### Bundle Customization

Modify generated bundles:

```bash
# Generate base bundle
amplihack bundle generate "base agent" --output-dir ~/agent

# Customize agents
vim ~/agent/.claude/agents/main-agent.md

# Regenerate with modifications preserved
amplihack bundle package ~/agent --output ./packages
```

### Integration with CI/CD

Automate bundle generation in GitHub Actions:

```yaml
# .github/workflows/generate-agent.yml
name: Generate Agent Bundle

on:
  workflow_dispatch:
    inputs:
      prompt:
        description: "Agent description"
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Generate Bundle
        run: |
          uvx amplihack bundle pipeline \
            "${{ github.event.inputs.prompt }}" \
            --output-dir ./generated-agent \
            --distribute
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Bundle Updates

Keep generated bundles up to date:

```bash
# Check for updates
amplihack bundle update ~/my-agent --check-only

# Apply updates
amplihack bundle update ~/my-agent --preserve-edits
```

### Multi-Agent Bundles

Create bundles with multiple coordinated agents:

```bash
amplihack bundle generate \
  "Create a bundle with three agents: 1) Scanner agent that finds issues, 2) Analyzer agent that categorizes them, 3) Reporter agent that generates summaries. All agents should work together in a pipeline." \
  --output-dir ~/multi-agent-system \
  --complexity advanced
```

---

## Additional Resources

- [Requirements Document](./agent-bundle-generator-requirements.md) - Detailed feature requirements
- [Design Document](./agent-bundle-generator-design.md) - Technical architecture and design decisions
- [Amplihack Philosophy](claude/context/PHILOSOPHY.md) - Core principles and design philosophy
- [Examples](./examples/) - Sample code and usage patterns

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Report a bug or request a feature](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- **Documentation**: Check the [main README](../README.md) for general usage
- **Examples**: Browse the [examples directory](./examples/) for more code samples

---

_Last Updated: 2025-09-30_
_Version: 1.0_
