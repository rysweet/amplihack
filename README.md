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
