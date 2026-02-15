# Memory Integration for Goal Agent Generator

## Overview

The goal agent generator now supports generating agents with built-in memory and learning capabilities using the amplihack-memory-lib.

## Usage

Generate a memory-enabled agent:

```bash
amplihack new --file prompt.md --enable-memory
```

This creates a goal-seeking agent with:

- Experience storage (successes, failures, patterns, insights)
- Semantic search for past experiences
- Pattern recognition across experiences
- Auto-compression and retention policies

## Generated Agent Structure

When `--enable-memory` is enabled, the generated agent includes:

```
agent-name/
├── main.py                    # Memory initialization code injected
├── memory/                    # Memory storage directory
│   └── .gitignore            # Excludes SQLite files from git
├── memory_config.yaml        # Memory configuration
├── requirements.txt          # Includes amplihack-memory-lib
└── README.md                 # Memory documentation section
```

## Memory Functions Available in Generated Agents

Every memory-enabled agent has these helper functions:

```python
# Store experiences
store_success(context, outcome, confidence=0.9)
store_failure(context, outcome, confidence=0.9)
store_pattern(context, outcome, confidence=0.85)
store_insight(context, outcome, confidence=0.8)

# Recall experiences
recall_relevant(query, limit=5)  # Returns list[Experience]

# Cleanup
cleanup_memory()  # Close connections when done
```

## Example

```python
# During execution, store learnings
store_success(
    context="Processed CSV file with 10k rows",
    outcome="Successfully extracted and validated data",
    confidence=0.95
)

# Before similar tasks, recall relevant experiences
past_experiences = recall_relevant("CSV processing")
for exp in past_experiences:
    print(f"Previously: {exp.context} -> {exp.outcome}")
```

## Memory Configuration

Configuration is in `memory_config.yaml`:

```yaml
memory:
  enabled: true
  agent_name: "agent-name"
  storage_path: "./memory"

  max_experiences: 1000
  auto_compress: true
  retention_days: 90

  semantic_search:
    enabled: true
    min_similarity: 0.5

  pattern_recognition:
    enabled: true
    min_frequency: 3
    confidence_threshold: 0.7
```

## Implementation Details

### Components Modified

1. **Memory Template** (`templates/memory_template.py`)
   - `get_memory_initialization_code()` - Generates memory setup code
   - `get_memory_config_yaml()` - Generates memory configuration
   - `get_memory_readme_section()` - Generates memory documentation

2. **Agent Assembler** (`agent_assembler.py`)
   - Added `enable_memory` parameter
   - Adds memory metadata to bundle

3. **Packager** (`packager.py`)
   - Writes `memory_config.yaml` if enabled
   - Creates `memory/` directory with `.gitignore`
   - Includes `amplihack-memory-lib` in requirements.txt
   - Injects memory initialization into `main.py`
   - Adds memory section to README

4. **CLI** (`cli.py` and main `cli.py`)
   - Added `--enable-memory` flag
   - Registered `new` command in main CLI

### Testing

Comprehensive test coverage in `tests/test_memory_integration.py`:

- Memory template generation
- Agent assembler with/without memory
- Packager with/without memory
- End-to-end integration test

All tests pass: 8 new tests covering memory integration.

## Design Philosophy

The memory integration follows amplihack's design philosophy:

- **Ruthless Simplicity**: Optional feature, doesn't add complexity to non-memory agents
- **Modular Design**: Memory is self-contained in templates and can be easily modified
- **Zero-BS Implementation**: All generated code works out of the box, no stubs
- **Regeneratable**: Agents can be regenerated with/without memory from same prompt

## Future Enhancements

Potential improvements:

- Custom memory adapters (beyond SQLite)
- Memory visualization in generated agents
- Memory sharing between agents
- Advanced pattern recognition
- Memory migration tools
