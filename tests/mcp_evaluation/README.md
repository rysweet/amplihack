## MCP Evaluation Framework

A generic, reusable framework for evaluating ANY MCP server integration with amplihack. Measures real value through controlled comparisons of baseline vs tool-enhanced coding workflows.

## Features

- **Generic Design**: Evaluate any MCP tool with minimal configuration
- **Real Measurements**: Actual execution data, not synthetic benchmarks
- **Comprehensive Metrics**: Quality, efficiency, and tool-specific measurements
- **Automated Reports**: Human-readable markdown reports with actionable recommendations
- **Extensible**: Easy to add new tools, scenarios, and metrics

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         Evaluation Framework (Generic)              │
│  ┌────────────┐  ┌──────────┐  ┌────────────────┐ │
│  │  Scenario  │→ │ Executor │→ │ Metrics        │ │
│  │  Runner    │  │          │  │ Collector      │ │
│  └────────────┘  └──────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────┘
         ↓              ↓               ↓
┌─────────────────────────────────────────────────────┐
│         Tool Adapters (Tool-Specific)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Serena  │  │ Copilot  │  │  Future Tool    │ │
│  │ Adapter  │  │ Adapter  │  │  Adapter        │ │
│  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install pyyaml requests

# Verify framework
cd tests/mcp_evaluation
python -c "from framework import MCPEvaluationFramework; print('Framework ready!')"
```

### Running Serena Evaluation

```python
from pathlib import Path
from tests.mcp_evaluation.framework import MCPEvaluationFramework
from tests.mcp_evaluation.tools import load_tool_config
from tests.mcp_evaluation.scenarios import get_all_scenarios

# Load Serena configuration
config = load_tool_config("serena")

# Create framework
framework = MCPEvaluationFramework(config)

# Get test scenarios
scenarios = get_all_scenarios()

# Run evaluation
report = framework.run_evaluation(scenarios)

# Save results
output_dir = Path("results/serena_2025_01_16")
output_dir.mkdir(parents=True, exist_ok=True)

report.save_json(output_dir / "report.json")

# Generate markdown report
from tests.mcp_evaluation.framework import ReportGenerator
generator = ReportGenerator(report)
generator.save(output_dir / "report.md")

print(f"Evaluation complete! Results saved to {output_dir}")
print(f"Recommendation: {report.recommendations[0]}")
```

## Test Scenarios

The framework includes three built-in test scenarios:

### 1. Cross-File Navigation

**Category**: NAVIGATION
**Test**: Find all implementations of the `Handler` interface across the codebase
**Evaluates**: Symbol navigation, text search accuracy, file traversal efficiency

### 2. Code Understanding

**Category**: ANALYSIS
**Test**: Analyze `DatabaseService` class dependencies and relationships
**Evaluates**: Dependency mapping, type information, relationship understanding

### 3. Targeted Modification

**Category**: MODIFICATION
**Test**: Add type hints to all `UserService` methods
**Evaluates**: Edit precision, context awareness, code correctness preservation

## Test Codebase

The framework includes a realistic Python microservice with:

- **16 Python files** organized in modules
- **4 Handler implementations** (HTTP, gRPC, WebSocket, Base)
- **3 Service classes** (UserService, AuthService, DatabaseService)
- **2 Data models** (User, Session)
- **Utility modules** (logger, config)

This provides realistic testing conditions for MCP tool evaluation.

## Metrics Collected

### Universal Metrics (Tool-Independent)

- **Quality**: Correctness score, test failures, requirements met
- **Efficiency**: Total tokens, wall clock time, file operations
- **Completeness**: Requirements fulfillment percentage

### Tool-Specific Metrics

- **Usage**: Features used, feature effectiveness
- **Performance**: Tool call latency, failure rate
- **Value**: Unique insights, estimated time savings

## Configuration

### Tool Configuration Format (YAML)

```yaml
tool_id: serena
tool_name: "Serena MCP Server"
version: "1.0.0"
description: "LSP-powered code intelligence"

capabilities:
  - id: symbol_navigation
    name: "Symbol Navigation"
    description: "Jump to definitions, find references"
    relevant_scenarios: [NAVIGATION, ANALYSIS]
    expected_improvement: both
    mcp_commands:
      - "serena/find_symbol"
      - "serena/goto_definition"

adapter_class: "SerenaToolAdapter"
setup_required: true
setup_instructions: |
  1. Install: npm install -g serena-mcp
  2. Start: serena-mcp start --port 8080
  3. Verify: curl http://localhost:8080/health

health_check_url: "http://localhost:8080/health"
environment_variables:
  SERENA_MCP_URL: "http://localhost:8080"
  SERENA_MCP_ENABLED: "1"

expected_advantages:
  NAVIGATION:
    - "Faster symbol location"
    - "No false positives"
  ANALYSIS:
    - "Accurate type information"
    - "Complete dependency graphs"

baseline_comparison_mode: "with_vs_without"
timeout_seconds: 30
fallback_behavior: baseline
```

## Adding a New MCP Tool

### Step 1: Create Configuration

Create `tools/your_tool_config.yaml` following the schema above.

### Step 2: Implement Adapter

```python
# tools/your_tool_adapter.py
from tests.mcp_evaluation.framework import ToolAdapter

class YourToolAdapter(ToolAdapter):
    def __init__(self, config):
        self.config = config

    def enable(self):
        # Set up tool for use
        pass

    def disable(self):
        # Disable tool (baseline mode)
        pass

    def is_available(self):
        # Check if tool is working
        return True

    def collect_tool_metrics(self):
        # Return tool-specific metrics
        pass

    def get_capabilities(self):
        return self.config.capabilities
```

### Step 3: Run Evaluation

```python
config = load_tool_config("your_tool")
framework = MCPEvaluationFramework(config)
report = framework.run_evaluation(get_all_scenarios())
```

That's it! The same scenarios work unchanged with any tool.

## Report Format

Reports include:

### Executive Summary

- Overall verdict (INTEGRATE / CONSIDER / DON'T INTEGRATE)
- Average performance improvement
- Average quality improvement
- Scenarios passed count

### Detailed Results

Per-scenario comparison tables with:

- Time delta (seconds and percentage)
- Token usage delta
- File operations delta
- Correctness improvement
- Tool-specific insights

### Capability Analysis

Per-capability assessment:

- Usage frequency
- Value rating (HIGH / MEDIUM / LOW)
- Expected vs actual improvement

### Recommendations

Actionable next steps based on results

## Philosophy Alignment

This framework follows amplihack principles:

- **Ruthless Simplicity**: Core framework < 500 lines
- **Brick Design**: Each component is self-contained and regeneratable
- **Zero-BS**: No stubs or placeholders, only working code
- **Measurement-Driven**: Real execution data drives decisions

## Directory Structure

```
tests/mcp_evaluation/
├── framework/                  # Core framework (generic)
│   ├── __init__.py
│   ├── types.py               # Data types and enums
│   ├── adapter.py             # ToolAdapter interface
│   ├── metrics.py             # Metrics collection
│   ├── evaluator.py           # Main orchestration
│   └── reporter.py            # Report generation
│
├── tools/                     # Tool adapters (tool-specific)
│   ├── __init__.py
│   ├── serena_config.yaml    # Serena configuration
│   └── serena_adapter.py     # Serena adapter
│
├── scenarios/                 # Test scenarios
│   ├── __init__.py
│   ├── scenario_1_navigation.py
│   ├── scenario_2_analysis.py
│   ├── scenario_3_modification.py
│   └── test_codebases/       # Realistic test code
│       └── microservice_project/
│
├── results/                   # Evaluation results
│   └── serena_2025_01_16/
│       ├── report.json
│       └── report.md
│
├── README.md                  # This file
└── run_evaluation.py          # Example usage script
```

## Requirements

- Python 3.10+
- PyYAML (for configuration loading)
- Requests (for health checks)
- Optional: MCP tool server (Serena, etc.)

## Success Criteria

Framework is successful if:

1. **Serena evaluation completes** - All scenarios run baseline and enhanced
2. **Results are actionable** - Clear integrate/don't-integrate recommendation
3. **Reusable without redesign** - Adding new tools requires only:
   - New config file
   - New adapter implementation
   - Same scenarios work unchanged
4. **Simple core maintained** - Core framework stays < 500 lines
5. **Reports are readable** - Stakeholders understand findings

## Next Steps

1. Run Serena evaluation
2. Analyze results
3. Make integration decision
4. Add more MCP tools (GitHub Copilot, etc.)
5. Create additional scenarios as needed

## Support

For questions or issues:

- Review architecture documentation in `Specs/MCP_EVALUATION_*.md`
- Check tool configuration schema
- Examine example scenarios for patterns

---

**Status**: Framework Implemented
**Version**: 1.0.0
**Next**: Run Serena evaluation
