# Goal-Seeking Agent Generator Tutorial

A step-by-step guide to generating, evaluating, and iterating on autonomous
learning agents in amplihack. This tutorial covers the complete workflow from
writing your first prompt file to running self-improvement loops.

---

## Table of Contents

1. [Introduction to Goal-Seeking Agents](#1-introduction-to-goal-seeking-agents)
2. [Your First Agent](#2-your-first-agent)
3. [SDK Selection Guide](#3-sdk-selection-guide)
4. [Multi-Agent Architecture](#4-multi-agent-architecture)
5. [Agent Spawning](#5-agent-spawning)
6. [Running Evaluations](#6-running-evaluations)
7. [Understanding Eval Levels](#7-understanding-eval-levels)
8. [Self-Improvement Loop](#8-self-improvement-loop)
9. [Security Domain Agents](#9-security-domain-agents)
10. [Custom Eval Levels](#10-custom-eval-levels)
11. [Troubleshooting](#troubleshooting)
12. [Reference](#reference)

---

## 1. Introduction to Goal-Seeking Agents

### What Is a Goal-Seeking Agent?

A goal-seeking agent is an autonomous program that pursues an objective by
**learning**, **remembering**, **teaching**, and **applying** knowledge. Unlike
a static script that follows a fixed sequence, these agents:

- **Learn**: Extract facts from content and store them in persistent memory.
- **Remember**: Search, verify, and organize knowledge across sessions.
- **Teach**: Explain what they know to other agents (or humans).
- **Apply**: Use stored knowledge and tools to solve new problems.

### Architecture

The generator pipeline has five stages:

```
Prompt (.md) --> PromptAnalyzer --> GoalDefinition
                                        |
                            ObjectivePlanner --> ExecutionPlan
                                        |
                           SkillSynthesizer --> Skills + SDK Tools
                                        |
                            AgentAssembler --> GoalAgentBundle
                                        |
                          GoalAgentPackager --> /goal_agents/<name>/
```

1. **Analyze**: Extract goal, domain, constraints from a markdown file.
2. **Plan**: Break the goal into phases with capabilities.
3. **Synthesize**: Match skills and SDK-native tools to capabilities.
4. **Assemble**: Build the agent bundle with config and metadata.
5. **Package**: Write the bundle to disk as a runnable project.

### The GoalSeekingAgent Interface

Every generated agent implements the same interface regardless of SDK:

```python
class GoalSeekingAgent:
    async def learn(self, content: str) -> list[str]
    async def remember(self, query: str) -> str
    async def teach(self, topic: str) -> str
    async def execute(self, instruction: str) -> str
```

Write your agent logic once; swap SDKs freely.

### Exercise

List the four capabilities of a goal-seeking agent and give a one-sentence
example for each.

**Expected**: Learn (extract facts from articles), Remember (retrieve stored
knowledge by query), Teach (explain topics to other agents), Apply (use tools
to solve new problems).

---

## 2. Your First Agent

### Step 1: Write a Prompt File

Create `my_goal.md`:

```markdown
# Goal: Learn and Summarize Python Best Practices

## Objective

Build an agent that reads Python style guides and can answer
questions about best practices.

## Domain

software-engineering

## Constraints

- Focus on PEP-8 and type-hinting
- Keep answers concise

## Success Criteria

- Can explain PEP-8 naming conventions
- Can describe when to use type hints
```

The prompt file requires four sections: **Goal/Objective**, **Domain**,
**Constraints**, and **Success Criteria**.

### Step 2: Generate the Agent

```bash
amplihack new --file my_goal.md
```

This runs the full pipeline and creates a directory under `./goal_agents/`.

With custom output directory and name:

```bash
amplihack new --file my_goal.md --name python-coach --output ./agents
```

### Step 3: Run the Agent

```bash
cd goal_agents/python-coach
python main.py
```

### What Happens Under the Hood

1. `PromptAnalyzer` parses `my_goal.md` and extracts goal, domain, constraints.
2. `ObjectivePlanner` creates an `ExecutionPlan` with phases.
3. `SkillSynthesizer` matches skills from `.claude/agents/amplihack/`.
4. `AgentAssembler` builds the `GoalAgentBundle`.
5. `GoalAgentPackager` writes files to disk.

### Exercise

Write a prompt file for an agent that learns Docker container security. Then
write the CLI command to generate it.

**Expected prompt structure**:

```markdown
# Goal: Learn Docker Container Security

## Domain

security

## Constraints

- Focus on container isolation and image scanning

## Success Criteria

- Can explain Docker namespaces
```

**Expected command**: `amplihack new --file docker_security.md --verbose`

---

## 3. SDK Selection Guide

The generator supports four SDK backends. The `--sdk` flag selects which one.

### Copilot SDK (default)

```bash
amplihack new --file goal.md --sdk copilot
```

- **Strengths**: GitHub integration, file_system/git/web tools.
- **Best for**: Repository automation, code review agents.
- **Requires**: GitHub Copilot access.

### Claude SDK

```bash
amplihack new --file goal.md --sdk claude
```

- **Strengths**: Rich tool set (bash, read/write/edit files, glob, grep).
- **Best for**: General-purpose agents, code analysis, file manipulation.
- **Requires**: `ANTHROPIC_API_KEY`.

### Microsoft Agent Framework

```bash
amplihack new --file goal.md --sdk microsoft
```

- **Strengths**: Enterprise integration, AI function primitives.
- **Best for**: Enterprise workflows, Azure-connected agents.
- **Requires**: More setup, fewer built-in tools.

### Mini SDK

```bash
amplihack new --file goal.md --sdk mini
```

- **Strengths**: Lightweight, minimal dependencies, fast iteration.
- **Best for**: Prototyping, testing, eval benchmarks.
- **Requires**: Nothing extra.

### Decision Matrix

| Need                       | Recommended SDK |
| -------------------------- | --------------- |
| GitHub automation          | copilot         |
| File analysis / code tools | claude          |
| Enterprise / Azure         | microsoft       |
| Prototyping / eval         | mini            |
| Maximum tool coverage      | claude          |
| Minimum setup              | mini            |

### Native Tools by SDK

| SDK       | Tools                                              |
| --------- | -------------------------------------------------- |
| claude    | bash, read_file, write_file, edit_file, glob, grep |
| copilot   | file_system, git, web_requests                     |
| microsoft | ai_function                                        |
| mini      | (none -- learning tools only)                      |

### Exercise

A teammate needs an agent that reviews GitHub PRs and posts comments. Which
SDK should they choose? Write the command.

**Expected**: Copilot, because it has built-in git and GitHub tools.
`amplihack new --file pr_reviewer.md --sdk copilot`

---

## 4. Multi-Agent Architecture

### Why Multi-Agent?

Single agents work well for focused tasks. Multi-agent setups are better when
you need specialization, coordination, or memory isolation.

### Enabling Multi-Agent

```bash
amplihack new --file goal.md --sdk copilot --multi-agent
```

### Generated Structure

```
goal_agents/<name>/
+-- main.py                # Entry point
+-- coordinator.yaml       # Coordinator config
+-- memory_agent.yaml      # Memory agent config
+-- sub_agents/
|   +-- researcher.yaml    # Research sub-agent
|   +-- writer.yaml        # Writing sub-agent
+-- shared_memory/         # Shared memory store
```

### How Coordination Works

1. User sends a request to the coordinator.
2. Coordinator decomposes the request into sub-tasks.
3. Each sub-task is dispatched to the appropriate sub-agent.
4. Sub-agents execute and return results.
5. Coordinator merges results and responds.

### Exercise

Write the CLI command for a multi-agent codebase analyzer using the Claude SDK.

**Expected**: `amplihack new --file codebase_analyzer.md --sdk claude --multi-agent`

---

## 5. Agent Spawning

### What Is Spawning?

Spawning allows the coordinator to create new sub-agents at runtime. Instead
of a fixed set, the system dynamically generates specialists.

### Enabling Spawning

```bash
amplihack new --file goal.md --sdk copilot --multi-agent --enable-spawning
```

`--enable-spawning` requires `--multi-agent`. If omitted, the CLI
automatically adds it.

### When to Use / Avoid

| Use When                                 | Avoid When                     |
| ---------------------------------------- | ------------------------------ |
| Dynamic domains, unpredictable sub-tasks | Fixed, known workflows         |
| Exploration and discovery                | Cost-sensitive environments    |
| Need to scale sub-agents for parallelism | Deterministic behaviour needed |

### Exercise

Write the command for a spawning-enabled research assistant using Claude.

**Expected**:

```bash
amplihack new --file research_assistant.md --sdk claude --multi-agent --enable-spawning
```

---

## 6. Running Evaluations

### The Progressive Test Suite

Run all 12 levels:

```bash
python -m amplihack.eval.progressive_test_suite \
    --agent-name my-agent \
    --output-dir eval_results/ \
    --sdk mini
```

Run specific levels:

```bash
python -m amplihack.eval.progressive_test_suite \
    --agent-name my-agent \
    --output-dir eval_results/ \
    --levels L1 L2 L3 \
    --sdk mini
```

### Output Format

The suite produces a JSON report:

```json
{
  "agent_name": "my-agent",
  "overall_score": 0.82,
  "level_scores": {
    "L1": 0.95,
    "L2": 0.8,
    "L3": 0.7
  },
  "pass_threshold": 0.7,
  "passed": true
}
```

- **overall_score**: Weighted average across all levels (0.0 to 1.0).
- **level_scores**: Score per level.
- **pass_threshold**: Default is 0.70.

### SDK Comparison

Compare SDKs head-to-head:

```bash
python -m amplihack.eval.sdk_eval_loop \
    --sdks mini claude copilot \
    --loops 3 \
    --levels L1 L2 L3
```

### Multi-Seed for Statistical Significance

```bash
python -m amplihack.eval.long_horizon_multi_seed \
    --seeds 3 \
    --agent-name my-agent
```

Use 3-run medians to smooth out LLM stochasticity.

### Exercise

Write the command to evaluate `security-scanner` on L1-L6 with the mini SDK.

**Expected**:

```bash
python -m amplihack.eval.progressive_test_suite \
    --agent-name security-scanner \
    --output-dir ./results/ \
    --levels L1 L2 L3 L4 L5 L6 \
    --sdk mini
```

---

## 7. Understanding Eval Levels

### Core Levels (L1-L6)

| Level | Name                   | What It Tests                         |
| ----- | ---------------------- | ------------------------------------- |
| L1    | Single Source Recall   | Direct fact retrieval from one source |
| L2    | Multi-Source Synthesis | Combining info from multiple articles |
| L3    | Temporal Reasoning     | Tracking changes over time            |
| L4    | Procedural Learning    | Learning step-by-step procedures      |
| L5    | Contradiction Handling | Detecting conflicting information     |
| L6    | Incremental Learning   | Updating knowledge with new info      |

### Advanced Levels (L7-L12)

| Level | Name                    | What It Tests                           |
| ----- | ----------------------- | --------------------------------------- |
| L7    | Knowledge Transfer      | Teaching another agent what was learned |
| L8    | Metacognition           | Knowing what it knows and does not know |
| L9    | Causal Reasoning        | Understanding why things happened       |
| L10   | Counterfactual          | Reasoning about "what if" scenarios     |
| L11   | Novel Skill Acquisition | Learning new skills from documentation  |
| L12   | Far Transfer            | Applying reasoning to a new domain      |

### Difficulty Progression

- **Foundation** (L1-L3): Recall, synthesis, temporal reasoning.
- **Application** (L4-L6): Procedures, conflicts, updates.
- **Higher-order** (L7-L9): Teaching, metacognition, causality.
- **Transfer** (L10-L12): Counterfactuals, novel skills, cross-domain.

### How Grading Works

The grader compares the agent's answer against the expected answer using
semantic similarity (LLM-based). Scores range from 0.0 to 1.0. Paraphrasing
is accepted -- exact wording is not required.

### Exercise

Your agent scores L1=0.90, L3=0.30. What does this tell you?

**Expected**: The agent is good at basic recall (L1) but poor at temporal
reasoning (L3). It stores facts but cannot track changes over time.

---

## 8. Self-Improvement Loop

### The Closed Loop

```
EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE
```

1. **EVAL**: Run L1-L12 for baseline scores.
2. **ANALYZE**: `ErrorAnalyzer` identifies failure patterns.
3. **RESEARCH**: Generate hypothesis, gather evidence, consider counter-arguments.
4. **IMPROVE**: Apply the best code change.
5. **RE-EVAL**: Run the same levels again.
6. **DECIDE**: Accept if improved with no regression; revert otherwise.

### Running the Loop

```bash
python -m amplihack.eval.self_improve.runner \
    --agent-name my-agent \
    --iterations 5 \
    --output-dir improve_results/ \
    --sdk mini
```

### Key Principles

- **Measure first, change second**: Never change without a baseline.
- **Every change has a hypothesis**: "L3 fails because temporal ordering is
  lost during retrieval."
- **Revert on regression**: If a change hurts other levels, revert it.
- **Log everything**: Every iteration is recorded for reproducibility.

### ErrorAnalyzer Output

```python
ErrorAnalysis(
    failure_mode="retrieval_miss",
    affected_level="L3",
    affected_component="memory_retrieval.py",
    proposed_change="Add timestamp-based sorting to retrieval"
)
```

### Example Iteration

```
Iteration 1:
  Baseline: L1=0.83, L2=0.67, L3=0.50
  Analysis: L3 fails because temporal ordering is lost
  Change: Add timestamp-based sorting to retrieval
  Post-change: L1=0.83, L2=0.70, L3=0.75
  Result: ACCEPT (+0.05 L2, +0.25 L3, no regression)
```

### Historical Results

A 5-loop cycle improved overall scores from 83.2% to 96.6% (+13.4%). The
biggest single win was source-specific fact filtering (+53.3% on L2).

### Exercise

An agent has baseline L1=0.90, L2=0.40. After a change, L1=0.70, L2=0.80.
Should you accept or revert?

**Expected**: REVERT. L1 regressed by -0.20. The loop requires no regression
on passing levels.

---

## 9. Security Domain Agents

### Creating a Security Agent

```markdown
# Goal: Security Vulnerability Analyzer

## Objective

Analyze codebases for common vulnerabilities (OWASP Top 10)
and generate remediation recommendations.

## Domain

security-analysis

## Constraints

- Must identify injection, XSS, CSRF, and auth issues
- Must provide severity ratings (Critical/High/Medium/Low)
- Must cite CWE numbers

## Success Criteria

- Identifies SQL injection in test code
- Provides correct CWE references
- Generates actionable remediation steps
```

```bash
amplihack new --file security_analyzer.md \
    --sdk claude --multi-agent --enable-memory
```

### Domain-Specific Eval

```bash
python -m amplihack.eval.domain_eval_harness \
    --domain security \
    --agent-name security-analyzer \
    --output-dir security_eval/
```

### Security Eval Dimensions

1. **Vulnerability detection**: Can it find known vulnerabilities?
2. **Classification accuracy**: Correct CWE numbers?
3. **Severity assessment**: Appropriate severity ratings?
4. **Remediation quality**: Actionable and correct fixes?

### Exercise

Write a prompt.md for an API security agent. Include all four sections.

---

## 10. Custom Eval Levels

### Why Custom Levels?

The built-in L1-L12 test general cognitive capabilities. Your domain may need
specialized evaluation (medical diagnosis, legal analysis, security, etc.).

### Anatomy of a Test Level

```python
from amplihack.eval.test_levels import TestLevel, TestArticle, TestQuestion

CUSTOM_LEVEL = TestLevel(
    level_id="CUSTOM-1",
    level_name="Domain-Specific Reasoning",
    description="Tests reasoning specific to your domain",
    articles=[
        TestArticle(
            title="Article Title",
            content="The content the agent must learn...",
            url="https://example.com/article",
            published="2026-02-20T10:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="What should the agent answer?",
            expected_answer="The reference answer for grading",
            level="CUSTOM-1",
            reasoning_type="domain_specific_reasoning",
        ),
    ],
)
```

### Step-by-Step

1. **Define articles**: Write or collect domain-specific content.
2. **Write questions**: Target the difficulty you need.
3. **Set expected answers**: Clear reference answers for the grader.
4. **Choose reasoning types**: Label each question's cognitive skill.
5. **Register the level**: Add to your eval configuration.
6. **Run and iterate**: Evaluate and refine.

### Tips

- One skill per question (do not mix temporal reasoning with synthesis).
- Clear expected answers (vague answers produce unreliable grades).
- At least 3 questions per level (for stable scores).
- Progressive difficulty (recall first, then synthesis, then reasoning).

### Exercise

Create a custom eval level for cooking recipe comprehension with at least one
article and two questions.

---

## Troubleshooting

### Common Issues

**`ImportError: No module named 'click'`**

The CLI requires click. Install it:

```bash
pip install click
```

**Agent generation fails with `ValueError: Raw prompt cannot be empty`**

Your prompt file is empty or missing the goal section. Ensure the file starts
with `# Goal: ...`.

**`--enable-spawning` warning**

The CLI automatically adds `--multi-agent` if you pass `--enable-spawning`
alone. This is a warning, not an error.

**Eval scores are inconsistent between runs**

LLM outputs are stochastic. Use 3-run medians:

```bash
python -m amplihack.eval.long_horizon_multi_seed --seeds 3 --agent-name my-agent
```

**Self-improvement loop applies a change then reverts it**

This is expected behaviour. The loop is conservative -- it reverts any change
that causes regression on previously passing levels.

**SDK eval loop times out**

Increase the timeout:

```bash
export AMPLIHACK_EVAL_TIMEOUT=900
```

**Mini SDK has no tools**

This is by design. Mini is for prototyping and eval. For real tool usage, use
`claude` or `copilot` SDK.

### Getting Help

- Architecture documentation: `docs/GOAL_SEEKING_AGENTS.md`
- Eval level definitions: `src/amplihack/eval/test_levels.py`
- Self-improvement loop: `src/amplihack/eval/self_improve/runner.py`
- CLI source: `src/amplihack/goal_agent_generator/cli.py`
- SDK adapters: `src/amplihack/agents/goal_seeking/sdk_adapters/`

---

## Reference

### CLI Options

```
amplihack new [OPTIONS]

Options:
  --file, -f PATH        Path to prompt.md (required)
  --output, -o PATH      Output directory (default: ./goal_agents)
  --name, -n TEXT         Custom agent name
  --skills-dir PATH      Custom skills directory
  --verbose, -v          Enable verbose output
  --enable-memory        Enable persistent memory
  --sdk [copilot|claude|microsoft|mini]  SDK backend (default: copilot)
  --multi-agent          Enable multi-agent architecture
  --enable-spawning      Enable dynamic sub-agent spawning
```

### Eval Commands

```bash
# Progressive test suite
python -m amplihack.eval.progressive_test_suite \
    --agent-name NAME --output-dir DIR [--levels L1 L2 ...] [--sdk SDK]

# SDK comparison loop
python -m amplihack.eval.sdk_eval_loop \
    --sdks SDK1 SDK2 ... --loops N [--levels L1 L2 ...]

# Multi-seed for statistics
python -m amplihack.eval.long_horizon_multi_seed \
    --seeds N --agent-name NAME

# Self-improvement loop
python -m amplihack.eval.self_improve.runner \
    --agent-name NAME --iterations N --output-dir DIR [--sdk SDK]

# Domain-specific eval
python -m amplihack.eval.domain_eval_harness \
    --domain DOMAIN --agent-name NAME --output-dir DIR
```

### Eval Level Summary

| Level | Name                    | Reasoning Type          |
| ----- | ----------------------- | ----------------------- |
| L1    | Single Source Recall    | direct_recall           |
| L2    | Multi-Source Synthesis  | cross_source_synthesis  |
| L3    | Temporal Reasoning      | temporal_difference     |
| L4    | Procedural Learning     | procedural_recall       |
| L5    | Contradiction Handling  | contradiction_detection |
| L6    | Incremental Learning    | incremental_update      |
| L7    | Knowledge Transfer      | knowledge_transfer      |
| L8    | Metacognition           | confidence_calibration  |
| L9    | Causal Reasoning        | causal_chain            |
| L10   | Counterfactual          | counterfactual_removal  |
| L11   | Novel Skill Acquisition | concept_discovery       |
| L12   | Far Transfer            | far_transfer_temporal   |

### Key Source Files

| Component           | Path                                                      |
| ------------------- | --------------------------------------------------------- |
| CLI                 | `src/amplihack/goal_agent_generator/cli.py`               |
| Models              | `src/amplihack/goal_agent_generator/models.py`            |
| Prompt Analyzer     | `src/amplihack/goal_agent_generator/prompt_analyzer.py`   |
| Objective Planner   | `src/amplihack/goal_agent_generator/objective_planner.py` |
| Skill Synthesizer   | `src/amplihack/goal_agent_generator/skill_synthesizer.py` |
| Agent Assembler     | `src/amplihack/goal_agent_generator/agent_assembler.py`   |
| Packager            | `src/amplihack/goal_agent_generator/packager.py`          |
| Test Levels         | `src/amplihack/eval/test_levels.py`                       |
| Progressive Suite   | `src/amplihack/eval/progressive_test_suite.py`            |
| Grader              | `src/amplihack/eval/grader.py`                            |
| Self-Improve Runner | `src/amplihack/eval/self_improve/runner.py`               |
| Error Analyzer      | `src/amplihack/eval/self_improve/error_analyzer.py`       |
| SDK Eval Loop       | `src/amplihack/eval/sdk_eval_loop.py`                     |
| Teaching Agent      | `src/amplihack/agents/teaching/generator_teacher.py`      |
