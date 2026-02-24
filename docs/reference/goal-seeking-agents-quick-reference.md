# Goal-Seeking Agents Quick Reference

Fast lookup for common commands, patterns, and workflows.

## Quick Start

```bash
# Create a new goal-seeking agent
amplihack new "Security auditor that scans code for vulnerabilities"

# Create with specific SDK
amplihack new --sdk copilot "API documentation generator"
amplihack new --sdk claude "Meeting notes synthesizer"
amplihack new --sdk microsoft "Code review assistant"

# Enable multi-agent architecture
amplihack new --multi-agent --sdk copilot "Complex research agent"

# Enable dynamic agent spawning
amplihack new --enable-spawning --sdk claude "Adaptive learning agent"
```

## CLI Reference

### Agent Generation

| Command | Description |
|---------|-------------|
| `amplihack new <goal>` | Generate agent with default SDK (copilot) |
| `--sdk {copilot,claude,microsoft,mini}` | Choose SDK backend |
| `--multi-agent` | Enable coordinator + memory + spawner architecture |
| `--enable-spawning` | Enable dynamic sub-agent spawning |
| `--domain {security,meetings,data,...}` | Generate domain-specific agent |

### Evaluation Commands

| Command | Description |
|---------|-------------|
| `python -m amplihack.eval.progressive_test_suite` | Run L1-L12 eval |
| `--runs 3` | 3-run median eval (recommended) |
| `--grader-votes 3` | Multi-vote grading for stability |
| `--sdk {mini,claude,copilot,microsoft}` | Test specific SDK |
| `--parallel N` | Run N evals concurrently |

### Self-Improvement Loop

| Command | Description |
|---------|-------------|
| `python -m amplihack.eval.sdk_eval_loop` | Run improvement iterations |
| `--sdk copilot --iterations 5` | 5 loops on Copilot SDK |
| `python -m amplihack.eval.matrix_eval` | 5-way agent comparison |

## SDK Selection Guide

| SDK | Best For | Pros | Cons |
|-----|----------|------|------|
| **Copilot** | GitHub workflows, code review | Native GitHub integration, fast | Requires GitHub account |
| **Claude** | Complex reasoning, research | Large context, strong reasoning | Higher cost |
| **Microsoft** | Enterprise workflows, Teams | Azure integration, governance | Requires Azure setup |
| **Mini** | Testing, prototypes, cost-sensitive | Lightweight, no dependencies | Limited capabilities |

## Evaluation Levels (L1-L12)

| Level | Focus | Pass Threshold |
|-------|-------|----------------|
| **L1** | Simple Recall | ≥85% |
| **L2** | Multi-Source Synthesis | ≥85% |
| **L3** | Temporal Reasoning | ≥70% |
| **L4** | Procedural Application | ≥80% |
| **L5** | Contradiction Resolution | ≥75% |
| **L6** | Incremental Updates | ≥85% |
| **L7** | Teaching Transfer | NLG ≥0.7 |
| **L8** | Metacognition | ≥50% |
| **L9** | Causal Reasoning | ≥50% |
| **L10** | Counterfactual Reasoning | ≥40% |
| **L11** | Novel Skill Acquisition | ≥50% |
| **L12** | Far Transfer | ≥60% |

## Common Patterns

### Generate and Evaluate

```bash
# 1. Generate agent
amplihack new --sdk copilot "Code documentation agent"

# 2. Navigate to generated directory
cd code_documentation_agent/

# 3. Run 3-run median eval with multi-vote grading
python -m amplihack.eval.progressive_test_suite \
  --runs 3 \
  --grader-votes 3 \
  --sdk copilot
```

### Self-Improvement Loop

```bash
# Run 5 improvement iterations
python -m amplihack.eval.sdk_eval_loop \
  --sdk copilot \
  --iterations 5 \
  --output improvement_report.json
```

### Multi-SDK Comparison

```bash
# Compare all 4 SDKs
python -m amplihack.eval.matrix_eval \
  --runs 3 \
  --output sdk_comparison.json
```

### Long-Horizon Memory Stress Test

```bash
# 1000-turn dialogue evaluation
python -m amplihack.eval.long_horizon_memory \
  --turns 1000 \
  --questions 20 \
  --output memory_eval.json
```

## Agent Architecture

### Single-Agent (Default)

```
┌──────────────────────┐
│   Learning Agent     │
│                      │
│ - 7 Learning Tools   │
│ - Memory System      │
│ - Intent Classifier  │
│ - Agentic Loop       │
└──────────────────────┘
```

### Multi-Agent (--multi-agent)

```
┌────────────────────────────────────────┐
│          Coordinator Agent             │
│   (Task routing and delegation)        │
└───────────┬────────────────────────────┘
            │
    ┌───────┴────────┬──────────────┐
    ▼                ▼              ▼
┌─────────┐    ┌──────────┐   ┌──────────┐
│ Memory  │    │ Reasoning│   │ Research │
│ Agent   │    │ Agent    │   │ Agent    │
└─────────┘    └──────────┘   └──────────┘
```

### With Spawning (--enable-spawning)

```
┌────────────────────────────────────────┐
│          Coordinator Agent             │
└───────────┬────────────────────────────┘
            │
    ┌───────┴────────┬──────────────────┐
    ▼                ▼                  ▼
┌─────────┐    ┌──────────┐   ┌──────────────────┐
│ Memory  │    │ Reasoning│   │ Agent Spawner    │
│ Agent   │    │ Agent    │   │ (Dynamic)        │
└─────────┘    └──────────┘   └──────────────────┘
                                       │
                            ┌──────────┴──────────┐
                            ▼                     ▼
                     ┌──────────┐         ┌──────────┐
                     │Retrieval │         │Synthesis │
                     │Sub-Agent │         │Sub-Agent │
                     └──────────┘         └──────────┘
```

## 7 Learning Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `learn_from_content` | Extract and store facts | Learn from articles, docs |
| `search_memory` | Retrieve knowledge | Find relevant facts |
| `synthesize_answer` | Combine facts to answer | Answer complex questions |
| `calculate` | Safe arithmetic | Compute medal totals |
| `explain_knowledge` | Teach concepts | Explain to beginners |
| `find_knowledge_gaps` | Identify missing info | Know what you don't know |
| `verify_fact` | Cross-check claims | Validate contradictions |

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API access | Required for Claude/Mini |
| `OPENAI_API_KEY` | OpenAI access | Required for Microsoft SDK |
| `COPILOT_MODEL` | Copilot model selection | `gpt-4` |
| `CLAUDE_AGENT_MODEL` | Claude SDK model | `claude-opus-4` |
| `MICROSOFT_AGENT_MODEL` | Microsoft SDK model | `gpt-4` |
| `EVAL_MODEL` | Evaluation LLM | `claude-opus-4` |
| `GRADER_MODEL` | Grading LLM | `claude-opus-4` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors for SDK | Install SDK: `pip install github-copilot-sdk` / `claude-agents` / `agent-framework` |
| Low eval scores | Run with `--runs 3 --grader-votes 3` for stability |
| Memory retrieval failures | Increase `simple_retrieval_threshold` in config |
| Slow evaluation | Use `--parallel 4` for concurrent runs |
| SDK agent not responding | Check API keys, verify SDK installation |

## File Structure

```
my_agent/
├── goal_prompt.md           # Agent goal and capabilities
├── prompts/                 # Markdown prompt templates
│   ├── system.md
│   ├── learning_task.md
│   └── synthesis_template.md
├── sdk_tools.json           # SDK-specific tool configs
├── sub_agents/              # Multi-agent configs (if --multi-agent)
│   ├── coordinator.yaml
│   ├── memory_agent.yaml
│   └── spawner.yaml
├── tests/                   # Unit tests
└── README.md                # Usage guide
```

## Related Documentation

- **Tutorial**: [Goal-Seeking Agent Tutorial](../tutorials/GOAL_SEEKING_AGENT_TUTORIAL.md)
- **How-To**: [Goal Agent Generator Guide](../GOAL_AGENT_GENERATOR_GUIDE.md)
- **Reference**: [Eval System Architecture](../EVAL_SYSTEM_ARCHITECTURE.md)
- **Explanation**: [Comprehensive Guide](../GOAL_SEEKING_AGENTS.md)
- **SDK Guide**: [SDK Adapters Guide](../SDK_ADAPTERS_GUIDE.md)
