# Eval-Recipes Benchmarking Integration

Systematic benchmarking of amplihack framework against vanilla Claude Code and other CLI agents using Microsoft's eval-recipes framework.

## Quick Start (5 Minutes)

```bash
# 1. Configure API key (choose one method)
# Method A: Environment variable (recommended)
export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE

# Method B: .env file
echo "ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE" > .env

# 2. Run a benchmark
make benchmark TARGET=amplihack TASK=simple-task

# 3. Compare with vanilla Claude Code
make benchmark-compare TASK=simple-task

# 4. View results
cat .claude/runtime/benchmarks/latest/amplihack/simple-task/results.json
```

## Architecture

### Five Modular Bricks

1. **SecretsManager** - Load API key from env var, .env file, or custom file
2. **AgentConfig** - Parse three-file agent configurations
3. **DockerManager** - Container lifecycle with context manager
4. **BenchmarkRunner** - Orchestrate trials and aggregate results
5. **ResultsManager** - Multi-format output and comparison

### Three-File Agent Pattern

Each agent follows Microsoft's battle-tested pattern:

```
.claude/agents/eval-recipes/<agent-name>/
├── agent.yaml              # Environment variables
├── install.dockerfile      # Docker setup commands
└── command_template.txt    # Liquid template for execution
```

## Available Commands

### Run Single Benchmark

```bash
make benchmark TARGET=<agent> TASK=<task>

# Examples
make benchmark TARGET=amplihack TASK=simple-task
make benchmark TARGET=claude_code TASK=simple-task
```

### Compare Agents

```bash
make benchmark-compare TASK=<task>

# Runs both amplihack and claude_code, shows comparison
```

### List Tasks

```bash
make benchmark-list

# Shows all available eval-recipes tasks
```

### Clean Results

```bash
make benchmark-clean

# Removes all benchmark results
```

### Help

```bash
make benchmark-help

# Shows all benchmarking commands
```

## Configuration

### API Key Setup

The API key is loaded using standard priority:

1. **Environment Variable** (highest priority, recommended)
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
   ```

2. **.env File** (project-level configuration)
   ```bash
   echo "ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE" > .env
   ```

3. **Custom File** (optional, for advanced use cases)
   ```bash
   # Custom file path can be passed programmatically
   # Supports YAML and JSON formats
   # Must have 0o600 permissions (chmod 600)
   ```

**Formats Supported** (for custom files):
- Plain text: `sk-ant-...`
- YAML: `ANTHROPIC_API_KEY: sk-ant-...`
- JSON: `{"ANTHROPIC_API_KEY": "sk-ant-..."}`

### Adding New Agents

Create a new agent directory following the three-file pattern:

```bash
mkdir -p .claude/agents/eval-recipes/my-agent
cd .claude/agents/eval-recipes/my-agent

# 1. Create agent.yaml
cat > agent.yaml << 'EOF'
required_env_vars:
  - ANTHROPIC_API_KEY
EOF

# 2. Create install.dockerfile
cat > install.dockerfile << 'EOF'
RUN apt-get update && apt-get install -y my-tool
RUN my-tool --version
EOF

# 3. Create command_template.txt
cat > command_template.txt << 'EOF'
my-tool execute "{{task_instructions}}"
EOF
```

## Results Format

### Directory Structure

```
.claude/runtime/benchmarks/
├── 20251116_203000/              # Timestamp
│   ├── amplihack/
│   │   └── simple-task/
│   │       ├── results.json      # Structured results
│   │       ├── results.md        # Human-readable
│   │       ├── results.csv       # Spreadsheet format
│   │       ├── stdout.log
│   │       └── stderr.log
│   └── claude_code/
│       └── simple-task/
│           └── ...
└── latest -> 20251116_203000/    # Symlink to most recent
```

### JSON Results Schema

```json
{
  "agent_name": "amplihack",
  "task_name": "simple-task",
  "num_trials": 3,
  "mean_score": 85.5,
  "median_score": 87.0,
  "std_dev": 4.2,
  "min_score": 81.0,
  "max_score": 90.0,
  "perfect_trials": 0,
  "timestamp": "2025-11-16T20:30:00Z",
  "trials": [...]
}
```

## Troubleshooting

### API Key Not Found

**Error**: `FileNotFoundError: ANTHROPIC_API_KEY not found`

**Solution** (choose one):
```bash
# Option A: Set environment variable
export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE

# Option B: Create .env file
echo "ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE" > .env
```

### Docker Daemon Not Running

**Error**: `ConnectionError: Cannot connect to Docker daemon`

**Solution**:
```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
open -a Docker  # macOS
```

### Permission Denied on Custom Secrets File

**Error**: `PermissionError: Secrets file has insecure permissions`

**Solution**:
```bash
# Only applies to custom secrets files (not env var or .env)
chmod 600 /path/to/custom-secrets-file
```

### Agent Not Found

**Error**: `ValueError: Agent 'my-agent' not found`

**Solution**:
```bash
# List available agents
ls -1 .claude/agents/eval-recipes/

# Verify agent has all 3 required files
ls -1 .claude/agents/eval-recipes/my-agent/
# Should show: agent.yaml, install.dockerfile, command_template.txt
```

### Task Not Found

**Error**: `ValueError: Task 'my-task' not found`

**Solution**:
```bash
# List available tasks
make benchmark-list

# Or check tasks directory
ls -1 data/tasks/
```

## Security

### Secret Management

- **Load**: API key loaded from env var, .env, or custom file (in priority order)
- **Inject**: Passed to container via environment variables
- **Sanitize**: Secrets automatically redacted in logs before persistence

### File Permissions

The SecretsManager enforces secure permissions for custom files:
- **Required**: `chmod 600` (read/write owner only)
- **Detected**: World-readable custom files trigger error
- **Validated**: Permission check before loading custom files
- **Note**: Environment variables and .env files do not require permission validation

### Log Sanitization

All logs are automatically sanitized before saving:
- Secrets replaced with `[REDACTED]`
- Patterns: `sk-ant-*`, API keys, tokens
- Happens before file write (not manual)

## Performance

### Typical Benchmarks

- **Single trial**: 2-5 minutes (depends on task complexity)
- **Multi-trial (3x)**: 6-15 minutes
- **Full matrix (2 agents, 5 tasks)**: 20-50 minutes

### Docker Overhead

- **Image build**: ~30 seconds first time, cached after
- **Container start**: ~2-3 seconds
- **Container cleanup**: <1 second

### Optimization

- **Use caching**: Docker images cached between runs
- **Parallel execution**: Not yet supported (sequential only)
- **Task selection**: Run only necessary tasks

## Philosophy Compliance

### Ruthless Simplicity

- Five bricks, each with ONE responsibility
- Minimal configuration (three files per agent)
- No unnecessary abstractions

### Modular Design (Bricks & Studs)

- Each brick is self-contained
- Clear public interfaces (studs)
- Can be regenerated from specifications

### Zero-BS Implementation

- No stubs or placeholders
- Every function works or doesn't exist
- All 63 tests passing

## References

- **eval-recipes**: https://github.com/microsoft/eval-recipes
- **Investigation Session**: `.claude/runtime/logs/20251116_201452/`
- **Module Specifications**: `.claude/runtime/logs/20251117_module_specs/`
- **GitHub Issue**: #1382

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review investigation documentation in `.claude/runtime/logs/20251116_201452/`
3. Create GitHub issue with error details

---

🤖 Part of the amplihack agentic coding framework
