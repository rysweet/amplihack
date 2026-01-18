# Analyze Codebase

Comprehensive codebase analysis tool that provides insights into code structure, patterns, and quality metrics.

## Overview

The Analyze Codebase tool performs deep analysis of code repositories to identify patterns, potential issues, and optimization opportunities. It combines static analysis with AI-powered insights to deliver actionable recommendations.

### Problem Statement

Developers need quick, comprehensive insights into codebases to understand structure, identify patterns, and spot potential issues without manually reviewing thousands of lines of code.

### Solution Approach

This tool leverages amplihack's agent system to analyze code from multiple perspectives simultaneously, providing a comprehensive view in minutes rather than hours.

### Key Benefits

- **Multi-perspective Analysis**: Security, performance, patterns, and architecture
- **AI-Powered Insights**: Beyond basic static analysis
- **Actionable Recommendations**: Specific steps for improvement
- **Integration Ready**: Works with amplihack workflow and agents

## Prerequisites

- Python 3.8+
- Access to target codebase
- amplihack framework installed

## Installation

```bash
# No additional installation required - uses amplihack core
```

## Usage

### Basic Usage

```bash
make analyze-codebase TARGET=./src
```

### Advanced Usage

```bash
make analyze-codebase TARGET=./src OPTIONS="--format=json --verbose --output=analysis.json"
```

### Parameters

| Parameter | Description                  | Default | Required |
| --------- | ---------------------------- | ------- | -------- |
| TARGET    | Directory or file to analyze | ./src   | yes      |
| OPTIONS   | Additional analysis options  | ""      | no       |

## Examples

### Example 1: Basic Analysis

```bash
make analyze-codebase TARGET=./src
```

**Expected Output:**

```
🔍 Analyzing codebase: ./src

📊 Summary:
- Files analyzed: 42
- Total lines: 3,847
- Languages: Python (90%), YAML (10%)
- Security issues: 2 low-risk
- Performance opportunities: 5
- Pattern compliance: 85%

📋 Top Recommendations:
1. Add input validation to user_service.py:45
2. Consider caching in data_processor.py:123
3. Extract common patterns in handlers/

📁 Detailed Analysis: ./analysis_report.md
```

### Example 2: JSON Output for Integration

```bash
make analyze-codebase TARGET=./src OPTIONS="--format=json --output=analysis.json"
```

**Expected Output:**

```json
{
  "summary": {
    "files_analyzed": 42,
    "total_lines": 3847,
    "languages": { "python": 0.9, "yaml": 0.1 },
    "security_score": 8.5,
    "performance_score": 7.2,
    "pattern_compliance": 0.85
  },
  "recommendations": [
    {
      "type": "security",
      "priority": "medium",
      "file": "user_service.py",
      "line": 45,
      "description": "Add input validation",
      "suggestion": "Use pydantic models for request validation"
    }
  ],
  "metrics": {
    "complexity": { "average": 4.2, "max": 12, "files_over_10": 3 },
    "coverage": { "estimated": 0.78, "missing_areas": ["error_handlers", "edge_cases"] },
    "dependencies": { "external": 15, "internal": 8, "circular": 0 }
  }
}
```

## Output Format

The tool outputs a comprehensive analysis including:

```
🔍 Analysis Results
├── 📊 Summary Statistics
├── 🛡️ Security Assessment
├── ⚡ Performance Analysis
├── 🏗️ Architecture Review
├── 📋 Recommendations
└── 📁 Detailed Reports
```

## Integration

### With Amplihack Agents

This tool integrates with:

- **Analyzer Agent**: Deep structural analysis
- **Security Agent**: Vulnerability assessment
- **Optimizer Agent**: Performance optimization opportunities
- **Patterns Agent**: Code pattern recognition

### With Workflow

This tool can be used in these workflow steps:

- **Step 3**: Code analysis before design changes
- **Step 8**: Quality validation before review
- **Step 10**: Pre-merge analysis

### With User Preferences

The tool respects these user preferences:

- **verbosity**: Adjusts detail level of output
- **communication_style**: Formats reports accordingly
- **priority_type**: Emphasizes relevant analysis areas

## Configuration

### Environment Variables

| Variable        | Description                      | Default |
| --------------- | -------------------------------- | ------- |
| ANALYZE_DEPTH   | Analysis depth (shallow/deep)    | deep    |
| ANALYZE_TIMEOUT | Maximum analysis time in seconds | 300     |

### Configuration Files

The tool looks for configuration in:

- `.amplihack/analyze.yaml`: Analysis preferences and rules
- `pyproject.toml`: Project-specific analysis settings

## Troubleshooting

### Common Issues

**Issue**: Analysis takes too long
**Solution**: Use `--depth=shallow` option or set smaller TARGET scope

**Issue**: Permission denied errors
**Solution**: Ensure read access to target directory and files

### Error Messages

| Error                 | Cause                   | Solution                             |
| --------------------- | ----------------------- | ------------------------------------ |
| "Target not found"    | Invalid directory path  | Check TARGET parameter               |
| "No analyzable files" | No supported file types | Verify directory contains code files |
| "Agent timeout"       | Analysis too complex    | Reduce scope or increase timeout     |

### Debug Mode

Enable debug output:

```bash
make analyze-codebase TARGET=./src DEBUG=1
```

## Architecture

### Components

- **Analyzer Core**: Main coordination and analysis logic
- **File Scanner**: Discovers and categorizes files
- **Agent Coordinator**: Manages parallel agent execution
- **Report Generator**: Formats and outputs results

### Data Flow

```
Input Directory → File Discovery → Parallel Agent Analysis → Result Aggregation → Report Generation → Output
```

### Dependencies

- amplihack.agents: For specialized analysis agents
- amplihack.core: For configuration and utilities
- pathlib: For file system operations

## Performance

### Typical Performance

- **Small projects** (< 1K LOC): 10-30 seconds
- **Medium projects** (1K-10K LOC): 30-120 seconds
- **Large projects** (10K+ LOC): 2-10 minutes

### Optimization Tips

- Use `--depth=shallow` for quick overview
- Target specific directories rather than entire project
- Run analysis incrementally on changed files

## Security Considerations

- **Input Validation**: All file paths validated for safety
- **File Access**: Restricted to specified target directory
- **Execution Safety**: Read-only analysis, no code execution

## Testing

Run the tool's test suite:

```bash
cd .claude/scenarios/analyze-codebase
python -m pytest tests/
```

## Contributing

See `HOW_TO_CREATE_YOUR_OWN.md` for guidance on:

- Creating similar analysis tools
- Customizing analysis rules
- Contributing new analysis patterns

## Version History

- **v1.0.0**: Initial release with multi-agent analysis
- **v0.9.0**: Beta with security and performance focus
- **v0.1.0**: Prototype in ai_working/

---

_This tool follows amplihack's philosophy of ruthless simplicity and immediate value delivery._
