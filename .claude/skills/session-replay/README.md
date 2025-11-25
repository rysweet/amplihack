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

- `/transcripts` - Conversation transcript management
- `context-management` skill - Proactive context optimization
- `codex_transcripts_builder.py` - Knowledge extraction from sessions

## Philosophy

This skill follows amplihack principles:

- **Ruthless Simplicity**: Direct file parsing, no complex dependencies
- **Zero-BS**: All functions work completely, no stubs
- **Brick Philosophy**: Self-contained, regeneratable module

## See Also

- [SKILL.md](./SKILL.md) - Full skill specification
- `.claude-trace/` - Trace file location (project root)
- `/transcripts` - Conversation transcript management command
