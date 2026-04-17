# Troubleshooting Guide

> [Home](../index.md) > Troubleshooting

Ahoy, matey! Hit a snag? This be yer map to fix common issues and get back on course.

## 🚨 Start Here - Common Issues

**CHECK THIS FIRST!** Most problems have already been solved:

- **[Discoveries](../DISCOVERIES.md)** - Known issues and solutions (CHECK HERE FIRST!)

---

## Quick Fixes by Category

### Auto Mode Issues

- [Auto Mode Permission Error](AUTO_MODE_PERMISSION_ERROR.md) - Permission denied errors in auto mode

### Exit & Shutdown Issues

- [Stop Hook Exit Hang](stop-hook-exit-hang.md) - Fix 10-13 second hang on exit (resolved in v0.9.1)

### Installation Issues

- [Copytree Same-File Crash](copytree-same-file-crash.md) - Fix `SameFileError` when `AMPLIHACK_HOME` points at the source tree
- [Copilot Installation False Negative](copilot-installation-false-negative.md) - Installation reports failure when it actually succeeded

### Startup Issues

- [Startup Conflict Prompt](startup-conflict-prompt.md) - Fix "Uncommitted changes detected in .claude/" prompt on every startup

### Configuration Problems

- [Hook Configuration](../HOOK_CONFIGURATION_GUIDE.md) - Customize framework behavior
- [Profile Management](../PROFILE_MANAGEMENT.md) - Multi-environment configuration guidance

### Azure & Cloud

- [Azure Integration](../AZURE_INTEGRATION.md) - Azure deployment issues

---

## Documentation Issues

Having trouble with documentation?

- [Documentation Guidelines](../DOCUMENTATION_GUIDELINES.md) - Writing effective docs
- [Documentation Knowledge Graph](../documentation_knowledge_graph.md) - How docs connect

---

## Development & Testing Issues

Problems during development?

### Testing

- [Benchmarking](../BENCHMARKING.md) - Performance measurement
- [Test Gap Analyzer](../../.claude/skills/test-gap-analyzer/SKILL.md) - Find untested code

### Code Quality

- [Code Review Guide](../CODE_REVIEW.md) - Review process and standards
- [Default Workflow](../claude/workflow/DEFAULT_WORKFLOW.md) - End-to-end checklist for finishing work
- [CS Validator](../cs-validator/README.md) - Code style validation

---

## Memory System Issues

Problems with agent memory?

- [Memory System Docs](../memory/README.md) - Complete memory documentation
- [Memory Testing Strategy](../memory/TESTING_STRATEGY.md) - Validate memory behavior and coverage
- [Memory Code Review](../memory/CODE_REVIEW_PR_1077.md) - Example troubleshooting

---

## Security Issues

Security-related problems?

- [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) - Essential security practices
- [Security Context Preservation](../SECURITY_CONTEXT_PRESERVATION.md) - Maintain security through sessions
- [Security Guides](../security/README.md) - Security-specific troubleshooting and guidance

---

## Getting More Help

Still stuck? Here's what to do:

1. **Check Discoveries** - [DISCOVERIES.md](../DISCOVERIES.md) has most known issues
2. **Search Documentation** - Use the [Documentation Graph](../doc_graph_quick_reference.md)
3. **Review Patterns** - Check [Development Patterns](../../.claude/context/PATTERNS.md)
4. **Ask for Help** - [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)

---

## Prevention Guides

Learn how to avoid common issues:

- [Development Philosophy](../PHILOSOPHY.md) - Principles that prevent problems
- [This Is The Way](../THIS_IS_THE_WAY.md) - Best practices and patterns
- [Default Workflow](../claude/workflow/DEFAULT_WORKFLOW.md) - Ensure process compliance

---

## Related Documentation

- [Commands](../commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command
- [Agents](../claude/agents/README.md) - Agent-specific issues
- [Features](../features/README.md) - Feature troubleshooting

---

**Pro Tip**: Most issues are already documented in [DISCOVERIES.md](../DISCOVERIES.md). Always check there first!
