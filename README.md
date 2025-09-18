# Microsoft Hackathon 2025 - Agentic Coding Framework

This project accelerates software development through AI-powered agents for
automation, code generation, and collaborative problem-solving.

## Installation & Usage

**Requirements:**

- Python 3.x
- git
- [uvx](https://github.com/astral-sh/uv) (recommended for running CLI tools from
  git repos)

**Quick run from GitHub (no local clone needed):**

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack install
```

This runs the `amplihack` CLI directly from the latest code.

**Uninstall:**

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack uninstall
```

**Developer mode (editable):**

```sh
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding
uv pip install -e .
uvx amplihack install
```

- The CLI lives in the `src/amplihack/` directory (src layout).
- Use only the `amplihack` CLI as above—no legacy scripts or entrypoints.
- The CLI might be installed under `.venv/bin`

## Development Setup

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and consistency. The
hooks run automatically on every commit to:

- Check for merge conflicts
- Fix trailing whitespace and end-of-file issues
- Format Python code with ruff
- Run type checking with pyright
- Format other files with prettier
- Detect secrets to prevent accidental commits

**Setup pre-commit hooks:**

```sh
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hooks
pre-commit install
pre-commit install --hook-type pre-push  # Optional: also run on push

# Run hooks manually on all files (useful for testing)
pre-commit run --all-files
```

After installation, the hooks will run automatically on `git commit`. If any
issues are found:

1. The hooks will attempt to auto-fix formatting issues
2. If fixes are made, you'll need to stage the changes and commit again
3. For issues that can't be auto-fixed, you'll see error messages to resolve
   manually
