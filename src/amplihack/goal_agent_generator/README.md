# Goal Agent Generator

Generate autonomous goal-seeking agents from natural language prompts.

## Overview

The Goal Agent Generator creates self-contained, executable agents that can autonomously pursue complex goals. Given a natural language description of a goal, it:

1. **Analyzes** the goal to extract objectives, constraints, and success criteria
2. **Plans** a multi-phase execution strategy
3. **Synthesizes** relevant skills from existing capabilities
4. **Assembles** a complete agent bundle
5. **Packages** as a standalone, runnable agent

## Architecture

### Phase 1 MVP (Current)

```
Input: prompt.md (natural language goal)
↓
[Stage 1] Prompt Analysis → GoalDefinition
↓
[Stage 2] Objective Planning → ExecutionPlan
↓
[Stage 2b] Skill Synthesis → List[SkillDefinition]
↓
[Stage 3] Agent Assembly → GoalAgentBundle
↓
[Stage 4] Packaging → Standalone Agent Directory
```

### Components

#### 1. Prompt Analyzer (`prompt_analyzer.py`)

- Extracts primary goal from natural language
- Classifies domain (data-processing, security, automation, etc.)
- Identifies constraints and success criteria
- Determines complexity level

#### 2. Objective Planner (`objective_planner.py`)

- Generates 3-5 phase execution plans
- Identifies dependencies between phases
- Calculates required skills and capabilities
- Estimates duration and identifies risks

#### 3. Skill Synthesizer (`skill_synthesizer.py`)

- Matches existing skills to requirements
- Scores skill relevance (0-1)
- Currently copies from `~/.amplihack/.claude/agents/amplihack`
- Future: AI-generate custom skills

#### 4. Agent Assembler (`agent_assembler.py`)

- Combines all components into bundle
- Creates auto-mode configuration
- Generates initial prompts
- Validates completeness

#### 5. Packager (`packager.py`)

- Creates standalone agent directory
- Generates main.py entry point
- Writes README and documentation
- Packages skills and configuration

## Usage

### CLI

```bash
# Generate from prompt file
amplihack new --file my_goal.md

# Custom output directory
amplihack new --file my_goal.md --output ./my_agents

# Custom agent name
amplihack new --file my_goal.md --name my-custom-agent

# Verbose output
amplihack new --file my_goal.md --verbose
```

### Python API

```python
from pathlib import Path
from amplihack.goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)

# 1. Analyze prompt
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze(Path("my_goal.md"))

# 2. Create plan
planner = ObjectivePlanner()
plan = planner.generate_plan(goal_def)

# 3. Synthesize skills
synthesizer = SkillSynthesizer()
skills = synthesizer.synthesize_skills(plan)

# 4. Assemble bundle
assembler = AgentAssembler()
bundle = assembler.assemble(goal_def, plan, skills)

# 5. Package agent
packager = GoalAgentPackager()
agent_dir = packager.package(bundle)

print(f"Agent created: {agent_dir}")
```

## Generated Agent Structure

```
my-agent/
├── main.py                  # Entry point - run this
├── README.md                # Agent documentation
├── prompt.md                # Original goal prompt
├── agent_config.json        # Configuration
├── .claude/
│   ├── agents/              # Copied skill files
│   └── context/
│       ├── goal.json        # Structured goal
│       └── execution_plan.json  # Execution plan
└── logs/                    # Execution logs
```

### Running a Generated Agent

```bash
cd my-agent
python main.py
```

The agent will:

1. Load goal and execution plan
2. Initialize auto-mode with Claude SDK
3. Execute phases autonomously
4. Log progress and decisions
5. Report completion/failure

## Prompt Format

A goal prompt should include:

```markdown
# Goal: <Primary objective>

<Detailed description>

## Constraints

- Constraint 1
- Constraint 2

## Success Criteria

- Criterion 1
- Criterion 2

## Context

<Additional context>
```

See `example_goal_prompt.md` for a complete example.

## Domain Classification

Supported domains:

- **data-processing**: Data ingestion, transformation, analysis
- **security-analysis**: Vulnerability scanning, auditing, threat detection
- **automation**: Workflow automation, scheduling, monitoring
- **testing**: Test generation, validation, QA
- **deployment**: Release management, publishing, distribution
- **monitoring**: Metrics, alerts, observability
- **integration**: API connections, webhooks, data sync
- **reporting**: Dashboards, summaries, visualizations

## Complexity Levels

- **simple**: 5-minute tasks, 3-4 phases, minimal dependencies
- **moderate**: 15-30 minute tasks, 4-5 phases, some coordination
- **complex**: 30+ minute tasks, 5+ phases, distributed execution

## Auto-Mode Configuration

Generated agents use auto-mode with:

- Max turns based on complexity (5-15)
- Initial prompt from goal definition
- Success criteria as completion signals
- Constraints as guardrails

## Testing

```bash
# Run unit tests
pytest src/amplihack/goal_agent_generator/tests/test_*.py

# Run integration tests
pytest src/amplihack/goal_agent_generator/tests/test_integration.py

# Run specific test
pytest src/amplihack/goal_agent_generator/tests/test_prompt_analyzer.py -v
```

## Future Enhancements (Phase 2+)

1. **AI Skill Generation**: Generate custom skills instead of copying
2. **Interactive Refinement**: Allow user to refine plans before generation
3. **Multi-Agent Coordination**: Generate agent teams with coordination
4. **Template Library**: Pre-built templates for common patterns
5. **Metrics Dashboard**: Track agent performance and success rates
6. **Version Control**: Track agent iterations and improvements

## Philosophy Alignment

This module follows amplihack principles:

- **Ruthless Simplicity**: MVP uses skill copying, not complex generation
- **Zero-BS**: Every component is functional, no placeholders
- **Modular Design**: Each stage is self-contained and testable
- **Regeneratable**: Agents can be regenerated from prompt at any time

## Troubleshooting

### "No skills matched"

- Check that `~/.amplihack/.claude/agents/amplihack` exists
- Provide custom `--skills-dir` if using different location
- Generic executor will be used as fallback

### "Bundle incomplete"

- Verify prompt file has clear goal and domain
- Check that all required fields are present
- Review verbose output for validation errors

### "Generated agent fails to run"

- Ensure amplihack package is installed
- Verify Claude API access
- Check main.py has executable permissions

## Contributing

When extending the goal agent generator:

1. Add tests for new functionality
2. Update models.py for new data structures
3. Follow brick philosophy (self-contained modules)
4. Document new capabilities in this README

## References

- Auto-mode documentation: `docs/AUTO_MODE.md`
- Bundle generator: `src/amplihack/bundle_generator/`
- Existing skills: `~/.amplihack/.claude/agents/amplihack/`
