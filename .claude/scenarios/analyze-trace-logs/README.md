# Analyze Trace Logs

Comprehensive trace log analysis tool that extracts user preference patterns from claude-trace JSONL logs.

## Overview

The Analyze Trace Logs tool analyzes claude-trace conversation logs to identify user communication patterns, preferences, and common request types. This data helps calibrate AI agent behavior and improve user experience.

### Problem Statement

Understanding user preferences and communication patterns is critical for:

- Calibrating agent autonomy levels
- Matching user communication styles
- Identifying common workflows and pain points
- Improving PM Architect decision-making

However, manually reviewing thousands of conversation logs is impractical.

### Solution Approach

This tool automatically analyzes claude-trace JSONL logs to extract:

- Request categorization (fix/debug, implement, testing, etc.)
- Task verb frequency (fix, create, analyze, etc.)
- Decision patterns (completeness, autonomy, quality emphasis)
- Common phrases and slash commands
- User workflow preferences

### Key Benefits

- **Automated Pattern Detection**: Identifies user preferences without manual review
- **Actionable Insights**: Provides specific recommendations for agent calibration
- **Comprehensive Analysis**: Analyzes multiple dimensions simultaneously
- **Flexible Sampling**: Configurable sample size for quick or deep analysis

## Prerequisites

- Python 3.8+
- claude-trace JSONL logs in `.claude-trace/` directory
- amplihack framework installed

## Installation

```bash
# No additional installation required - uses Python standard library
```

## Usage

### Basic Usage

```bash
make analyze-trace-logs
```

This analyzes the 15 most recent trace logs in `.claude-trace/` and generates a report at `.claude/runtime/TRACE_LOG_ANALYSIS.md`.

### Specify Custom Log Directory

```bash
make analyze-trace-logs TARGET=/path/to/logs
```

### Advanced Options

```bash
# Analyze more files for deeper insights
make analyze-trace-logs OPTIONS="--sample-size 30"

# Custom output location
make analyze-trace-logs OPTIONS="--output ./my-analysis.md"

# Combine options
make analyze-trace-logs TARGET=./logs OPTIONS="--sample-size 30 --output ./report.md"
```

### Direct Python Usage

```bash
# Use defaults
python .claude/scenarios/analyze-trace-logs/tool.py

# Specify log directory
python .claude/scenarios/analyze-trace-logs/tool.py /path/to/logs

# With options
python .claude/scenarios/analyze-trace-logs/tool.py --sample-size 20 --output report.md
```

### Parameters

| Parameter     | Description                       | Default                               | Required |
| ------------- | --------------------------------- | ------------------------------------- | -------- |
| log_dir       | Directory containing JSONL logs   | .claude-trace                         | no       |
| --sample-size | Number of recent files to analyze | 15                                    | no       |
| --output      | Output report path                | .claude/runtime/TRACE_LOG_ANALYSIS.md | no       |

## Examples

### Example 1: Quick Analysis

```bash
make analyze-trace-logs
```

**Expected Output:**

```
================================================================================
Claude-Trace Log Analysis
================================================================================

Found 47 non-empty JSONL files
Sampling 15 most recent files...

Processing 1/15: 2025-11-22-14-30-45.jsonl...
Processing 2/15: 2025-11-22-13-15-22.jsonl...
...
Processing 15/15: 2025-11-20-09-45-12.jsonl...

Total user messages collected: 342

================================================================================
Generating report...
================================================================================

Analysis complete!
Report saved to: /Users/ryan/src/project/.claude/runtime/TRACE_LOG_ANALYSIS.md
```

### Example 2: Deep Analysis

```bash
make analyze-trace-logs OPTIONS="--sample-size 50"
```

Analyzes 50 recent files for more comprehensive insights.

### Example 3: Custom Output

```bash
make analyze-trace-logs OPTIONS="--output ./weekly-analysis.md"
```

Saves report to custom location for weekly reviews.

## Output Format

The tool generates a comprehensive markdown report with these sections:

### Executive Summary

- Total messages analyzed
- Files processed
- Analysis date

### File Statistics

- Table of processed files with entry counts and sizes

### Request Categories

- Distribution of request types (fix_debug, implement, testing, etc.)
- Percentage breakdown

### Most Common Task Verbs

- Frequency analysis of action verbs (fix, create, analyze, etc.)
- Top 20 verbs with counts

### Top Slash Commands

- Most frequently used slash commands
- Usage counts

### Top Common User Requests

- 20 most common short requests (< 100 chars)
- Frequency counts

### Common Key Phrases

- Recurring phrases (15-150 chars)
- Multi-occurrence phrases

### Decision Patterns

- Completeness preference (do it all vs. minimal)
- Autonomy preference (independent vs. guided)
- Merge instructions
- Quality emphasis
- Polite requests

### Workflow Preferences

- Quantified preference metrics
- Completeness vs. minimal scope
- High vs. low autonomy
- Merge and quality patterns

### Key Insights

- Synthesized observations about user preferences
- Communication style assessment
- Task focus analysis
- Most common verbs

### Recommendations for PM Architect

- Autonomy level calibration
- Communication style matching
- Scope decision alignment
- Workflow type preferences
- Task focus priorities

## Report Example Snippet

```markdown
# Claude-Trace Log Analysis Report

## Executive Summary

- **Total Messages Analyzed**: 342
- **Files Processed**: 15
- **Analysis Date**: 2025-11-22 14:35:22

## Request Categories

Distribution of user request types:

- **implement**: 89 (26.0%)
- **fix_debug**: 67 (19.6%)
- **analyze**: 45 (13.2%)
- **git_operations**: 38 (11.1%)
- **testing**: 34 (9.9%)

## Most Common Task Verbs

Action verbs found in user requests:

1. **create**: 78 times (22.8%)
2. **fix**: 67 times (19.6%)
3. **add**: 56 times (16.4%)
4. **analyze**: 45 times (13.2%)
5. **implement**: 43 times (12.6%)

## Key Insights

- User strongly emphasizes **completeness** - prefers 'do it all' over minimal solutions
- User strongly prefers **autonomous execution** without frequent check-ins
- Primary focus is on **implementing new features** and building
- Most common action verbs: 'create', 'fix', 'add'

## Recommendations for PM Architect

Based on the analysis:

1. **Autonomy Level**: Calibrate agent autonomy based on detected preference
2. **Communication Style**: Match user's concise or detailed style
3. **Scope Decisions**: Align with user's aggressive vs. conservative tendencies
4. **Workflow Type**: Prefer parallel or sequential based on user patterns
5. **Task Focus**: Prioritize fix/debug vs. implementation based on usage
```

## Integration

### With Amplihack Agents

This tool provides data for:

- **PM Architect Agent**: Calibrates decision-making based on user patterns
- **Prompt Writer Agent**: Adapts communication style to user preferences
- **Workflow Agents**: Adjusts autonomy level and update frequency

### With User Preferences

Analysis results can inform updates to `.claude/context/USER_PREFERENCES.md`:

```markdown
### Learned Patterns

Based on trace log analysis (2025-11-22):

- User prefers high autonomy (67% of requests indicate independence)
- Communication style: Balanced (avg message length: 85 chars)
- Primary focus: Feature implementation (60%) over debugging (40%)
- Completeness preference: Strong (78% prefer comprehensive solutions)
```

### With Workflow

Use this tool periodically to:

- **Weekly**: Review preference trends
- **Monthly**: Update USER_PREFERENCES.md based on patterns
- **Quarterly**: Adjust agent calibration settings

## Configuration

### Environment Variables

None required. Tool uses standard Python libraries.

### File Locations

- **Input**: `.claude-trace/*.jsonl` (default)
- **Output**: `.claude/runtime/TRACE_LOG_ANALYSIS.md` (default)

## Troubleshooting

### Common Issues

**Issue**: No JSONL files found
**Solution**: Ensure claude-trace is enabled and generating logs

**Issue**: Parsing errors in logs
**Solution**: Tool automatically skips malformed JSON lines with warnings

**Issue**: Empty analysis results
**Solution**: Increase `--sample-size` or check that logs contain user messages

### Error Messages

| Error                     | Cause                         | Solution                                |
| ------------------------- | ----------------------------- | --------------------------------------- |
| "Log directory not found" | Invalid path                  | Check TARGET parameter                  |
| "Malformed JSON"          | Corrupted log file            | Automatically skipped, no action needed |
| "No user messages"        | Logs only contain system msgs | Check log files are from real sessions  |

### Debug Tips

Enable detailed output:

```bash
python .claude/scenarios/analyze-trace-logs/tool.py --sample-size 5
```

Smaller sample size shows per-file processing details.

## Architecture

### Components

- **TraceLogAnalyzer**: Main analysis coordinator
- **JSONL Parser**: Handles various trace log formats
- **Pattern Extractors**: Categorization, verb extraction, decision patterns
- **Report Generator**: Markdown formatter with insights

### Data Flow

```
JSONL Logs → Parse Entries → Extract User Messages →
Categorize & Analyze → Generate Insights → Markdown Report
```

### Dependencies

- Python standard library only:
  - `json`: JSONL parsing
  - `re`: Pattern matching
  - `collections`: Counter, defaultdict
  - `pathlib`: File operations

## Performance

### Typical Performance

- **15 files** (~50MB total): 5-10 seconds
- **30 files** (~100MB total): 10-20 seconds
- **50 files** (~200MB total): 20-40 seconds

### Optimization Tips

- Use smaller `--sample-size` for quick checks
- Focus on recent files (sorted by modification time)
- Run analysis weekly rather than on every session

## Security Considerations

- **Read-Only**: Tool only reads log files, never modifies
- **Local Processing**: All analysis happens locally, no external calls
- **Privacy**: No log data leaves the local machine

## Testing

Run the tool's test suite:

```bash
cd .claude/scenarios/analyze-trace-logs
python -m pytest tests/
```

Tests cover:

- JSONL parsing with malformed data
- User message extraction
- Pattern categorization
- Report generation

## Contributing

See `HOW_TO_CREATE_YOUR_OWN.md` for guidance on:

- Creating similar log analysis tools
- Customizing pattern detection
- Adding new analysis dimensions

## Use Cases

### Use Case 1: Agent Calibration

Analyze trace logs weekly to adjust agent autonomy:

```bash
make analyze-trace-logs OPTIONS="--sample-size 30"
# Review "Workflow Preferences" section
# Update USER_PREFERENCES.md accordingly
```

### Use Case 2: Communication Style Matching

Identify user's preferred communication style:

```bash
make analyze-trace-logs
# Review "Key Insights" for concise vs. detailed preference
# Adjust verbosity setting in USER_PREFERENCES.md
```

### Use Case 3: Workflow Optimization

Discover common request patterns to create custom agents:

```bash
make analyze-trace-logs OPTIONS="--sample-size 50"
# Review "Most Common Task Verbs" and "Request Categories"
# Create specialized agents for frequent patterns
```

## Version History

- **v1.0.0**: Initial release with pattern detection and report generation
- **v0.9.0**: Prototype in .claude/runtime/

## Future Enhancements

Potential future additions:

- JSON output format for programmatic access
- Time-series analysis for preference changes over time
- Integration with Neo4j for relationship mapping
- Real-time analysis mode for live calibration

---

_This tool follows amplihack's philosophy of ruthless simplicity and immediate value delivery._
