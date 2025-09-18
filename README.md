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

### Quick Start for Developers

**⚠️ REQUIRED: Run setup after cloning!**

```sh
# After cloning, run ONE of these:
make setup           # Easiest - uses Makefile
# OR
python3 setup_dev.py # Direct Python script
# OR
pip install pre-commit && pre-commit install  # Manual setup
```

This installs pre-commit hooks that will:

- Prevent commits with formatting issues
- Auto-fix what can be fixed
- Ensure your code will pass CI checks

**Without this setup, your commits may fail CI!**

**What the hooks do:**

- Auto-fix formatting issues (spaces, line endings)
- Format Python code with ruff
- Run type checking with pyright
- Format Markdown/JSON with prettier
- Detect accidental secrets

**If a commit fails:**

1. The hooks will auto-fix what they can
2. Review the changes: `git diff`
3. Stage the fixes: `git add .`
4. Commit again

**Note:** Without running `pre-commit install`, commits will NOT be checked
locally and may fail CI checks
