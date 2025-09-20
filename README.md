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

## Default Coding Workflow

This project includes a standardized 13-step workflow for all non-trivial code
changes. The workflow ensures consistency, quality, and philosophy compliance
across all development.

### Using the Workflow

The workflow is automatically followed by Claude Code for:

- New features
- Bug fixes
- Refactoring
- Any non-trivial code changes

The workflow steps include:

1. Requirements clarification
2. Issue creation
3. Branch setup
4. TDD design
5. Implementation
6. Simplification
7. Testing
8. Committing
9. PR creation
10. Review
11. Feedback implementation
12. Philosophy check
13. Merge readiness

### Customizing the Workflow

The workflow is defined in `.claude/workflow/DEFAULT_WORKFLOW.md` and can be
customized to fit your team's needs:

1. **Edit the workflow file:**

   ```sh
   # Open the workflow file in your editor
   $EDITOR .claude/workflow/DEFAULT_WORKFLOW.md
   ```

2. **Modify steps as needed:**
   - Add new steps or remove unnecessary ones
   - Change the order of operations
   - Adjust the level of detail in checklists
   - Customize agent usage for each step

3. **Save your changes:**
   - Changes take effect immediately
   - No restart or compilation needed
   - The updated workflow will be used for all future tasks

### Workflow Philosophy

The workflow enforces key development principles:

- **Ruthless Simplicity**: Each step has one clear purpose
- **Test-Driven Development**: Tests before implementation
- **Quality Gates**: Multiple review and validation steps
- **Documentation**: Clear commits and PR descriptions

See `.claude/workflow/DEFAULT_WORKFLOW.md` for the complete workflow with
detailed checklists for each step
