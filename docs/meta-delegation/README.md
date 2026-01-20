# Meta-Agentic Task Delegation System

**Delegate complex tasks to AI agents running in isolated subprocess environments with automatic validation and evidence collection.**

---

## What is Meta-Delegation?

Meta-delegation is a system that runs AI agents (like guides, QA engineers, architects, or junior developers) in isolated subprocess environments to solve complex tasks autonomously. The meta-delegator monitors execution, collects evidence, validates success criteria, and provides detailed reports.

**Key Benefits:**

- **Isolated Execution**: Each agent runs in its own subprocess with no interference
- **Automatic Validation**: Success criteria are evaluated using evidence-based scoring
- **Multi-Platform Support**: Works with Claude Code, GitHub Copilot, or Microsoft Amplifier
- **Evidence Collection**: Captures artifacts, logs, and outputs for analysis
- **Persona Flexibility**: Choose from guide, QA engineer, architect, or junior developer personas

---

## Quick Start

### Basic Usage

```python
from amplihack.meta_delegation import run_meta_delegation

result = run_meta_delegation(
    goal="Create a REST API for user authentication with JWT tokens",
    success_criteria="API has login endpoint, returns valid JWT, includes tests",
    persona_type="architect",
    platform="claude-code"
)

print(f"Status: {result.status}")
print(f"Success Score: {result.success_score}/100")
print(f"Evidence: {len(result.evidence)} artifacts collected")
```

**Output:**

```
Status: SUCCESS
Success Score: 95/100
Evidence: 12 artifacts collected

Evidence Summary:
  - 3 code files generated
  - 4 tests passing
  - 2 documentation files
  - 1 architecture diagram
  - 2 validation reports
```

---

## When to Use Meta-Delegation

Use meta-delegation when you need:

1. **Complex Multi-Step Tasks**: Tasks requiring multiple phases (design, implementation, testing)
2. **Isolated Experimentation**: Try different approaches without affecting your main environment
3. **Validation Requirements**: Need proof that success criteria were met
4. **Persona-Specific Expertise**: Leverage specialized agent behavior (architect vs QA)
5. **Evidence-Based Decisions**: Require artifacts and logs for review

**Good Use Cases:**

- Prototype new features with full implementation and tests
- Generate architecture designs with validation
- Create comprehensive documentation with examples
- Run QA analysis on existing code
- Experiment with risky refactorings safely

**Poor Use Cases:**

- Simple one-line code changes (use direct agents instead)
- Interactive tasks requiring user input
- Tasks without clear success criteria
- Operations requiring access to your live environment

---

## Navigation

- **[Tutorial](./tutorial.md)** - Learn meta-delegation step-by-step (30 minutes)
- **[How-To Guide](./howto.md)** - Common tasks and recipes
- **[Reference](./reference.md)** - Complete API documentation
- **[Concepts](./concepts.md)** - Understanding the architecture
- **[Troubleshooting](./troubleshooting.md)** - Fix common issues

---

## Personas

Meta-delegation supports four persona types, each with different behavior:

| Persona      | Best For                          | Approach            | Output Style       |
| ------------ | --------------------------------- | ------------------- | ------------------ |
| `guide`      | Teaching and explaining           | Socratic, iterative | Tutorials, guides  |
| `qa_engineer`| Testing and validation            | Rigorous, thorough  | Test reports, bugs |
| `architect`  | Design and system architecture    | Strategic, holistic | Specs, diagrams    |
| `junior_dev` | Implementation following specs    | Task-focused, clean | Working code       |

See [Concepts](./concepts.md#personas) for detailed persona behavior.

---

## Platform Support

Meta-delegation works across three platforms:

| Platform       | Status      | Notes                                   |
| -------------- | ----------- | --------------------------------------- |
| `claude-code`  | ✅ Full     | Default, best integration               |
| `copilot`      | ✅ Full     | Requires GitHub Copilot CLI             |
| `amplifier`    | ✅ Full     | Requires Microsoft Amplifier            |

All platforms support:
- Subprocess isolation
- Evidence collection
- Success validation
- Full persona set

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Meta-Delegator Orchestrator                │
│  Coordinates all components and manages lifecycle            │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐  ┌──────────────────┐  ┌─────────────────┐
│   Platform    │  │  Persona Strategy│  │ Gadugi Scenario │
│ CLI Abstraction│  │     Module       │  │   Generator     │
│               │  │                  │  │                 │
│ Manages CLI   │  │ Selects behavior │  │ Creates test    │
│ execution     │  │ based on persona │  │ scenarios       │
└───────────────┘  └──────────────────┘  └─────────────────┘
        ↓                     ↓                     ↓
┌───────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  Subprocess   │  │ Success Criteria │  │    Evidence     │
│ State Machine │  │    Evaluator     │  │    Collector    │
│               │  │                  │  │                 │
│ Monitors      │  │ Scores results   │  │ Gathers         │
│ execution     │  │ against goals    │  │ artifacts       │
└───────────────┘  └──────────────────┘  └─────────────────┘
```

See [Concepts](./concepts.md#architecture) for detailed architecture.

---

## Example: Complete Workflow

```python
from amplihack.meta_delegation import run_meta_delegation

# 1. Define a complex task
goal = """
Create a Python module for parsing configuration files.
Support JSON, YAML, and TOML formats.
Include comprehensive tests and documentation.
"""

success_criteria = """
- Module has parse() function accepting file path and format
- Returns typed Config object with validation
- Has tests covering all three formats
- Includes README with usage examples
- All tests pass
"""

# 2. Run with architect persona for design
result = run_meta_delegation(
    goal=goal,
    success_criteria=success_criteria,
    persona_type="architect",
    platform="claude-code"
)

# 3. Check results
if result.status == "SUCCESS":
    print(f"✓ Architecture complete (score: {result.success_score}/100)")

    # Review evidence
    for evidence_item in result.evidence:
        print(f"  - {evidence_item.type}: {evidence_item.path}")

    # Read the architecture report
    arch_report = result.get_evidence_by_type("architecture_doc")[0]
    print(f"\nArchitecture:\n{arch_report.content}")
else:
    print(f"✗ Task failed: {result.failure_reason}")
    print(f"Partial progress: {result.success_score}/100")
```

**Output:**

```
✓ Architecture complete (score: 92/100)
  - architecture_doc: docs/config_parser_architecture.md
  - api_spec: specs/config_parser_api.yaml
  - code_file: src/config_parser/__init__.py
  - code_file: src/config_parser/parsers.py
  - test_file: tests/test_config_parser.py
  - documentation: README.md

Architecture:
# Configuration Parser Module

## Overview
Multi-format configuration parser supporting JSON, YAML, and TOML...

[Full architecture document contents]
```

---

## Quick Reference

### Common Commands

```python
# Run with default settings (guide persona, claude-code platform)
result = run_meta_delegation(goal="...", success_criteria="...")

# Use specific persona
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    persona_type="qa_engineer"
)

# Use different platform
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    platform="amplifier"
)

# Access results
print(result.status)           # "SUCCESS", "FAILURE", or "PARTIAL"
print(result.success_score)    # 0-100
print(result.evidence)         # List of EvidenceItem objects
print(result.execution_log)    # Full subprocess output
print(result.duration_seconds) # Execution time
```

### Result Status Codes

- **SUCCESS**: Task completed, success criteria met (score ≥ 80)
- **PARTIAL**: Task completed with issues (score 50-79)
- **FAILURE**: Task failed or success criteria not met (score < 50)

---

## Next Steps

1. **Learn the basics**: Start with the [Tutorial](./tutorial.md)
2. **Try common tasks**: Check the [How-To Guide](./howto.md)
3. **Understand internals**: Read the [Concepts](./concepts.md)
4. **Deep reference**: See the [API Reference](./reference.md)

---

## Related Documentation

- [Guide Agent](../claude/agents/amplihack/specialized/guide.md) - Socratic teaching agent
- [Outside-In Testing Skill](../claude/skills/outside-in-testing/SKILL.md) - Test-driven development
- [Goal Agent Generator](../GOAL_AGENT_GENERATOR_GUIDE.md) - Create autonomous agents
- [Agent Memory Integration](../AGENT_MEMORY_INTEGRATION.md) - How agents share knowledge

---

**Status**: [PLANNED - Implementation Pending]

This documentation describes the intended behavior of the meta-delegation system once implemented.
