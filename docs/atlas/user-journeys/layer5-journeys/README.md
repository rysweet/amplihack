# Layer 5: User Journey Scenario Graphs

**Generated:** 2026-03-17
**Codebase:** amplihack (v0.6.73)

## Overview

Five primary user journeys cover the main usage patterns of amplihack:

## Journeys

### 1. Install and Launch (`install-and-launch.mmd`)

The most common first-time user flow: install amplihack, then launch a Claude Code session. Covers the full install pipeline (file copy, settings generation, hook registration, manifest writing) followed by the launch pipeline (mode detection, dependency checking, CLI discovery, plugin staging, subprocess spawning).

### 2. Session Lifecycle (`session-lifecycle.mmd`)

Traces a complete Claude Code session from start to finish, showing how hooks fire at each lifecycle event. Covers memory retrieval on session start, XPIA threat scanning on tool use, workflow classification on user prompts, context preservation on compact, and memory persistence on stop.

### 3. Proxy API Call (`proxy-api-call.mmd`)

The optional proxy mode flow: a client sends a `/v1/messages` request, the proxy routes it through LiteLLM to the appropriate AI provider (with fallback), and streams the response back. Shows middleware logging and response caching.

### 4. Recipe Execution (`recipe-execution.mmd`)

How the dev-orchestrator dispatches tasks through the recipe system. User invokes `/dev`, the orchestrator classifies the task, selects a recipe YAML, and executes steps with conditional logic, delegating to specialized agents (architect, builder, tester).

### 5. Plugin Install (`plugin-install.mmd`)

The plugin management flow: user installs a Claude Code plugin via CLI, the plugin manager discovers and validates it, copies files, and registers it in settings.json.

## Diagrams

- [install-and-launch.mmd](install-and-launch.mmd)
- [session-lifecycle.mmd](session-lifecycle.mmd)
- [proxy-api-call.mmd](proxy-api-call.mmd)
- [recipe-execution.mmd](recipe-execution.mmd)
- [plugin-install.mmd](plugin-install.mmd)
