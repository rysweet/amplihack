# GitHub Copilot SDK Skill

Comprehensive knowledge base for using the GitHub Copilot SDK to embed Copilot's agentic workflows in applications across Python, TypeScript, Go, and .NET.

## Overview

The GitHub Copilot SDK exposes the same production-tested agent runtime behind Copilot CLI as a programmable SDK. You define agent behavior; Copilot handles planning, tool invocation, file edits, and more.

## Quick Links

| Resource                                   | Description                              |
| ------------------------------------------ | ---------------------------------------- |
| [SKILL.md](./SKILL.md)                     | Core instructions and quick start        |
| [reference.md](./reference.md)             | Complete API reference (all 4 languages) |
| [examples.md](./examples.md)               | 10+ runnable code examples               |
| [patterns.md](./patterns.md)               | 8+ production patterns                   |
| [drift-detection.md](./drift-detection.md) | Update procedures                        |

## Installation

| Language           | Command                                   |
| ------------------ | ----------------------------------------- |
| Node.js/TypeScript | `npm install @github/copilot-sdk`         |
| Python             | `pip install github-copilot-sdk`          |
| Go                 | `go get github.com/github/copilot-sdk/go` |
| .NET               | `dotnet add package GitHub.Copilot.SDK`   |

## Prerequisites

1. **Copilot CLI** - Install and authenticate ([guide](https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli))
2. **Copilot Subscription** - Required (free tier available)

Verify CLI is working:

```bash
copilot --version
```

## Key Features

- **Multi-language support**: Python, TypeScript, Go, .NET
- **Streaming responses**: Real-time output for better UX
- **Custom tools**: Define functions Copilot can invoke
- **MCP integration**: Connect to Model Context Protocol servers
- **Session management**: Multiple conversations, persistence
- **BYOK support**: Use your own API keys for LLM providers

## Architecture

```
Your Application
       ↓
  SDK Client
       ↓ JSON-RPC
  Copilot CLI (server mode)
```

## Official Resources

- **GitHub Repository**: https://github.com/github/copilot-sdk
- **Getting Started Guide**: https://github.com/github/copilot-sdk/blob/main/docs/getting-started.md
- **Cookbook**: https://github.com/github/copilot-sdk/tree/main/cookbook
- **Awesome Copilot**: https://github.com/github/awesome-copilot

## Status

The GitHub Copilot SDK is currently in **Technical Preview**. While functional for development and testing, it may not yet be suitable for production use.

## Skill Maintenance

This skill tracks the official GitHub Copilot SDK documentation. See [drift-detection.md](./drift-detection.md) for update procedures and validation workflow.

**Last Updated**: 2025-01-25
**Source Version**: GitHub Copilot SDK v1.0 (Technical Preview)
