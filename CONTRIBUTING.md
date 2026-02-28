# Contributing to amplihack

Thank you for your interest in contributing to amplihack! This guide will help you get started.

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **git**

### Setting Up Your Development Environment

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/amplihack.git
cd amplihack

# 2. Install dependencies with uv
uv sync

# 3. Install pre-commit hooks
pre-commit install

# 4. Copy the environment template
cp .env.example .env
# Edit .env with your API keys as needed
```

### Running Tests

```bash
# Run the full test suite
pytest

# Run a specific test file
pytest tests/test_example.py

# Run with verbose output
pytest -v
```

### Building Documentation

```bash
make docs-serve    # Start local docs server
make docs-build    # Build the documentation site
```

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/rysweet/amplihack/issues) to avoid duplicates.
2. Open a new issue with:
   - A clear, descriptive title
   - Steps to reproduce
   - Expected vs. actual behavior
   - Your environment (OS, Python version, amplihack version)

### Suggesting Features

Open an issue with the **Feature Request** label. Describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

### Submitting Code

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Make your changes** — keep commits focused and atomic.
3. **Run tests** and ensure they pass:
   ```bash
   pytest
   ```
4. **Run pre-commit checks**:
   ```bash
   pre-commit run --all-files
   ```
5. **Push** your branch and open a Pull Request against `main`.

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/short-description` | `feat/add-memory-export` |
| Bug fix | `fix/short-description` | `fix/agent-timeout` |
| Docs | `docs/short-description` | `docs/update-quickstart` |
| Tests | `test/short-description` | `test/workflow-coverage` |

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add memory graph export command
fix: resolve agent timeout in parallel workflows
docs: clarify prerequisites for WSL setup
test: add coverage for recipe validation
```

## Code Style

- **Python**: Follow existing code conventions. Pre-commit hooks enforce formatting.
- **Markdown**: Follow [markdownlint](https://github.com/DavidAnson/markdownlint) rules (see `.markdownlint.json`).
- Keep functions focused and well-documented.

## Pull Request Guidelines

- Reference any related issues (e.g., `Closes #123`).
- Provide a clear description of what changed and why.
- Keep PRs small and focused — one concern per PR.
- Ensure CI checks pass before requesting review.

## Questions?

If you're unsure about anything, open an issue or start a discussion. We're happy to help!
