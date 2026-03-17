# External Dependency Inventory

**Generated:** 2026-03-17

| Dependency | Type | Auth | Rate Limit | Fallback |
|-----------|------|------|-----------|----------|
| Anthropic API | AI Provider | API Key | Per plan | Azure OpenAI via LiteLLM |
| Azure OpenAI | AI Provider | Azure Service Principal | Per deployment | Anthropic via LiteLLM |
| LiteLLM | LLM Router | - | - | Direct provider calls |
| GitHub (amplihack-memory-lib) | Git dependency | - | - | Cached wheel |
| GitHub (amplihack-agent-eval) | Git dependency | - | - | Cached wheel |
| PyPI | Package registry | - | - | Cached packages |
| Claude Code CLI | External binary | - | - | Error with install guidance |
| GitHub Copilot CLI | External binary | - | - | Error with install guidance |
| OpenAI Codex CLI | External binary | - | - | Error with install guidance |
| Node.js | Runtime | - | - | Error with install guidance |
| Docker | Container runtime | - | - | Non-Docker mode |
| tmux | Terminal multiplexer | - | - | Single-session mode |
