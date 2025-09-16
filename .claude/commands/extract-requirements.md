# extract-requirements

Extract functional requirements from a codebase, separating WHAT the software does from HOW it implements it.

## Usage

```
/extract-requirements <project-path> [options]
```

## Options

- `--output <file>` - Output file path (default: requirements.md)
- `--format <type>` - Output format: markdown, json, yaml (default: markdown)
- `--compare <file>` - Compare against existing requirements for gap analysis
- `--resume` - Resume from previous extraction state
- `--concurrency <n>` - Number of parallel extractions (default: 3)
- `--verbose` - Show detailed progress

## Examples

### Basic extraction
```
/extract-requirements ./my-project
```

### Gap analysis against existing requirements
```
/extract-requirements ./my-project --compare existing-requirements.md
```

### Resume interrupted extraction
```
/extract-requirements ./my-project --resume
```

### JSON output for programmatic use
```
/extract-requirements ./my-project --format json --output requirements.json
```

## Description

This command analyzes a codebase and extracts functional requirements from the implementation. It:

1. **Discovers** all code files and groups them into logical modules
2. **Extracts** requirements using AI to understand code semantics
3. **Categorizes** requirements by type and priority
4. **Analyzes** gaps against existing documentation (if provided)
5. **Formats** output as technology-agnostic requirement documents

### Key Features

- **Resume Capability**: Saves progress after each module for interruption recovery
- **Parallel Processing**: Analyzes multiple modules concurrently
- **Gap Analysis**: Identifies missing, extra, and modified requirements
- **Multiple Formats**: Supports Markdown, JSON, and YAML output
- **Technology Agnostic**: Generates requirements without implementation details

### How It Works

The tool uses a hybrid code/AI approach:
- **Code** handles file traversal, state management, and formatting
- **AI** understands code semantics and extracts functional requirements

Each module is processed independently with results saved immediately, allowing for:
- Resume from interruptions
- Partial results on timeout
- Incremental updates

### Requirements Format

Generated requirements follow standard format:
```markdown
## Category: Feature Name

### REQ-MOD-001: Requirement Title
The system SHALL [action] [object] [condition/context]

### REQ-MOD-002: Another Requirement
The system SHALL [action] [object] [condition/context]
```

### Gap Analysis Output

When comparing against existing requirements:
```markdown
## Gap Analysis Report

### Missing Requirements (in code but not documented)
- Module: auth - User session management
- Module: api - Rate limiting functionality

### Extra Requirements (documented but not in code)
- REQ-AUTH-005: Multi-factor authentication
- REQ-API-012: GraphQL endpoint support

### Modified Requirements
- REQ-DB-003: Changed from SQL to support multiple databases
```

## Implementation

This command runs the requirement extractor tool located at:
`tools/requirement_extractor/`

Internally, it executes:
```bash
python -m tools.requirement_extractor <project-path> [options]
```

Or via Makefile:
```bash
make extract-requirements PATH=<project-path> [OPTIONS="--compare existing.md"]
```

The tool is designed for large codebases with hundreds or thousands of files, using incremental saves and resume capability to handle long-running extractions.

## Error Handling

- **Timeouts**: Individual modules that timeout are skipped, extraction continues
- **AI Unavailable**: Falls back to basic pattern matching if Claude SDK unavailable
- **File Errors**: Cloud-synced files are retried with exponential backoff
- **Partial Success**: Always saves whatever was successfully extracted

## Performance

- Processes ~10 modules per minute with AI extraction
- Handles projects with 10,000+ files
- Memory efficient with streaming processing
- Configurable concurrency for rate limit management