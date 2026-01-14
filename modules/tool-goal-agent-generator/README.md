# Goal Agent Generator Tool

Generate specialized goal-seeking agents from natural language prompts.

## Overview

This Amplifier tool analyzes natural language goal descriptions and generates complete agent bundles including:

- **Goal Definition**: Extracted objectives, domain, constraints, and success criteria
- **Execution Plan**: Multi-phase plan with dependencies and parallel opportunities
- **Skills**: Matched skills from the amplihack skill library
- **Auto-Mode Configuration**: Settings for autonomous execution

## Installation

```bash
pip install -e modules/tool-goal-agent-generator/
```

## Usage

### As an Amplifier Tool

The tool is automatically available when installed. Agents can invoke it:

```
Generate a goal-seeking agent for:
"Create an automated security scanner that analyzes code repositories 
for vulnerabilities, generates reports, and tracks remediation progress."
```

### Programmatic Usage

```python
from tool_goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)

# Analyze the goal
analyzer = PromptAnalyzer()
goal = analyzer.analyze_text("Build a data processing pipeline...")

# Generate execution plan
planner = ObjectivePlanner()
plan = planner.generate_plan(goal)

# Match required skills
synthesizer = SkillSynthesizer(skills_directory=Path("./skills"))
skills = synthesizer.synthesize_skills(plan)

# Assemble the bundle
assembler = AgentAssembler()
bundle = assembler.assemble(goal, plan, skills, bundle_name="my-agent")

# Package for deployment
packager = GoalAgentPackager(output_dir=Path("./agents"))
agent_path = packager.package(bundle)
```

## Components

| Component | Purpose |
|-----------|---------|
| `PromptAnalyzer` | Extracts goal, domain, constraints from natural language |
| `ObjectivePlanner` | Generates multi-phase execution plans |
| `SkillSynthesizer` | Matches existing skills to requirements |
| `AgentAssembler` | Combines components into complete bundle |
| `GoalAgentPackager` | Packages bundle as deployable directory |

## Domain Templates

The planner includes templates for common domains:

- `data-processing` - ETL pipelines, data analysis
- `security-analysis` - Vulnerability scanning, auditing
- `automation` - Workflow automation, task scheduling
- `testing` - Test planning and execution
- `deployment` - Release and deployment pipelines
- `monitoring` - Observability and alerting

## Output Structure

Generated agent bundles include:

```
my-agent/
├── goal.md           # Goal definition
├── plan.md           # Execution plan
├── skills/           # Required skills
│   ├── skill-1.md
│   └── skill-2.md
├── auto-mode.json    # Auto-mode configuration
└── main.py           # Entry point script
```

## Philosophy

This tool embodies the amplihack philosophy:

- **Goal-Driven**: Agents are created for specific objectives
- **Modular**: Skills are composed, not hardcoded
- **Autonomous**: Auto-mode enables unsupervised execution
- **Transparent**: All components are readable markdown/JSON
