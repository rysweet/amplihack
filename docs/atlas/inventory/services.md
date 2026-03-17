# Service Inventory

**Generated:** 2026-03-17

Amplihack is a single Python package, not a microservice architecture. The "services" below are internal components that function as logical services.

| Component | Language | Port | Repo Path | Health Check |
|-----------|----------|------|-----------|--------------|
| amplihack CLI | Python | - | src/amplihack/cli.py | `amplihack health` |
| Integrated Proxy | Python (FastAPI) | configurable | src/amplihack/proxy/integrated_proxy.py | GET /health |
| Responses Proxy | Python (Flask) | 5000 | src/amplihack/proxy/responses_api_proxy.py | - |
| Log Streaming | Python (FastAPI) | configurable | src/amplihack/proxy/log_streaming.py | GET /health |
| Docker Container | Python | - | docker/docker-compose.yml | - |
| Rust Hook Engine | Rust | - | .claude/bin/amplihack-hooks | - |

## Non-Runtime Components

| Component | Language | Repo Path | Purpose |
|-----------|----------|-----------|---------|
| amplifier-bundle | YAML/Markdown | amplifier-bundle/ | Microsoft Amplifier recipes, tools, skills |
| .claude agents | Markdown | .claude/agents/ | Specialized AI agent definitions |
| .claude skills | Markdown | .claude/skills/ | Claude Code skill definitions (~120 skills) |
| .claude commands | Markdown | .claude/commands/ | Slash command definitions |
| .claude scenarios | Python/Markdown | .claude/scenarios/ | Production scenario tools |
| .claude tools | Python/Shell | .claude/tools/ | Hook scripts and utilities |
| .claude workflow | Markdown | .claude/workflow/ | DEFAULT_WORKFLOW definition |
| amplifier-module-orchestrator | TypeScript | amplifier-module-orchestrator-amplihack/ | Amplifier module |
| amplihack-logparse | Python | amplihack-logparse/ | Log parsing utility |
| docs | Markdown | docs/ | MkDocs documentation site |
| tests | Python | tests/ | Test suite (100+ test files) |
| scripts | Python/Shell | scripts/ | Development and CI scripts |
| Specs | Markdown | Specs/ | Module specifications |
