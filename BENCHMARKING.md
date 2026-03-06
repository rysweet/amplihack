# Benchmarking amplihack with eval-recipes

Complete guide for running Microsoft's eval-recipes benchmarks to measure amplihack performance.

## Quick Start

```bash
# 1. Clone eval-recipes
git clone https://github.com/microsoft/eval-recipes.git ~/eval-recipes
cd ~/eval-recipes

# 2. Copy our agent configs
cp -r /path/to/amplihack/.claude/agents/eval-recipes/* data/agents/

# 3. Set API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Run benchmark
uv run scripts/run_benchmarks.py \
  --agent-filter "name=amplihack" \
  --task-filter "name=linkedin_drafting" \
  --num-trials 1
```

## Available Agents

### amplihack

Baseline amplihack with full context and workflow orchestration.

### claude_code

Vanilla Claude Code for baseline comparison.

### amplihack_pr1443_v2

amplihack with task classification fix (proven +36.5 point improvement on LinkedIn task).

## Common Tasks

```bash
# LinkedIn drafting (complex tool creation)
--task-filter "name=linkedin_drafting"

# Email drafting (CLI tool creation)
--task-filter "name=email_drafting"

# Multiple tasks
--task-filter "name=linkedin_drafting,email_drafting"
```

## Command Reference

### Basic Run

```bash
uv run scripts/run_benchmarks.py \
  --agent-filter "name=AGENT_NAME" \
  --task-filter "name=TASK_NAME" \
  --num-trials 1
```

### With Reports

```bash
uv run scripts/run_benchmarks.py \
  --agent-filter "name=amplihack" \
  --task-filter "name=linkedin_drafting" \
  --num-trials 3 \
  --generate-reports
```

### Compare Multiple Agents

```bash
uv run scripts/run_benchmarks.py \
  --agent-filter "name=amplihack,claude_code" \
  --task-filter "name=linkedin_drafting" \
  --num-trials 1
```

## Results Location

Results saved to: `~/eval-recipes/.benchmark_results/YYYY-MM-DD_HH-MM-SS/`

```bash
# Find latest score
find .benchmark_results -name "score.txt" -newer /tmp/test_start -exec cat {} \;

# View failure report
find .benchmark_results -name "FAILURE_REPORT*.md" | tail -1 | xargs less

# View HTML report
open .benchmark_results/latest/benchmark_report.html
```

## Testing a PR Branch

To test a specific PR branch:

1. Create new agent config in `~/eval-recipes/data/agents/amplihack_prXXXX/`
2. Update `install.dockerfile`:
   ```dockerfile
   RUN git clone -b BRANCH_NAME --single-branch --depth 1 \
       https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git /tmp/amplihack && \
       mkdir -p /project/.claude && \
       cp -r /tmp/amplihack/.claude/* /project/.claude/ && \
       cp /tmp/amplihack/CLAUDE.md /project/ && \
       rm -rf /tmp/amplihack
   ```
3. Run: `uv run scripts/run_benchmarks.py --agent-filter "name=amplihack_prXXXX" --task-filter "name=TASK"`

## Proven Results

**PR #1443 Validation** (2025-11-19):

- **Baseline (main):** 6.5/100 (created skill instead of tool)
- **With fix (PR #1443 V2):** 43.0/100 (created executable tool)
- **Improvement:** +36.5 points proven via actual benchmark

## Timing Expectations

- Docker build: ~60 seconds
- Task execution: 5-15 minutes
- Test scoring: 8-12 minutes
- **Total:** 15-25 minutes per task

## Troubleshooting

**"command not found: amplihack"**

- Agent config uses wrong command template
- Should use: `IS_SANDBOX=1 claude -p "{{task_instructions}}"` not `amplihack claude`

**Import errors in generated code**

- This is expected - eval tests both architecture and execution
- Architecture scores (30%) award partial credit for good design
- Execution scores (70%) require working code

**Docker build fails**

- Check Dockerfile syntax matches base.dockerfile patterns
- Don't add `RUN apt-get install` (causes errors)
- Use existing Claude Code from base image

## References

- **eval-recipes:** https://github.com/microsoft/eval-recipes
- **Agent configs:** `~/.amplihack/.claude/agents/eval-recipes/` in amplihack repo
- **Issue #1435:** Task classification improvement
- **Validation results:** See benchmark_results/ directories
