# eval-recipes Agent Configurations

Agent configurations for use with Microsoft's eval-recipes benchmarking framework.

## Usage with Upstream eval-recipes

```bash
# Clone eval-recipes from Microsoft
git clone https://github.com/microsoft/eval-recipes.git
cd eval-recipes

# Copy our agent configs
cp -r /path/to/amplihack/.claude/agents/eval-recipes/* data/agents/

# Run benchmarks
uv run eval_recipes/main.py --agent amplihack --task linkedin_drafting
uv run eval_recipes/main.py --agent claude_code --task email_drafting
```

## Available Agents

### amplihack

Benchmarks amplihack framework with full agent orchestration, workflow execution, and multi-agent collaboration.

**Config files:**

- `agent.yaml` - Environment requirements
- `install.dockerfile` - Installation steps
- `command_template.txt` - How to invoke amplihack

### claude_code

Benchmarks vanilla Claude Code for baseline comparison.

**Config files:**

- `agent.yaml` - Environment requirements
- `install.dockerfile` - Installation steps
- `command_template.txt` - How to invoke Claude Code

## Key Design Decision

**We consume eval-recipes from upstream, not copy it.**

- ✅ Agent configs live in our repo (`~/.amplihack/.claude/agents/eval-recipes/`)
- ✅ eval-recipes framework consumed from Microsoft's repo
- ❌ Do NOT copy eval-recipes code into our codebase

This keeps our repo focused on agent configs, not framework implementation.

## Docker Best Practice

All Dockerfiles run as non-root user (`USER claude`) because Claude Code blocks `--dangerously-skip-permissions` when running as root.

## References

- **eval-recipes:** https://github.com/microsoft/eval-recipes
- **Documentation:** See eval-recipes README for framework usage
- **Agent configs:** This directory contains our specific agent setups
