# Scenarios Directory Pattern

The Scenarios Directory Pattern implements a **Progressive Maturity Model** for organizing user-facing tools in amplihack. This pattern provides clear separation between experimental and production-ready tools while maintaining amplihack's ruthless simplicity philosophy.

## Philosophy: Metacognitive Recipes

Scenarios are **metacognitive recipes** - tools that build powerful functionality from minimal user input by leveraging AI understanding and automation. Each scenario encapsulates expert knowledge and best practices into simple, reusable patterns.

## Directory Organization

```
.claude/
├── scenarios/          # Production-ready user-facing tools
│   ├── README.md      # This file
│   ├── tool-name/     # Each tool gets its own directory
│   │   ├── README.md                 # Tool overview and usage
│   │   ├── HOW_TO_CREATE_YOUR_OWN.md # Template for similar tools
│   │   ├── tests/                    # Tool-specific tests
│   │   ├── tool.py                   # Main implementation
│   │   └── examples/                 # Usage examples
│   └── templates/     # Shared templates and utilities
└── ai_working/        # Experimental tools under development
    └── experimental-tool/
        ├── README.md
        ├── prototype.py
        └── notes.md
```

## Graduation Criteria

Tools move from `ai_working/` to `scenarios/` when they meet these criteria:

1. **Proven Value**: 2-3 successful uses by real users
2. **Complete Documentation**: README.md + HOW_TO_CREATE_YOUR_OWN.md
3. **Test Coverage**: Comprehensive test suite
4. **Makefile Integration**: Easy execution via `make tool-name`
5. **Stability**: No breaking changes for 1+ week

## Tool Requirements (scenarios/)

Each production tool must include:

### 1. README.md

- Clear problem statement
- Installation/setup instructions
- Usage examples with actual commands
- Expected outputs and behaviors
- Troubleshooting guide

### 2. HOW_TO_CREATE_YOUR_OWN.md

- Step-by-step creation guide
- Template code with placeholders
- Customization points
- Common patterns and variations

### 3. tests/

- Unit tests (60% of coverage)
- Integration tests (30% of coverage)
- End-to-end tests (10% of coverage)
- Test data and fixtures

### 4. Makefile Target

- Simple execution: `make tool-name`
- Parameter passing
- Error handling

## Creating New Tools

### 1. Start in ai_working/

```bash
mkdir .claude/ai_working/new-tool
cd .claude/ai_working/new-tool
touch README.md prototype.py notes.md
```

### 2. Develop and Test

- Build minimal viable version
- Test with real scenarios
- Gather user feedback
- Iterate based on learning

### 3. Graduate to scenarios/

```bash
mkdir .claude/scenarios/new-tool
# Copy refined version with full documentation
# Add to Makefile
# Create test suite
```

## Tool Naming Conventions

- **Kebab-case**: `multi-word-tool-name`
- **Descriptive**: Name clearly indicates purpose
- **Actionable**: Usually verb-noun format (`analyze-performance`, `generate-docs`)

## Integration with Amplihack

Tools integrate seamlessly with amplihack's existing systems:

- **Agent System**: Tools can invoke specialized agents
- **Workflow Integration**: Tools respect DEFAULT_WORKFLOW.md
- **Philosophy Compliance**: All tools follow ruthless simplicity
- **User Preferences**: Tools adapt to USER_PREFERENCES.md

## Example: Code Analysis Tool

```
.claude/scenarios/analyze-codebase/
├── README.md              # "Comprehensive codebase analysis tool"
├── HOW_TO_CREATE_YOUR_OWN.md # Template for analysis tools
├── tool.py               # Main analyzer implementation
├── tests/
│   ├── test_analyzer.py
│   ├── test_integration.py
│   └── fixtures/
│       └── sample_code/
└── examples/
    ├── basic_analysis.py
    └── advanced_patterns.py
```

Usage: `make analyze-codebase TARGET=./src`

## Makefile Integration

Each tool gets a Makefile target for easy execution:

```makefile
analyze-codebase:
	@python .claude/scenarios/analyze-codebase/tool.py $(TARGET)

generate-docs:
	@python .claude/scenarios/generate-docs/tool.py $(FORMAT) $(OUTPUT)
```

## Security Considerations

All tools implement security validation:

- **Input Sanitization**: Validate tool names and paths
- **Path Traversal Prevention**: Restrict file access to project scope
- **User Content Validation**: Sanitize user-generated inputs
- **Safe Execution**: Sandbox tool execution when needed

## Success Metrics

- **Adoption Rate**: Tools used by multiple users
- **Time to Value**: Quick setup and immediate benefit
- **Maintenance Burden**: Low ongoing maintenance needs
- **User Satisfaction**: Positive feedback and repeat usage

---

_This pattern embodies amplihack's philosophy: powerful tools built from simple, reusable components that respect user intent and deliver immediate value._
