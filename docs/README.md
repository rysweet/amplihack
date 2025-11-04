# Amplihack Documentation

Complete documentation for the amplihack agentic coding framework.

## Getting Started

- [Prerequisites](PREREQUISITES.md) - Installation requirements and setup
- [Developing Amplihack](DEVELOPING_AMPLIHACK.md) - Developer guide and contribution guidelines

## Core Concepts

- [This Is The Way](THIS_IS_THE_WAY.md) - Philosophy and design principles
- [Auto Mode](AUTO_MODE.md) - Continuous autonomous work mode
- [Passthrough Mode](PASSTHROUGH_MODE.md) - Direct API passthrough

## Hooks and Automation

- **[Stop Hooks Guide](STOP_HOOKS_GUIDE.md)** - Complete guide to stop hooks, lock-based continuous work, and reflection system
- [Hook Configuration Guide](HOOK_CONFIGURATION_GUIDE.md) - How to configure and customize hooks
- [Shell Command Hook](SHELL_COMMAND_HOOK.md) - Shell command hook details

## Integration and Security

- [Azure Integration](AZURE_INTEGRATION.md) - Azure OpenAI integration guide
- [Security Context Preservation](SECURITY_CONTEXT_PRESERVATION.md) - Security context handling
- [Security Recommendations](SECURITY_RECOMMENDATIONS.md) - Security best practices

## Tools and Utilities

- [Create Your Own Tools](CREATE_YOUR_OWN_TOOLS.md) - Guide to creating custom tools
- [Proxy Configuration Guide](PROXY_CONFIG_GUIDE.md) - HTTP proxy setup

## Testing and Quality

- [Code Review](CODE_REVIEW.md) - Code review guidelines
- [Test Azure Proxy](TEST_AZURE_PROXY.md) - Testing Azure proxy integration

## Advanced Topics

- [UVX Data Models](UVX_DATA_MODELS.md) - UVX package data structures
- [OpenAI Responses API](OPENAI_RESPONSES_API.md) - API response handling
- [Tool Null Name Analysis](TOOL_NULL_NAME_ANALYSIS.md) - Tool naming analysis
- [Discoveries](DISCOVERIES.md) - Project discoveries and learnings
- [Amplifier Master Integration Plan](AMPLIFIER_MASTER_INTEGRATION_PLAN.md) - Integration architecture

## Directory Structure

```
docs/
├── README.md (this file)           # Documentation index
├── STOP_HOOKS_GUIDE.md             # Stop hooks and reflection (NEW)
├── PREREQUISITES.md                # Getting started
├── DEVELOPING_AMPLIHACK.md         # Developer guide
├── AUTO_MODE.md                    # Auto mode details
├── HOOK_CONFIGURATION_GUIDE.md     # Hook setup
├── cs-validator/                   # C# validator docs
├── document_driven_development/    # DDD methodology
└── testing/                        # Test specifications

```

## Quick Links by Topic

### For Users
- Getting Started: [Prerequisites](PREREQUISITES.md)
- Understanding Hooks: [Stop Hooks Guide](STOP_HOOKS_GUIDE.md)
- Configuring Behavior: [Hook Configuration](HOOK_CONFIGURATION_GUIDE.md)

### For Developers
- Contributing: [Developing Amplihack](DEVELOPING_AMPLIHACK.md)
- Creating Tools: [Create Your Own Tools](CREATE_YOUR_OWN_TOOLS.md)
- Code Review: [Code Review](CODE_REVIEW.md)

### For Integration
- Azure: [Azure Integration](AZURE_INTEGRATION.md)
- Proxy: [Proxy Configuration](PROXY_CONFIG_GUIDE.md)
- Security: [Security Recommendations](SECURITY_RECOMMENDATIONS.md)

---

**Questions or issues?** File at: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues
