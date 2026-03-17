# Layer 2: Compile-Time Dependency Graph

**Generated:** 2026-03-17
**Codebase:** amplihack (v0.6.73)

## Overview

Amplihack is a Python package (`src/amplihack/`) with 30+ internal modules and ~40 direct external dependencies declared in `pyproject.toml`. The dependency tree is wide rather than deep -- many modules are leaf nodes that import from the standard library and one or two external packages.

## Internal Module Map

The package at `src/amplihack/` contains these top-level modules:

| Module | Purpose | Key Dependencies |
|--------|---------|-----------------|
| `cli.py` | CLI argument parser, main dispatch | launcher, docker, proxy, plugin_cli |
| `session.py` | Session lifecycle, signal handling | memory, hooks |
| `launcher/` | Claude/Copilot/Codex subprocess launcher | session, hooks, plugin_manager |
| `hooks/` | Python hook scripts (SessionStart, Stop, etc.) | filesystem, settings |
| `proxy/` | API proxy layer (FastAPI + Flask) | fastapi, flask, litellm, azure-identity |
| `memory/` | Persistent cross-session memory | kuzu, amplihack-memory-lib |
| `security/` | XPIA defense, hook-based threat detection | hooks |
| `safety/` | Git conflict detection, safe copy | hooks |
| `fleet/` | Multi-agent orchestration (hive mind) | claude-agent-sdk, meta_delegation |
| `recipes/` | Recipe YAML parser and executor | recipe_cli |
| `meta_delegation/` | Platform CLI adapter, subprocess management | utils |
| `plugin_manager/` | Claude Code plugin discovery/install | filesystem |
| `bundle_generator/` | Amplifier bundle packaging | filesystem |
| `goal_agent_generator/` | Goal-seeking agent synthesis | claude-agent-sdk |
| `knowledge_builder/` | Code knowledge graph construction | vendor/blarify |
| `vendor/blarify/` | Vendored code intelligence (AST, SCIP) | langchain, tree-sitter, kuzu |
| `uvx/` | UVX deployment management | packaging |
| `docker/` | Docker container detection and management | docker |
| `utils/` | Shared utilities (prerequisites, UVX detection) | stdlib |

## External Dependencies (Top-Level)

See [inventory.md](inventory.md) for the complete package inventory table.

## Key Dependency Chains

1. **CLI -> Launcher -> Session -> Memory -> Kuzu**: The main execution path
2. **Proxy -> LiteLLM -> AI Providers**: API routing
3. **Knowledge -> Blarify -> Tree-Sitter**: Code intelligence
4. **Fleet -> Claude-Agent-SDK**: Multi-agent orchestration

## Diagrams

- [deps.mmd](deps.mmd) -- Mermaid flowchart
- [deps.dot](deps.dot) -- Graphviz DOT
