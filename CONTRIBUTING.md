# Contributing to amplihack

Thank you for your interest in contributing to amplihack! This guide will help
you get started.

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **git**
- **[pre-commit](https://pre-commit.com/)** — Git hook framework (`pip install pre-commit` or `uv tool install pre-commit`)

### Setting Up Your Development Environment

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/amplihack.git
cd amplihack

# 2. Install all dependencies (dev + runtime) into a local .venv
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

#### Interpreting Test Results

**What success looks like:**

```
==================== 237 passed in 45.2s ====================
```

All tests passing means your changes don't break existing functionality.

**What failure looks like:**

```
======================== FAILURES ========================
___________________________ TestClass.test_method _______________________
...
FAILED tests/test_example.py::TestClass::test_method
```

A failure means something isn't working as expected. Don't panic — this is
normal during development.

**Common causes of test failures:**

1. **Missing environment variables** — Copy `.env.example` to `.env` and add
   your API keys
2. **Missing dependencies** — Run `uv sync` to install all dependencies
3. **Import errors** — Run `uv sync` first; if still failing, check the error
   message for missing packages

**Debugging tips:**

- Run with `-v` flag for detailed output: `pytest -v`
- Run a single test file to isolate issues: `pytest tests/test_example.py`
- Check the error traceback — it usually points to the exact line failing

**Expected runtime:** Full test suite takes ~2-3 minutes on typical hardware

### Building Documentation

```bash
make docs-serve    # Start local docs server
make docs-build    # Build the documentation site
```

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/rysweet/amplihack/issues) to avoid
   duplicates.
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

| Type    | Pattern                  | Example                  |
| ------- | ------------------------ | ------------------------ |
| Feature | `feat/short-description` | `feat/add-memory-export` |
| Bug fix | `fix/short-description`  | `fix/agent-timeout`      |
| Docs    | `docs/short-description` | `docs/update-quickstart` |
| Tests   | `test/short-description` | `test/workflow-coverage` |

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add memory graph export command
fix: resolve agent timeout in parallel workflows
docs: clarify prerequisites for WSL setup
test: add coverage for recipe validation
```

## Code Style

We use automated tools to maintain consistent code style across the project.

### Python

- **Formatter**: [Ruff](https://docs.astral.sh/ruff/) (runs via pre-commit hooks)
- **Line length**: 100 characters max
- **Python version**: 3.11+

**Quick start:**
```bash
# Format all Python files
ruff format .

# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

**Key conventions:**
- Use 4 spaces for indentation (not tabs)
- Follow PEP 8 naming conventions
- Keep functions focused and well-documented
- Run `pre-commit run --all-files` before committing

**What if pre-commit fails?**
```bash
# Common fix: auto-format your code
ruff format <file.py>
ruff check --fix <file.py>
git add <file.py>
git commit
```

### Markdown

- **Linter**: [markdownlint](https://github.com/DavidAnson/markdownlint)
- **Config**: See `.markdownlint.json` for rules

**Common rules:**
- Maximum line length: 100 characters
- Use `#` for headings (not underlines)
- Use `-` for unordered lists (not `*`)

**Check your markdown:**
```bash
# Install markdownlint CLI
npm install -g markdownlint-cli

# Check all markdown files
markdownlint .
```

### Pre-commit Hooks

Pre-commit hooks automatically check your code before each commit. To set up:

```bash
# Install pre-commit
pip install pre-commit
# or
uv tool install pre-commit

# Install the hooks
pre-commit install
```

**What gets checked:**
- Python formatting (Ruff)
- Markdown formatting (markdownlint)
- Trailing whitespace
- YAML syntax
- And more...

**Skip hooks temporarily** (not recommended):
```bash
git commit --no-verify
```

**Run checks manually:**
```bash
pre-commit run --all-files
```

### Getting Help

If you're unsure about code style:
1. Check existing code for patterns
2. Run `ruff format` — it will handle most style questions
3. Open an issue or PR — reviewers will help guide you

Remember: Pre-commit hooks are your friend! They catch issues before you commit.

## Pull Request Guidelines

- Reference any related issues (e.g., `Closes #123`).
- Provide a clear description of what changed and why.
- Keep PRs small and focused — one concern per PR.
- Ensure CI checks pass before requesting review.

## Questions?

If you're unsure about anything, open an issue or start a discussion. We're
happy to help!
