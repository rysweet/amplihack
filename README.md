# Microsoft Hackathon 2025 - Agentic Coding Framework

This project accelerates software development through AI-powered agents for
automation, code generation, and collaborative problem-solving.

## Installation & Usage

**Requirements:**

- Python 3.x
- git
- [uvx](https://github.com/astral-sh/uv) (recommended for running CLI tools from
  git repos)

### Quick Install

**Quick run from GitHub (no local clone needed):**

```sh
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack install
```

This runs the `amplihack` CLI directly from the latest code.

### Launching Claude Code with Azure OpenAI Integration

The `amplihack` CLI now includes powerful integration with Claude Code and Azure
OpenAI:

**Basic Claude Code launch:**

```sh
# Launch Claude Code with amplihack from any directory
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch

# Or from a specific branch (e.g., during development)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding@feat/amplihack-proxy-launcher amplihack launch
```

**With Azure OpenAI proxy (automatically includes persistence prompt):**

```sh
# Launch with Azure OpenAI proxy - persistence prompt is automatically included
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack launch --with-proxy-config ./azure.env

# Or from a specific branch
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding@feat/amplihack-proxy-launcher amplihack launch --with-proxy-config ./azure.env
```

The proxy integration allows you to use Azure OpenAI models with Claude Code,
providing enterprise security and compliance while maintaining the Claude Code
interface. When using the proxy, an Azure persistence prompt is automatically
appended to help the model operate autonomously.

### Other Commands

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
