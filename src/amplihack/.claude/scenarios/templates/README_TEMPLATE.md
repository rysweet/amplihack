# {TOOL_NAME}

{ONE_LINE_DESCRIPTION}

## Overview

{DETAILED_DESCRIPTION}

### Problem Statement

{WHAT_PROBLEM_DOES_THIS_SOLVE}

### Solution Approach

{HOW_DOES_THIS_TOOL_SOLVE_IT}

### Key Benefits

- {BENEFIT_1}
- {BENEFIT_2}
- {BENEFIT_3}

## Prerequisites

- {REQUIREMENT_1}
- {REQUIREMENT_2}
- {REQUIREMENT_3}

## Installation

```bash
# Add any setup steps here
{INSTALLATION_COMMANDS}
```

## Usage

### Basic Usage

```bash
make {tool-name}
```

### Advanced Usage

```bash
make {tool-name} TARGET={target} OPTIONS="{options}"
```

### Parameters

| Parameter | Description           | Default         | Required |
| --------- | --------------------- | --------------- | -------- |
| TARGET    | {target_description}  | {default_value} | {yes/no} |
| OPTIONS   | {options_description} | {default_value} | {yes/no} |

## Examples

### Example 1: {EXAMPLE_TITLE}

```bash
make {tool-name} TARGET=./src
```

**Expected Output:**

```
{SAMPLE_OUTPUT}
```

### Example 2: {ADVANCED_EXAMPLE_TITLE}

```bash
make {tool-name} TARGET=./src OPTIONS="--verbose --format=json"
```

**Expected Output:**

```json
{SAMPLE_JSON_OUTPUT}
```

## Output Format

The tool outputs {OUTPUT_FORMAT_DESCRIPTION}:

```
{SAMPLE_OUTPUT_STRUCTURE}
```

## Integration

### With Amplihack Agents

This tool integrates with:

- **{AGENT_NAME}**: {INTEGRATION_DESCRIPTION}
- **{AGENT_NAME}**: {INTEGRATION_DESCRIPTION}

### With Workflow

This tool can be used in these workflow steps:

- **Step {N}**: {WORKFLOW_INTEGRATION}
- **Step {N}**: {WORKFLOW_INTEGRATION}

### With User Preferences

The tool respects these user preferences:

- **{PREFERENCE_NAME}**: {HOW_IT_ADAPTS}
- **{PREFERENCE_NAME}**: {HOW_IT_ADAPTS}

## Configuration

### Environment Variables

| Variable   | Description   | Default   |
| ---------- | ------------- | --------- |
| {VAR_NAME} | {description} | {default} |

### Configuration Files

The tool looks for configuration in:

- `{CONFIG_FILE_PATH}`: {PURPOSE}
- `{CONFIG_FILE_PATH}`: {PURPOSE}

## Troubleshooting

### Common Issues

**Issue**: {COMMON_PROBLEM}
**Solution**: {SOLUTION_STEPS}

**Issue**: {COMMON_PROBLEM}
**Solution**: {SOLUTION_STEPS}

### Error Messages

| Error           | Cause   | Solution   |
| --------------- | ------- | ---------- |
| {ERROR_MESSAGE} | {CAUSE} | {SOLUTION} |
| {ERROR_MESSAGE} | {CAUSE} | {SOLUTION} |

### Debug Mode

Enable debug output:

```bash
make {tool-name} TARGET={target} DEBUG=1
```

## Architecture

### Components

- **{COMPONENT_NAME}**: {PURPOSE}
- **{COMPONENT_NAME}**: {PURPOSE}

### Data Flow

```
{DATA_FLOW_DESCRIPTION}
```

### Dependencies

- {DEPENDENCY_1}: {PURPOSE}
- {DEPENDENCY_2}: {PURPOSE}

## Performance

### Typical Performance

- **Small projects** ({SIZE_RANGE}): {TIME_ESTIMATE}
- **Medium projects** ({SIZE_RANGE}): {TIME_ESTIMATE}
- **Large projects** ({SIZE_RANGE}): {TIME_ESTIMATE}

### Optimization Tips

- {TIP_1}
- {TIP_2}
- {TIP_3}

## Security Considerations

- **Input Validation**: {VALIDATION_DESCRIPTION}
- **File Access**: {ACCESS_RESTRICTIONS}
- **Execution Safety**: {SAFETY_MEASURES}

## Testing

Run the tool's test suite:

```bash
cd .claude/scenarios/{tool-name}
python -m pytest tests/
```

## Contributing

See `HOW_TO_CREATE_YOUR_OWN.md` for guidance on:

- Creating similar tools
- Customizing this tool
- Contributing improvements

## Version History

- **v1.0.0**: Initial release
- **v0.9.0**: Beta version
- **v0.1.0**: Prototype in ai_working/

---

_This tool follows amplihack's philosophy of ruthless simplicity and immediate value delivery._
