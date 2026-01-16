# amplihack

**Agentic coding framework that uses specialized AI agents to accelerate software development through intelligent automation and collaborative problem-solving.**

## What is amplihack?

amplihack is a development tool built on Claude Code that leverages multiple specialized AI agents working together to handle complex software development tasks. It combines ruthless simplicity with powerful capabilities to make AI-assisted development more effective and maintainable.

## Quick Navigation

**New to amplihack?** Start here:

- [Get Started](#-get-started) - Installation and first steps
- [Core Concepts](#-core-concepts) - Philosophy and principles
- [First Docs Site Tutorial](tutorials/first-docs-site.md) - Create your first documentation site

**Looking for something specific?**

- [Commands & Operations](#%EF%B8%8F-commands--operations) - Execute complex tasks
- [Workflows](#-workflows) - Structured development processes
- [Agents & Tools](#-agents--tools) - Specialized AI capabilities
- [Troubleshooting](#-troubleshooting--discoveries) - Fix common issues

---

## 🚀 Get Started

Everything you need to install and configure amplihack.

### Installation

- [Prerequisites](PREREQUISITES.md) - System requirements and dependencies
- [Interactive Installation](INTERACTIVE_INSTALLATION.md) - Step-by-step setup wizard
- [Quick Start](README.md) - Basic usage and first commands

### Configuration

- [Profile Management](PROFILE_MANAGEMENT.md) - Multiple environment configurations
- [Proxy Configuration](PROXY_CONFIG_GUIDE.md) - Network proxy setup
- [Hook Configuration](HOOK_CONFIGURATION_GUIDE.md) - Customize framework behavior
- [Copilot CLI Setup](COPILOT_SETUP.md) - Setup and integration for GitHub Copilot CLI

### Deployment

- [UVX Deployment](UVX_DEPLOYMENT_SOLUTIONS.md) - Deploy with uvx
- [UVX Data Models](UVX_DATA_MODELS.md) - Understanding uvx data structures
- [Azure Integration](AZURE_INTEGRATION.md) - Deploy to Azure cloud

---

## 💡 Core Concepts

Understand the philosophy and architecture behind amplihack.

### Philosophy & Principles

- [Development Philosophy](PHILOSOPHY.md) - Ruthless simplicity and modular design
- [This Is The Way](THIS_IS_THE_WAY.md) - Best practices and patterns
- [Workspace Pattern](WORKSPACE_PATTERN.md) - Organize your development environment
- [Trust & Anti-Sycophancy](claude/context/TRUST.md) - Honest agent behavior

### Architecture

- [Project Overview](claude/context/PROJECT.md) - System architecture
- [Development Patterns](claude/context/PATTERNS.md) - Proven implementation patterns
- [Blarify Architecture](blarify_architecture.md) - Understanding the Blarify integration
- [Documentation Knowledge Graph](documentation_knowledge_graph.md) - How docs connect
- [Copilot CLI vs Claude Code](architecture/COPILOT_CLI_VS_CLAUDE_CODE.md) - Architecture comparison

### Key Features

- [Modular Design](#-modular-design-philosophy) - Self-contained modules (bricks & studs)
- [Zero-BS Implementation](#-zero-bs-implementation) - No stubs or placeholders
- [Specialized AI Agents](#-specialized-ai-agents) - Purpose-built for each task
- [Structured Workflows](#-structured-workflows) - Proven methodologies

---

## 📋 Workflows

Proven methodologies for consistent, high-quality results.

### Core Workflows

- [Default Workflow](claude/workflow/DEFAULT_WORKFLOW.md) - Standard multi-step development process
- [Investigation Workflow](claude/workflow/INVESTIGATION_WORKFLOW.md) - Deep codebase analysis and understanding
- [Document-Driven Development (DDD)](document_driven_development/README.md) - Documentation-first approach for large features

### DDD Deep Dive

Document-Driven Development is a systematic methodology where documentation comes first and acts as the specification.

- **Core Concepts**
  - [Overview](document_driven_development/README.md) - What is DDD and when to use it
  - [Core Concepts](document_driven_development/core_concepts/README.md) - File crawling, context poisoning, retcon writing
  - [File Crawling](document_driven_development/core_concepts/file_crawling.md) - Systematic file processing
  - [Context Poisoning](document_driven_development/core_concepts/context_poisoning.md) - Preventing inconsistencies
  - [Retcon Writing](document_driven_development/core_concepts/retcon_writing.md) - Present-tense documentation

- **Implementation Phases**
  - [Phase 0: Planning](document_driven_development/phases/00_planning_and_alignment.md) - Define scope and objectives
  - [Phase 1: Documentation](document_driven_development/phases/01_documentation_retcon.md) - Write the spec
  - [Phase 2: Approval](document_driven_development/phases/02_approval_gate.md) - Review and validate
  - [Phase 3: Code Planning](document_driven_development/phases/03_implementation_planning.md) - Implementation strategy
  - [Phase 4: Implementation](document_driven_development/phases/04_code_implementation.md) - Build it
  - [Phase 5: Testing](document_driven_development/phases/05_testing_and_verification.md) - Verify behavior
  - [Phase 6: Cleanup](document_driven_development/phases/06_cleanup_and_push.md) - Final touches

- **Reference**
  - [Reference Materials](document_driven_development/reference/README.md) - Practical resources
  - [Checklists](document_driven_development/reference/checklists.md) - Phase verification
  - [Tips for Success](document_driven_development/reference/tips_for_success.md) - Best practices
  - [Common Pitfalls](document_driven_development/reference/common_pitfalls.md) - What to avoid
  - [FAQ](document_driven_development/reference/faq.md) - Common questions

### Advanced Workflows

- [N-Version Programming](claude/workflow/N_VERSION_WORKFLOW.md) - Multiple solutions for critical code
- [Multi-Agent Debate](claude/workflow/DEBATE_WORKFLOW.md) - Structured decision-making
- [Cascade Workflow](claude/workflow/CASCADE_WORKFLOW.md) - Graceful degradation patterns
- [Workflow Enforcement](workflow-enforcement.md) - Ensure process compliance

---

## 🤖 Agents & Tools

Specialized AI agents and tools for every development task.

### Core Agents

- [Agents Overview](claude/agents/amplihack/README.md) - Complete agent catalog
- [Architect](claude/agents/amplihack/core/architect.md) - System design and specifications
- [Builder](claude/agents/amplihack/core/builder.md) - Code implementation from specs
- [Reviewer](claude/agents/amplihack/core/reviewer.md) - Quality assurance and compliance
- [Tester](claude/agents/amplihack/core/tester.md) - Test generation and validation

### Specialized Agents

- [API Designer](claude/agents/amplihack/specialized/api-designer.md) - Contract definitions
- [Security Agent](claude/agents/amplihack/specialized/security.md) - Vulnerability assessment
- [Database Agent](claude/agents/amplihack/specialized/database.md) - Schema and query optimization
- [Integration Agent](claude/agents/amplihack/specialized/integration.md) - External service connections
- [Cleanup Agent](claude/agents/amplihack/specialized/cleanup.md) - Code simplification

### Goal-Seeking Agents

**Autonomous agents that iterate toward objectives without stopping.**

- [Goal Agent Generator Guide](GOAL_AGENT_GENERATOR_GUIDE.md) - Create custom goal-seeking agents
- [Goal Agent Generator Presentation](GOAL_AGENT_GENERATOR_PRESENTATION.md) - Concept overview
- [Goal Agent Generator Design](agent-bundle-generator-design.md) - Architecture and patterns
- [Goal Agent Requirements](agent-bundle-generator-requirements.md) - Specifications
- [Implementation Summary](goal_agent_generator/IMPLEMENTATION_SUMMARY.md) - Current status

**Key Feature**: Goal-seeking agents work autonomously toward a defined objective, iterating and adapting without requiring user intervention at each step. Perfect for complex, open-ended tasks.

### Workflow Agents

- [Ambiguity Handler](claude/agents/amplihack/specialized/ambiguity.md) - Clarify unclear requirements
- [Optimizer](claude/agents/amplihack/specialized/optimizer.md) - Performance improvements
- [Pattern Recognition](claude/agents/amplihack/specialized/patterns.md) - Identify reusable solutions

### Claude Code Skills

Modular, on-demand capabilities that extend amplihack:

- [Skills Catalog](skills/SKILL_CATALOG.md) - Complete skills catalog
- [Documentation Writing](claude/skills/documentation-writing/README.md) - Eight Rules compliance
- [Mermaid Diagrams](claude/skills/mermaid-diagram-generator/SKILL.md) - Visual documentation
- [Test Gap Analyzer](claude/skills/test-gap-analyzer/SKILL.md) - Find untested code
- [Code Smell Detector](claude/skills/code-smell-detector/SKILL.md) - Identify anti-patterns

### Scenario Tools

Production-ready executable tools following the Progressive Maturity Model:

- [Scenario Tools Overview](claude/scenarios/README.md) - Progressive maturity model
- [Create Your Own Tools](CREATE_YOUR_OWN_TOOLS.md) - Build custom tools
- [Agent Bundle Generator](agent-bundle-generator-guide.md) - Package agents for distribution

#### Available Tools

- **[check-broken-links](claude/scenarios/check-broken-links/README.md)** - Automated link checker for documentation sites and markdown files
  - Check GitHub Pages sites or local documentation
  - Catch broken internal links and dead external URLs
  - Integrates with Makefile: `make check-broken-links TARGET=<url-or-path>`
  - Returns exit codes for CI integration

---

## ⚡️ Commands & Operations

Execute complex tasks with simple slash commands.

### Command Reference

- [Command Selection Guide](commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command for your task

### Core Commands

- `/ultrathink` - Main orchestration command (reads workflow, orchestrates agents)
- `/analyze` - Comprehensive code review for philosophy compliance
- `/improve` - Capture learnings and self-improvement
- `/fix` - Intelligent fix workflow for common error patterns

### Document-Driven Development Commands

- `/ddd:0-help` - Get help and understand DDD
- `/ddd:prime` - Prime context with DDD overview
- `/ddd:1-plan` - Phase 0: Planning & Alignment
- `/ddd:2-docs` - Phase 1: Documentation Retcon
- `/ddd:3-code-plan` - Phase 3: Implementation Planning
- `/ddd:4-code` - Phase 4: Code Implementation
- `/ddd:5-finish` - Phase 5: Testing & Phase 6: Cleanup
- `/ddd:status` - Check current phase and progress

### Advanced Commands

- `/amplihack:n-version <task>` - Generate N independent solutions for critical code
- `/amplihack:debate <question>` - Multi-agent structured debate for decisions
- `/amplihack:cascade <task>` - Fallback cascade for resilient operations
- `/amplihack:customize` - Manage user preferences and settings

### Auto Mode

- [Auto Mode Guide](AUTO_MODE.md) - Autonomous multi-turn execution
- [Auto Mode Safety](AUTOMODE_SAFETY.md) - Safety guardrails and best practices
- [Passthrough Mode](PASSTHROUGH_MODE.md) - Direct API access

---

## 🧠 Memory & Knowledge

Persistent memory systems and knowledge management.

### 5-Type Memory System ⭐ NEW

Psychological memory model with episodic, semantic, procedural, prospective, and working memory:

- [5-Type Memory Guide](memory/5-TYPE-MEMORY-GUIDE.md) - Complete user guide
- [Developer Reference](memory/5-TYPE-MEMORY-DEVELOPER.md) - Architecture and API
- [Quick Reference](memory/5-TYPE-MEMORY-QUICKREF.md) - One-page cheat sheet
- [Kùzu Schema](memory/KUZU_MEMORY_SCHEMA.md) - Graph database design
- [Terminal Visualization](memory/MEMORY_TREE_VISUALIZATION.md) - View graph in terminal
- [Memory System Overview](memory/README.md) - Complete memory documentation

### Memory Systems

- [Agent Memory Integration](AGENT_MEMORY_INTEGRATION.md) - How agents share and persist knowledge
- [Agent Memory Quickstart](AGENT_MEMORY_QUICKSTART.md) - Get started with memory
- [Agent Type Memory Sharing](agent_type_memory_sharing_patterns.md) - Patterns for memory collaboration

### Neo4j Memory System

Advanced graph-based memory for complex knowledge representation:

- [Neo4j Memory Quick Reference](neo4j_memory/quick_reference.md) - Fast answers
- [Neo4j Phase 4 Implementation](neo4j_memory_phase4_implementation.md) - Latest features
- [Documentation Graph](doc_graph_quick_reference.md) - Navigate documentation connections

**Research & Deep Dives**:

- [Executive Summary](research/neo4j_memory_system/00-executive-summary/README.md)
- [Technical Research](research/neo4j_memory_system/01-technical-research/README.md)
- [Design Patterns](research/neo4j_memory_system/02-design-patterns/README.md)
- [Integration Guides](research/neo4j_memory_system/03-integration-guides/README.md)
- [External Knowledge](research/neo4j_memory_system/04-external-knowledge/README.md)

### Memory Testing

- [A/B Test Summary](memory/AB_TEST_SUMMARY.md) - Performance comparisons
- [A/B Test Quick Reference](memory/AB_TEST_QUICK_REFERENCE.md) - Test results at a glance
- [Effectiveness Test Design](memory/EFFECTIVENESS_TEST_DESIGN.md) - How we measure success
- [Final Cleanup Report](memory/FINAL_CLEANUP_REPORT.md) - Memory system cleanup

### External Knowledge

- [External Knowledge Integration](external_knowledge_integration.md) - Import external data sources
- [Blarify Integration](blarify_integration.md) - Connect with Blarify knowledge base
- [Blarify Quickstart](blarify_quickstart.md) - Get started with Blarify

---

## 🔧 Features & Integrations

Specific features and third-party integrations.

### Power Steering

Intelligent guidance system that prevents common mistakes:

- [Power Steering Overview](features/power-steering/README.md) - What is Power Steering
- [Architecture](features/power-steering/architecture.md) - How it works
- [Configuration](features/power-steering/configuration.md) - Setup and customization
- [Troubleshooting](features/power-steering/troubleshooting.md) - Fix infinite loop and other issues
- [Migration Guide v0.9.1](features/power-steering/migration-v0.9.1.md) - Upgrade guide
- [Technical Reference](features/power-steering/technical-reference.md) - Developer reference
- [Changelog v0.9.1](features/power-steering/changelog-v0.9.1.md) - Infinite loop fix release notes

### Other Features

- [Claude.md Preservation](features/claude-md-preservation.md) - Preserve custom instructions
- [Neo4j Session Cleanup](features/neo4j-session-cleanup.md) - Automatic resource management
- [Shutdown Detection](concepts/shutdown-detection.md) - Graceful exit handling (prevents 10-13s hang)

### Third-Party Integrations

- [GitHub Copilot via LiteLLM](github-copilot-litellm-integration.md) - Use Copilot with amplihack
- [OpenAI Responses API](OPENAI_RESPONSES_API.md) - OpenAI integration patterns
- [MCP Evaluation](mcp_evaluation/README.md) - Model Context Protocol evaluation

---

## ⚙️ Configuration & Deployment

Advanced configuration, deployment patterns, and environment management.

### Configuration

- [Profile Management](PROFILE_MANAGEMENT.md) - Multiple environment configurations
- [Proxy Configuration](PROXY_CONFIG_GUIDE.md) - Network proxy setup
- [Hook Configuration](HOOK_CONFIGURATION_GUIDE.md) - Customize framework behavior
- [Shell Command Hook](SHELL_COMMAND_HOOK.md) - Custom shell integrations

### Deployment

- [UVX Deployment Solutions](UVX_DEPLOYMENT_SOLUTIONS.md) - Production deployment with uvx
- [UVX Data Models](UVX_DATA_MODELS.md) - Understanding uvx data structures
- [Azure Integration](AZURE_INTEGRATION.md) - Deploy to Azure cloud
- [Test Azure Proxy](TEST_AZURE_PROXY.md) - Validate Azure proxy setup

### Remote Sessions

- [Remote Sessions Overview](remote-sessions/README.md) - Execute on remote machines
- [Remote Session Architecture](remote-sessions/architecture.md) - How remote execution works
- [Remote Session Security](remote-sessions/security.md) - Secure remote operations

---

## 🧪 Testing & Quality

Testing strategies, quality assurance, and validation patterns.

### Testing

- [Benchmarking](BENCHMARKING.md) - Performance measurement and comparison
- [Test Gap Analyzer](claude/skills/test-gap-analyzer/SKILL.md) - Find untested code
- [CS Validator](cs-validator/README.md) - Code style validation
- [Testing Strategies](testing/README.md) - Comprehensive testing guide

### Code Review

- [Code Review Guide](CODE_REVIEW.md) - Review process and standards
- [Memory Code Review](memory/CODE_REVIEW_PR_1077.md) - Example: Memory system review
- [Workflow Completion](WORKFLOW_COMPLETION.md) - Checklist for finishing features

---

## 🔒 Security

Security guidelines, context preservation, and best practices.

### Security Documentation

- [Security Recommendations](SECURITY_RECOMMENDATIONS.md) - Essential security practices
- [Security Context Preservation](SECURITY_CONTEXT_PRESERVATION.md) - Maintain security through sessions
- [Security Guides](security/README.md) - Comprehensive security documentation

### Safe Operations

- [Auto Mode Safety](AUTOMODE_SAFETY.md) - Autonomous operation guardrails
- [Passthrough Mode](PASSTHROUGH_MODE.md) - Direct API access patterns

---

## 🛠️ Troubleshooting & Discoveries

Fix common issues and learn from past solutions.

### Troubleshooting

- [Discoveries](DISCOVERIES.md) - Known issues and solutions (CHECK HERE FIRST!)
- [Troubleshooting Guides](troubleshooting/README.md) - Common problems and fixes
- [Stop Hook Exit Hang](troubleshooting/stop-hook-exit-hang.md) - Fix 10-13s hang on exit (resolved v0.9.1)
- [Tool Null Name Analysis](TOOL_NULL_NAME_ANALYSIS.md) - Debugging tool name issues
- [Config Analysis Report](config-analysis-report.md) - Configuration problem diagnosis

### Documentation Guides

- [Documentation Guidelines](DOCUMENTATION_GUIDELINES.md) - Writing effective docs
- [Documentation Structure Analysis](DOCUMENTATION_STRUCTURE_ANALYSIS.md) - Current state of docs
- [How to Generate GitHub Pages](howto/github-pages-generation.md) - Publish your docs

---

## 🔬 Research & Advanced Topics

Cutting-edge research, experimental features, and deep technical dives.

### Research Projects

- [Neo4j Memory System Research](research/neo4j_memory_system/README.md) - Complete research archive
  - [Executive Summary](research/neo4j_memory_system/00-executive-summary/README.md)
  - [Technical Research](research/neo4j_memory_system/01-technical-research/README.md)
  - [Design Patterns](research/neo4j_memory_system/02-design-patterns/README.md)
  - [Integration Guides](research/neo4j_memory_system/03-integration-guides/README.md)
  - [External Knowledge](research/neo4j_memory_system/04-external-knowledge/README.md)

### Advanced Topics

- [Agent Type Memory Sharing Patterns](agent_type_memory_sharing_patterns.md) - Advanced memory patterns
- [Documentation Knowledge Graph](documentation_knowledge_graph.md) - Graph-based doc navigation
- [Workspace Pattern](WORKSPACE_PATTERN.md) - Advanced workspace organization

---

## 📚 Reference & Resources

Quick references, guides, and additional resources.

### Quick References

- [Command Selection Guide](commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command
- [Doc Graph Quick Reference](doc_graph_quick_reference.md) - Navigate documentation
- [Neo4j Quick Reference](neo4j_memory/quick_reference.md) - Memory system commands
- [A/B Test Quick Reference](memory/AB_TEST_QUICK_REFERENCE.md) - Test results

### Developing amplihack

- [Developing amplihack](DEVELOPING_AMPLIHACK.md) - Contribute to the framework
- [Create Your Own Tools](CREATE_YOUR_OWN_TOOLS.md) - Build custom tools
- [Workflow to Skills Migration](WORKFLOW_TO_SKILLS_MIGRATION.md) - Migration guide

### Contributing

- [File Organization](contributing/file-organization.md) - Where different file types belong in the repository

### GitHub & Community

- [GitHub Repository](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding) - Source code
- [Issue Tracker](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues) - Report bugs or request features
- [GitHub Pages](https://rysweet.github.io/amplihack/) - Online documentation

---

## Philosophy in Action

amplihack follows three core principles:

1. **Ruthless Simplicity**: Start with the simplest solution that works. Add complexity only when justified.

2. **Modular Design**: Build self-contained modules (bricks) with clear public contracts (studs) that others can connect to.

3. **Zero-BS Implementation**: No stubs, no placeholders, no dead code. Every function must work or not exist.

---

## Example Workflow

```bash
# Start with a feature request
/ultrathink "Add user authentication to the API"

# UltraThink will:
# 1. Read the default workflow
# 2. Orchestrate multiple agents (architect, security, api-designer, database, builder, tester)
# 3. Follow all workflow steps systematically
# 4. Ensure quality and philosophy compliance
# 5. Generate tests and documentation
```

---

## Use Cases

amplihack excels at:

- **Feature Development**: Orchestrate multiple agents to design, implement, test, and document new features
- **Code Review**: Comprehensive analysis for philosophy compliance and best practices
- **Refactoring**: Systematic cleanup and improvement of existing code
- **Investigation**: Deep understanding of complex codebases and architectures
- **Integration**: Connect external services with proper error handling and testing
- **Security**: Vulnerability assessment and secure implementation patterns

---

## Need Help?

- **Start here**: [Prerequisites](PREREQUISITES.md) → [Interactive Installation](INTERACTIVE_INSTALLATION.md) → [Quick Start](README.md)
- **Common issues**: Check [Discoveries](DISCOVERIES.md) first
- **Questions**: See [DDD FAQ](document_driven_development/reference/faq.md)
- **Report issues**: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)

---

**Ready to get started?** Head to [Prerequisites](PREREQUISITES.md) to set up amplihack in your development environment.
