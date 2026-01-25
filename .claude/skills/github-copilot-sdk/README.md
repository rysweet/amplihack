# GitHub Copilot SDK Skill

Navigation guide for building applications with the GitHub Copilot SDK across Python, TypeScript, Go, and .NET.

## Quick Navigation

**I want to...**

- **Get started fast** → [SKILL.md](./SKILL.md) - Essential patterns, 80% of use cases
- **Look up API details** → [reference.md](./reference.md) - Complete API reference for all languages
- **Choose my language** → [multi-language.md](./multi-language.md) - Language-specific guidance and trade-offs
- **Copy working examples** → [examples.md](./examples.md) - Production-ready code samples
- **Learn best practices** → [patterns.md](./patterns.md) - Production patterns and anti-patterns
- **Track SDK changes** → [drift-detection.md](./drift-detection.md) - Version compatibility and updates
- **Check quality** → [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) - Skill validation metrics

## Skill Contents

### SKILL.md (Start Here)
**2200 tokens** - Quick start guide covering 80% of use cases.

Essential reading for:
- First-time SDK users
- Building standard agent workflows
- Understanding core concepts quickly

### reference.md
**4500 tokens** - Complete API reference across all supported languages.

Use when you need:
- Detailed parameter specifications
- Return type information
- Authentication patterns
- Error handling approaches

### multi-language.md
**2500 tokens** - Language selection and comparison guide.

Read this when:
- Choosing between Python/TypeScript/Go/.NET
- Understanding language-specific trade-offs
- Working in polyglot environments
- Migrating between languages

### examples.md
**4000 tokens** - Copy-paste examples for common scenarios.

Contains working code for:
- Agent initialization and setup
- Tool integration patterns
- Message handling
- Session management
- Production error handling

### patterns.md
**3000 tokens** - Production patterns and architectural guidance.

Covers:
- Stateless agent design
- Tool composition
- Error recovery strategies
- Testing approaches
- Performance optimization

### drift-detection.md
**2000 tokens** - Version tracking and compatibility monitoring.

Learn about:
- SDK version detection
- Breaking change identification
- Migration strategies
- Compatibility matrices

## Typical Workflows

### Building Your First Agent

1. [SKILL.md](./SKILL.md) - Read Quick Start section
2. [multi-language.md](./multi-language.md) - Choose your language
3. [examples.md](./examples.md) - Copy initialization example
4. [patterns.md](./patterns.md) - Review stateless design section

### Adding Tool Integration

1. [reference.md](./reference.md) - Look up tool registration API
2. [examples.md](./examples.md) - Copy tool integration example
3. [patterns.md](./patterns.md) - Review tool composition patterns

### Production Deployment

1. [patterns.md](./patterns.md) - Read production section
2. [reference.md](./reference.md) - Review error handling APIs
3. [drift-detection.md](./drift-detection.md) - Set up version tracking

### Troubleshooting

1. [SKILL.md](./SKILL.md) - Check common issues section
2. [examples.md](./examples.md) - Verify your code matches examples
3. [drift-detection.md](./drift-detection.md) - Check for version mismatches

## Language Support

This skill covers all official SDK languages:

- **Python** - Most examples, best for rapid development
- **TypeScript** - Strong typing, Node.js ecosystem
- **Go** - Performance, concurrency primitives
- **.NET (C#)** - Enterprise integration, Windows deployments

See [multi-language.md](./multi-language.md) for detailed comparison.

## Quality Metrics

See [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) for:
- Example verification status
- API coverage metrics
- Last validation date
- Known gaps

## Philosophy Alignment

This skill follows amplihack's ruthless simplicity:

- **Real examples only** - All code is tested and runnable
- **No over-abstraction** - Direct SDK usage, minimal wrappers
- **One clear path** - Show the best way, not every way
- **Production-ready** - Patterns proven in real deployments

## Contributing

When updating this skill:

1. Keep SKILL.md focused on essentials (≤2200 tokens)
2. Add comprehensive details to reference.md
3. All examples must be tested and working
4. Update drift-detection.md when SDK versions change
5. Regenerate VALIDATION_REPORT.md after changes

---

**Start here**: [SKILL.md](./SKILL.md) - Get building in 5 minutes.
