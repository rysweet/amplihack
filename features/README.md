# Features Documentation

> [Home](../index.md) > Features

Ahoy! This be the treasure map to amplihack's specific features and third-party integrations.

## Quick Navigation

**Looking for something specific?**

- [Power Steering](#power-steering) - Intelligent session completion verification
- [Other Features](#other-features) - Additional amplihack features
- [Third-Party Integrations](#third-party-integrations) - External service connections

---

## Power Steering

Intelligent guidance system that prevents common mistakes and ensures work completeness:

- [Power Steering Overview](power-steering/README.md) - What is Power Steering and why use it
- [Configuration Guide](power-steering/configuration.md) - Complete configuration reference
- [Customization Guide](power-steering/customization-guide.md) - Customize considerations for your workflow
- [Troubleshooting](power-steering/troubleshooting.md) - Fix common Power Steering issues

**Key Benefits:**

- ✅ Reduces incomplete PRs by 30+%
- ✅ Reduces review cycles by 20+%
- ✅ Reduces CI failures by 15+%
- ✅ Prevents scope creep
- ✅ Enforces workflow compliance
- ✅ Respects user preferences (NEW)

---

## Other Features

Additional amplihack capabilities:

- [LSP Auto-Configuration](lsp-auto-configuration.md) - Zero-configuration Language Server Protocol setup
  - **Automatic**: Configures LSP when you run `amplihack claude`
  - **Multi-Language**: Supports 16 programming languages
  - **Complete Setup**: System binaries, plugins, and project configuration
- [Smart Memory Management](smart-memory-management.md) - Automatic Node.js memory optimization fer Claude Code launch
- [Claude.md Preservation](claude-md-preservation.md) - Preserve custom instructions during updates
- [Neo4j Session Cleanup](neo4j-session-cleanup.md) - Automatic resource management for memory system
- [Shutdown Detection](shutdown-detection.md) - Graceful exit handling (prevents 10-13s hang on exit)
  - [Technical Explanation](../concepts/shutdown-detection.md) - How and why it works
  - [API Reference](../reference/shutdown-detection-api.md) - Complete API documentation
  - [Developer How-To](../howto/add-shutdown-detection-to-hooks.md) - Add to custom hooks

---

## Third-Party Integrations

Connect amplihack with external services and tools:

- [GitHub Copilot via LiteLLM](../github-copilot-litellm-integration.md) - Use Copilot with amplihack
- [OpenAI Responses API](../OPENAI_RESPONSES_API.md) - OpenAI integration patterns
- [MCP Evaluation](../mcp_evaluation/README.md) - Model Context Protocol evaluation
- [Azure Integration](../AZURE_INTEGRATION.md) - Deploy to Azure cloud

---

## Configuration & Deployment

Feature-related configuration:

- [Hook Configuration](../HOOK_CONFIGURATION_GUIDE.md) - Customize framework behavior
- [Profile Management](../PROFILE_MANAGEMENT.md) - Multiple environment configurations
- [Proxy Configuration](../PROXY_CONFIG_GUIDE.md) - Network proxy setup

---

## Related Documentation

- [Workflows](../../.claude/workflow/DEFAULT_WORKFLOW.md) - How features integrate with workflows
- [Agents](../../.claude/agents/amplihack/README.md) - How agents use features
- [Commands](../commands/COMMAND_SELECTION_GUIDE.md) - Feature-related commands

---

Need help? Check the [Troubleshooting Guide](../troubleshooting/README.md) or [Discoveries](../DISCOVERIES.md) for common issues with features.
