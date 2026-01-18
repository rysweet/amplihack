# Session Replay Skill

Analyze claude-trace JSONL files for session health, patterns, and actionable insights.

## Overview

The session-replay skill provides API-level analysis of Claude Code sessions by parsing claude-trace JSONL files. It complements the `/transcripts` command by focusing on performance metrics, token usage, and error patterns rather than conversation content.

## Features

- **Session Health Analysis**: Token usage, request timing, error rates
- **Error Pattern Detection**: Categorize and track recurring failures
- **Tool Usage Analytics**: Identify inefficient patterns and bottlenecks
- **Session Comparison**: Track trends across multiple sessions

## Quick Start

```
User: Analyze my latest session health

Claude: I'll analyze the most recent trace file...
[Reads .claude-trace/*.jsonl]
[Extracts metrics]
[Generates health report]
```

## Actions

| Action    | Description                     |
| --------- | ------------------------------- |
| `health`  | Analyze session health metrics  |
| `errors`  | Identify error patterns         |
| `compare` | Compare metrics across sessions |
| `tools`   | Analyze tool usage patterns     |

## Trace File Format

Claude-trace produces JSONL files with request/response pairs:

```json
{
  "timestamp": 1763926357.797,
  "request": {
    "method": "POST",
    "url": "https://api.anthropic.com/v1/messages",
    "body": { "model": "...", "messages": [...] }
  },
  "response": {
    "usage": { "input_tokens": N, "output_tokens": N },
    "content": [...]
  }
}
```

## Metrics Extracted

- **Token Usage**: Input/output tokens, efficiency ratio
- **Request Stats**: Count, latency, error rate
- **Tool Usage**: Call frequency, success rates
- **Health Score**: Composite session quality metric

## Example Output

```
Session Health Report
=====================
File: log-2025-11-23-19-32-36.jsonl
Duration: 45 minutes

Token Usage:
- Input: 125,432 tokens
- Output: 34,521 tokens
- Efficiency: 27.5% output ratio

Health Score: 82/100 (Good)
```

## Related Tools

| Need                             | Use This                        |
| -------------------------------- | ------------------------------- |
| Session performance metrics      | **session-replay** (this skill) |
| Conversation content/restoration | `/transcripts` command          |
| Knowledge extraction             | `codex_transcripts_builder.py`  |
| Token optimization               | `context-management` skill      |

## Philosophy Alignment

This skill strictly follows amplihack principles:

- **Ruthless Simplicity**: Direct file parsing using only Python standard library (json, pathlib)
- **Zero-BS**: Every code example runs without modification, no stubs or placeholders
- **Brick Philosophy**: Self-contained module with clear inputs (trace files) and outputs (reports)
- **Fail Fast**: Clear error messages for malformed files, missing traces, or permission issues

## Limitations

- **Read-only**: Cannot modify or generate trace files
- **Local only**: Analyzes traces in current project only
- **JSONL format**: Only claude-trace JSONL format supported
- **Post-session**: Analyzes completed sessions, not real-time

## See Also

- [SKILL.md](./SKILL.md) - Full skill specification with implementation details
- `.claude-trace/` - Trace file location (project root)
- `/transcripts` - Conversation transcript management command
- `context-management` skill - Proactive context optimization
