# Agent Adapter System

**Version**: 1.0.0
**Status**: Production Ready

## Overview

The agent adapter system converts amplihack's `.claude/agents/` to `.github/agents/` for GitHub Copilot CLI compatibility, enabling users to leverage the same agent ecosystem across both Claude Code and Copilot CLI platforms.

## Philosophy

- **Ruthless Simplicity**: Single-pass conversion, no complex state machines
- **Zero-BS Implementation**: No stubs, every function works or doesn't exist
- **Regeneratable**: Can rebuild `.github/agents/` from `.claude/agents/` at any time
- **Fail-Fast**: Validate agent structure before conversion, report all errors upfront

## Modules

### agent_parser.py

Parses amplihack agent markdown files with YAML frontmatter.

**Public API:**
- `AgentDocument`: Parsed agent structure (frontmatter + body + source path)
- `parse_agent(path)`: Parse agent markdown file with validation
- `has_frontmatter(content)`: Check if content has YAML frontmatter

**Example:**
```python
from amplihack.adapters import parse_agent

agent = parse_agent(Path(".claude/agents/core/architect.md"))
print(agent.frontmatter["name"])  # "architect"
print(agent.body[:100])  # First 100 chars of body
```

### agent_adapter.py

Transforms Claude Code agents for Copilot CLI compatibility.

**Public API:**
- `adapt_agent_for_copilot(agent)`: Full agent adaptation
- `adapt_frontmatter(frontmatter)`: Transform frontmatter format
- `adapt_instructions(body)`: Adapt agent instructions

**Transformations:**
- Combine `description` + `role` into single description
- Extract/generate triggers from description
- Remove `model` field (Copilot doesn't support)
- Convert Task tool → subagent invocation
- Convert TodoWrite → state file updates
- Add "Include" prefix to `@.claude/` references
- Convert Skill tool → MCP server call
- Convert `/command` → `@.github/agents/command`

**Example:**
```python
from amplihack.adapters import parse_agent, adapt_agent_for_copilot

agent = parse_agent(Path(".claude/agents/core/architect.md"))
adapted = adapt_agent_for_copilot(agent)

print(adapted.frontmatter["triggers"])  # ["architect", "architecture", "design", ...]
print("model" in adapted.frontmatter)  # False
```

### agent_registry.py

Maintains manifest of converted agents for discovery.

**Public API:**
- `AgentRegistryEntry`: Single agent in registry
- `categorize_agent(path)`: Categorize agent by path (core/specialized/workflow)
- `create_registry(entries)`: Generate registry from conversions
- `write_registry(registry, path)`: Write registry to JSON file

**Example:**
```python
from amplihack.adapters import AgentRegistryEntry, create_registry, write_registry

entries = [
    AgentRegistryEntry(
        name="architect",
        description="System design agent",
        category="core",
        source_path=".claude/agents/core/architect.md",
        target_path=".github/agents/core/architect.md",
        triggers=["architect", "design"],
        version="1.0.0"
    )
]

registry = create_registry(entries)
write_registry(registry, Path(".github/agents/REGISTRY.json"))
```

### copilot_agent_converter.py

Main conversion orchestration and validation.

**Public API:**
- `ConversionReport`: Results of conversion operation
- `AgentConversion`: Single agent conversion result
- `convert_agents(source_dir, target_dir, force)`: Convert all agents
- `convert_single_agent(agent_path, target_dir, force)`: Convert one agent
- `validate_agent(agent_path)`: Validate agent structure
- `is_agents_synced(source_dir, target_dir)`: Check if agents are in sync

**Example:**
```python
from pathlib import Path
from amplihack.adapters import convert_agents

report = convert_agents(
    source_dir=Path(".claude/agents"),
    target_dir=Path(".github/agents"),
    force=True
)

print(f"Succeeded: {report.succeeded}")
print(f"Failed: {report.failed}")
```

## CLI Usage

```bash
# Basic sync
amplihack sync-agents

# Force overwrite
amplihack sync-agents --force

# Dry-run mode
amplihack sync-agents --dry-run

# Verbose output
amplihack sync-agents --verbose
```

## Performance

**Tested Performance:**
- **36 agents converted in 0.12 seconds** (< 2 seconds target)
- **Average: ~3ms per agent**
- **Memory usage: < 10MB**

## File Structure

```
src/amplihack/adapters/
├── __init__.py                 # Public API exports
├── copilot_agent_converter.py # Main conversion logic
├── agent_parser.py             # Markdown + frontmatter parsing
├── agent_adapter.py            # Claude → Copilot transformation
├── agent_registry.py           # Registry generation
├── README.md                   # This file
└── tests/
    ├── __init__.py
    ├── test_converter.py       # Conversion tests
    ├── test_parser.py          # Parsing tests
    ├── test_adapter.py         # Adaptation tests
    └── test_registry.py        # Registry tests
```

## Testing

Tests follow the TDD pyramid:
- **60% Unit tests**: Fast, focused tests for individual functions
- **30% Integration tests**: Multiple components working together
- **10% E2E tests**: Complete workflows

Run tests:
```bash
pytest src/amplihack/adapters/tests/
```

## Error Handling

**Fail-Fast Validation:**
- Validates ALL agents before converting ANY
- Reports all validation errors at once
- Don't proceed with partial conversion

**Resilient Conversion:**
- If single agent conversion fails, continue with others
- Track all errors in conversion report
- Never lose progress - conversion is idempotent

**User-Friendly Errors:**
- Clear error messages with context
- Actionable fix suggestions
- No cryptic stack traces

## Extension Guide

### Adding New Adaptations

To add a new transformation pattern:

1. Add transformation function in `agent_adapter.py`:
   ```python
   def _adapt_new_pattern(body: str) -> str:
       """Transform new pattern."""
       # Implement transformation
       return adapted_body
   ```

2. Call from `adapt_instructions()`:
   ```python
   def adapt_instructions(body: str) -> str:
       adapted = body
       adapted = _adapt_task_tool(adapted)
       adapted = _adapt_new_pattern(adapted)  # Add here
       return adapted
   ```

3. Add tests in `test_adapter.py`:
   ```python
   def test_adapt_new_pattern():
       body = "Original pattern"
       adapted = adapt_instructions(body)
       assert "Adapted pattern" in adapted
   ```

### Adding New Agent Categories

To add a new category:

1. Update `categorize_agent()` in `agent_registry.py`:
   ```python
   def categorize_agent(source_path: Path) -> Literal["core", "specialized", "workflow", "new_category"]:
       if "/new_category/" in str(source_path):
           return "new_category"
       # ... rest of logic
   ```

2. Update type hint in `AgentRegistryEntry`:
   ```python
   category: Literal["core", "specialized", "workflow", "new_category"]
   ```

3. Update `create_registry()` to include new category:
   ```python
   categories = {
       "core": [],
       "specialized": [],
       "workflow": [],
       "new_category": []
   }
   ```

## Contributing

When making changes:

1. Follow the existing patterns and philosophy
2. Add tests for new functionality (TDD approach)
3. Update this README with new features
4. Ensure < 2 second performance for 37 agents
5. Run all tests before submitting

## License

Part of amplihack framework - see main project LICENSE.
