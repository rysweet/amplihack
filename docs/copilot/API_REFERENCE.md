# API Reference: Copilot CLI with amplihack

Complete reference for all CLI commands, Python APIs, and MCP server tools.

## Table of Contents

- [CLI Commands](#cli-commands)
- [Python API](#python-api)
- [Agent Reference](#agent-reference)
- [Pattern Reference](#pattern-reference)
- [MCP Server Tools](#mcp-server-tools)

## CLI Commands

### amplihack

Main CLI entry point.

#### amplihack launch

Launch Claude Code with amplihack configuration.

```bash
amplihack launch [OPTIONS]
```

**Options:**

- `--with-proxy-config FILE` - Load proxy configuration from file
- `--checkout-repo OWNER/REPO` - Clone and work in GitHub repository
- `--no-ultrathink` - Disable automatic ultrathink wrapping
- `--profile NAME` - Use specific profile configuration

**Examples:**

```bash
# Basic launch
amplihack launch

# With Azure OpenAI
amplihack launch --with-proxy-config ./azure.env

# Work in GitHub repo
amplihack launch --checkout-repo rysweet/amplihack

# Use specific profile
amplihack launch --profile production
```

#### amplihack copilot

Launch GitHub Copilot CLI with amplihack context.

```bash
amplihack copilot [ARGS]
```

**Arguments:**

- `ARGS` - Additional arguments passed to Copilot CLI

**Examples:**

```bash
# Basic launch
amplihack copilot

# With specific directory
amplihack copilot --add-dir /path/to/project

# Pass through Copilot args
amplihack copilot --model gpt-4
```

**What it does:**

1. Checks if Copilot CLI installed (installs if missing)
2. Sets up full filesystem access (`--allow-all-tools --add-dir /`)
3. Launches with amplihack context available

#### amplihack init

Initialize amplihack in current project.

```bash
amplihack init [OPTIONS]
```

**Options:**

- `--force` - Overwrite existing files

**Examples:**

```bash
# Initialize project
cd /path/to/project
amplihack init

# Force reinitialize
amplihack init --force
```

**Creates:**

```
.claude/
├── context/
│   ├── PHILOSOPHY.md
│   ├── PATTERNS.md
│   ├── PROJECT.md
│   ├── TRUST.md
│   ├── USER_PREFERENCES.md
│   └── USER_REQUIREMENT_PRIORITY.md
├── agents/amplihack/
│   ├── core/
│   └── specialized/
├── scenarios/
├── workflow/
│   └── DEFAULT_WORKFLOW.md
└── tools/

.github/
└── copilot-instructions.md
```

#### amplihack convert-agents

Convert Claude agents to Copilot format.

```bash
amplihack convert-agents [OPTIONS]
```

**Options:**

- `--source-dir PATH` - Source directory (default: `.claude/agents`)
- `--target-dir PATH` - Target directory (default: `.github/agents`)
- `--force` - Overwrite existing agents
- `--dry-run` - Show what would be converted without converting

**Examples:**

```bash
# Convert agents
amplihack convert-agents

# Force overwrite
amplihack convert-agents --force

# Dry run to preview
amplihack convert-agents --dry-run

# Custom directories
amplihack convert-agents --source-dir ./my-agents --target-dir ./copilot-agents
```

**Output:**

```
Converting agents...
✓ core/architect.md
✓ core/builder.md
✓ core/reviewer.md
[...]
✓ specialized/security.md
✓ specialized/database.md

Conversion complete:
  Total: 37
  Succeeded: 37
  Failed: 0
  Skipped: 0

Registry written to: .github/agents/REGISTRY.json
```

#### amplihack analyze

Analyze codebase for complexity and philosophy compliance.

```bash
amplihack analyze [TARGET] [OPTIONS]
```

**Arguments:**

- `TARGET` - Directory or file to analyze

**Options:**

- `--format {text|json|markdown}` - Output format (default: text)
- `--depth {quick|standard|deep}` - Analysis depth (default: standard)
- `--check-philosophy` - Check philosophy compliance
- `--output FILE` - Write results to file

**Examples:**

```bash
# Analyze directory
amplihack analyze ./src

# Deep analysis with JSON output
amplihack analyze ./src --depth deep --format json

# Check philosophy compliance
amplihack analyze ./src --check-philosophy

# Save results to file
amplihack analyze ./src --output analysis.json --format json
```

**Output:**

```
Analyzing: ./src

Complexity Analysis:
  Total files: 47
  Total lines: 3,421
  Average complexity: 8.3
  High complexity files: 3

Philosophy Compliance:
  ✓ Module structure: 94%
  ✓ Zero-BS implementation: 98%
  ✗ Pattern usage: 67%

Recommendations:
  - Simplify function calculate_metrics() (complexity: 23)
  - Extract class validation logic to separate module
  - Apply Safe Subprocess Wrapper pattern in 3 locations
```

#### amplihack mcp

Manage MCP server configurations.

```bash
amplihack mcp COMMAND [OPTIONS]
```

**Commands:**

- `list` - List configured MCP servers
- `add SERVER CONFIG` - Add MCP server
- `remove SERVER` - Remove MCP server
- `test SERVER` - Test MCP server connection

**Examples:**

```bash
# List servers
amplihack mcp list

# Add server
amplihack mcp add filesystem --command npx --args "-y @modelcontextprotocol/server-filesystem"

# Test server
amplihack mcp test filesystem

# Remove server
amplihack mcp remove filesystem
```

#### amplihack new

Generate goal-seeking agent from natural language prompt.

```bash
amplihack new "DESCRIPTION"
```

**Arguments:**

- `DESCRIPTION` - Natural language description of agent purpose

**Examples:**

```bash
# Create deployment agent
amplihack new "Create automated deployment agent for Kubernetes"

# Create testing agent
amplihack new "Generate comprehensive test agent for REST APIs"

# Create security agent
amplihack new "Security audit agent for web applications"
```

**Output:**

Agent created at: `.claude/agents/amplihack/specialized/deployment-automation.md`

#### amplihack --version

Show version information.

```bash
amplihack --version
```

**Output:**

```
amplihack version 0.9.0
```

## Python API

### analyze_codebase

Programmatic code analysis.

```python
from amplihack.scenarios.analyze_codebase import analyze

results = analyze(
    target="./src",
    depth="standard",
    check_philosophy=True
)
```

**Parameters:**

- `target` (str): Path to analyze
- `depth` (str): Analysis depth - "quick", "standard", or "deep"
- `check_philosophy` (bool): Check philosophy compliance

**Returns:**

```python
{
    "complexity": {
        "total_files": int,
        "total_lines": int,
        "average_complexity": float,
        "high_complexity_files": List[str]
    },
    "philosophy_compliance": {
        "module_structure": float,
        "zero_bs": float,
        "pattern_usage": float
    },
    "recommendations": List[str]
}
```

### convert_agents

Programmatic agent conversion.

```python
from amplihack.adapters.copilot_agent_converter import convert_agents

report = convert_agents(
    source_dir=Path(".claude/agents"),
    target_dir=Path(".github/agents"),
    force=True
)
```

**Parameters:**

- `source_dir` (Path): Source directory with Claude agents
- `target_dir` (Path): Target directory for Copilot agents
- `force` (bool): Overwrite existing files

**Returns:**

```python
ConversionReport(
    total=37,
    succeeded=37,
    failed=0,
    skipped=0,
    conversions=[...],
    errors=[]
)
```

### validate_agent

Validate agent structure.

```python
from amplihack.adapters.copilot_agent_converter import validate_agent

error = validate_agent(Path(".claude/agents/core/architect.md"))

if error:
    print(f"Validation error: {error}")
else:
    print("Agent valid")
```

**Parameters:**

- `agent_path` (Path): Path to agent file

**Returns:**

- `None` if valid
- `str` error message if invalid

### is_agents_synced

Check if agents are in sync.

```python
from amplihack.adapters.copilot_agent_converter import is_agents_synced

if not is_agents_synced():
    print("Agents out of sync - run amplihack convert-agents")
else:
    print("Agents synchronized")
```

**Parameters:**

- `source_dir` (Path): Source directory (default: `.claude/agents`)
- `target_dir` (Path): Target directory (default: `.github/agents`)

**Returns:**

- `True` if in sync
- `False` if outdated or never synced

### launch_copilot

Programmatic Copilot launch.

```python
from amplihack.launcher.copilot import launch_copilot

exit_code = launch_copilot(
    args=["--add-dir", "/path/to/project"],
    interactive=True
)
```

**Parameters:**

- `args` (List[str]): Arguments to pass to Copilot CLI
- `interactive` (bool): Use interactive mode

**Returns:**

- `int`: Exit code

## Agent Reference

### Core Agents

#### @architect

Design systems and decompose problems.

**Invocation:**

```
> @architect: Design authentication module with JWT support
```

**Capabilities:**

- System architecture design
- Problem decomposition
- Module specification
- Interface design
- Dependency analysis

**Output:**

- Module specification
- Public API definition
- Dependencies list
- Test requirements

#### @builder

Implement code from specifications.

**Invocation:**

```
> @builder: Implement the authentication module from architect's spec
```

**Capabilities:**

- Code generation from specs
- Zero-BS implementation
- Brick philosophy compliance
- Pattern application

**Output:**

- Complete working implementation
- No stubs or placeholders
- Clear public API
- Internal documentation

#### @reviewer

Review code for philosophy compliance.

**Invocation:**

```
> @reviewer: Review this PR for amplihack philosophy compliance
```

**Capabilities:**

- Philosophy compliance checking
- Pattern verification
- Code quality assessment
- Best practices validation

**Output:**

- Compliance report
- Violations identified
- Recommendations
- Refactoring suggestions

#### @tester

Generate tests following TDD pyramid.

**Invocation:**

```
> @tester: Generate tests for the authentication module
```

**Capabilities:**

- Test suite generation
- TDD pyramid compliance (60/30/10)
- Edge case identification
- Test data generation

**Output:**

- Unit tests (60%)
- Integration tests (30%)
- E2E tests (10%)
- Test fixtures

#### @api-designer

Design APIs and contracts.

**Invocation:**

```
> @api-designer: Design REST API for user management
```

**Capabilities:**

- API endpoint design
- Request/response modeling
- Error handling strategy
- Authentication flow design

**Output:**

- Endpoint specifications
- Data models
- Error codes
- Authentication requirements

#### @optimizer

Analyze performance and bottlenecks.

**Invocation:**

```
> @optimizer: Analyze performance of the search function
```

**Capabilities:**

- Performance profiling
- Bottleneck identification
- Optimization recommendations
- Trade-off analysis

**Output:**

- Performance metrics
- Bottleneck locations
- Optimization strategies
- Expected improvements

### Specialized Agents

#### @security

Security audit and vulnerability assessment.

**Invocation:**

```
> @security: Audit this authentication module for vulnerabilities
```

**Capabilities:**

- Vulnerability scanning
- Security best practices
- Threat modeling
- Remediation recommendations

#### @database

Database design and query optimization.

**Invocation:**

```
> @database: Design schema for multi-tenant application
```

**Capabilities:**

- Schema design
- Index optimization
- Query performance
- Migration planning

#### @cleanup

Code simplification and refactoring.

**Invocation:**

```
> @cleanup: Simplify this complex function
```

**Capabilities:**

- Complexity reduction
- Dead code removal
- Extract functions
- Improve readability

#### @patterns

Identify and apply reusable patterns.

**Invocation:**

```
> @patterns: Identify patterns in this error handling code
```

**Capabilities:**

- Pattern recognition
- Pattern recommendation
- Anti-pattern detection
- Refactoring to patterns

#### @integration

External service integration design.

**Invocation:**

```
> @integration: Design integration with Stripe payment API
```

**Capabilities:**

- Integration architecture
- Error handling strategy
- Retry logic
- Testing approach

#### @analyzer

Deep code analysis and understanding.

**Invocation:**

```
> @analyzer: Analyze this legacy codebase structure
```

**Capabilities:**

- Code structure analysis
- Dependency mapping
- Technical debt assessment
- Refactoring recommendations

#### @ambiguity

Clarify ambiguous requirements.

**Invocation:**

```
> @ambiguity: "We need better performance"
```

**Capabilities:**

- Requirement clarification
- Assumption identification
- Constraint discovery
- Goal specification

#### @fix-agent

Rapid resolution of common errors.

**Invocation:**

```
> @fix-agent: Fix this import error
```

**Modes:**

- QUICK: Template-based fix (< 5 min)
- DIAGNOSTIC: Root cause analysis
- COMPREHENSIVE: Full workflow

**Patterns:** import, ci, test, config, quality, logic

For complete agent list (37+ agents), see `.github/agents/REGISTRY.json`.

## Pattern Reference

### Foundational Patterns (14)

#### Bricks & Studs Module Design

Self-contained modules with clear public API.

```python
# module/__init__.py
from .core import primary_function
from .models import DataModel

__all__ = ['primary_function', 'DataModel']
```

#### Zero-BS Implementation

Every function works or doesn't exist.

```python
# ✓ Working implementation
def process(data, output="results.json"):
    result = {"processed": data}
    Path(output).write_text(json.dumps(result))
    return result

# ✗ Stub implementation
def process(data):
    # TODO: Implement
    raise NotImplementedError()
```

#### API Validation Before Implementation

Validate APIs before coding.

```python
# 1. Check official docs
# 2. Verify model names
# 3. Test minimal example
# 4. Then implement

model = "claude-3-sonnet-20241022"  # ✓ Verified
if model not in VALID_MODELS:
    raise ValueError(f"Invalid model: {model}")
```

#### Safe Subprocess Wrapper

Comprehensive error handling for subprocesses.

```python
def safe_subprocess_call(cmd, context, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}\nContext: {context}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out: {cmd[0]}\nContext: {context}"
```

#### Fail-Fast Prerequisite Checking

Check prerequisites at startup.

```python
class PrerequisiteChecker:
    REQUIRED_TOOLS = {"node": "--version", "npm": "--version"}

    def check_and_report(self):
        result = self.check_all_prerequisites()
        if not result.all_available:
            print(self.format_missing(result.missing))
            return False
        return True
```

For complete pattern library, see `.claude/context/PATTERNS.md`.

## MCP Server Tools

### Available MCP Servers

amplihack integrates with Model Context Protocol servers.

#### filesystem

File system operations.

**Configuration:**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
```

**Tools:**

- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write file
- `list_directory(path)` - List directory contents
- `create_directory(path)` - Create directory

#### git

Git operations.

**Configuration:**

```json
{
  "mcpServers": {
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git"]
    }
  }
}
```

**Tools:**

- `git_status()` - Get repository status
- `git_commit(message)` - Create commit
- `git_branch(name)` - Create branch
- `git_push()` - Push changes

#### docker

Docker container management.

**Configuration:**

```json
{
  "mcpServers": {
    "docker": {
      "command": "docker-mcp",
      "args": []
    }
  }
}
```

**Tools:**

- `list_containers()` - List all containers
- `create_container(image)` - Create container
- `get_logs(container)` - Get container logs
- `deploy_compose(yaml)` - Deploy compose stack

### Managing MCP Servers

```bash
# List configured servers
amplihack mcp list

# Add server
amplihack mcp add SERVER --command CMD --args "ARG1 ARG2"

# Test server
amplihack mcp test SERVER

# Remove server
amplihack mcp remove SERVER
```

### Using MCP Tools in Copilot

```
> Use MCP file system tools to read config.json
> Use MCP git tools to create feature branch
> Use MCP docker tools to start database container
```

**Note:** MCP support in Copilot CLI is limited compared to Claude Code.

## Exit Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 0    | Success                           |
| 1    | General error                     |
| 2    | Invalid arguments                 |
| 124  | Command timeout                   |
| 127  | Command not found                 |
| 130  | Interrupted by user (Ctrl+C)      |

## Environment Variables

| Variable                    | Description                    | Default        |
| --------------------------- | ------------------------------ | -------------- |
| `AMPLIHACK_CONFIG_DIR`      | Configuration directory        | `.claude/`     |
| `AMPLIHACK_AGENTS_DIR`      | Agents directory               | `.claude/agents/` |
| `AMPLIHACK_LOG_LEVEL`       | Logging level                  | `INFO`         |
| `ANTHROPIC_API_KEY`         | Anthropic API key              | None           |
| `GITHUB_TOKEN`              | GitHub API token               | None           |

## See Also

- [Getting Started Guide](./GETTING_STARTED.md)
- [Complete User Guide](./USER_GUIDE.md)
- [Migration Guide](./MIGRATION_FROM_CLAUDE.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [FAQ](./FAQ.md)
