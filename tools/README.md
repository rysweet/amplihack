# Claude Code Tools

This directory contains tools for enhancing Claude Code's capabilities with hybrid code/AI approaches.

## Tools

### requirement_extractor

Extracts functional requirements from codebases by analyzing implementation and separating WHAT the software does from HOW it does it.

**Features:**
- AI-powered semantic analysis of code
- Resume capability for interrupted extractions
- Gap analysis against existing requirements
- Multiple output formats (Markdown, JSON, YAML)
- Parallel processing for large codebases

**Usage:**
```bash
# Basic extraction
make extract-requirements PATH=/path/to/project

# With gap analysis
make extract-requirements-compare PATH=/path/to/project COMPARE=existing.md

# Resume interrupted extraction
make extract-requirements-resume PATH=/path/to/project

# Direct Python usage
python -m tools.requirement_extractor /path/to/project --output requirements.md
```

## Installation

```bash
# Install dependencies (if any)
make install

# Run tests
make test

# Clean temporary files
make clean
```

## Architecture

Tools in this directory follow the "amplifier" pattern:
- **Code for structure** - File traversal, state management, formatting
- **AI for intelligence** - Understanding semantics, extracting meaning

Each tool is designed to be:
- **Resumable** - Can continue from interruptions
- **Incremental** - Saves progress continuously
- **Resilient** - Handles errors gracefully
- **Scalable** - Works with large inputs

## Testing

```bash
# Run all tests
make test

# Test extraction on sample project
make test-extraction
```

## Development

When adding new tools, follow these principles:

1. **Modular Design** - Clear separation of concerns
2. **Ruthless Simplicity** - No unnecessary complexity
3. **Incremental Saves** - Save after each unit of work
4. **Graceful Degradation** - Work without all dependencies
5. **Clear Contracts** - Well-defined interfaces between modules

## Directory Structure

```
tools/
├── README.md                        # This file
├── requirement_extractor/           # Requirements extraction tool
│   ├── __init__.py
│   ├── __main__.py                 # CLI entry point
│   ├── discovery.py                # File discovery and grouping
│   ├── extractor.py                # AI-powered extraction
│   ├── state_manager.py            # Resume capability
│   ├── gap_analyzer.py             # Gap analysis
│   ├── formatter.py                # Output formatting
│   ├── orchestrator.py             # Pipeline coordination
│   └── models.py                   # Data models
└── tests/
    └── test_requirement_extractor.py  # Comprehensive tests
```

## Contributing

When contributing new tools:

1. Follow the existing module pattern
2. Include comprehensive tests
3. Document in this README
4. Add Makefile targets for easy usage
5. Create .claude/commands documentation