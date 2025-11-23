# MCP Evaluation Framework - Quick Start Guide

## 5-Minute Quick Start

### 1. Verify Installation

```bash
cd tests/mcp_evaluation
python test_framework.py
```

Expected output: `6 passed, 0 failed`

### 2. Run Mock Evaluation

```bash
python run_evaluation.py
```

This runs the full evaluation with mock adapters (no MCP server required).

### 3. View Results

```bash
ls -la results/serena_*/
cat results/serena_*/report.md
```

## Real Serena Evaluation

### Prerequisites

1. **Install Serena MCP Server**:

   ```bash
   npm install -g serena-mcp
   ```

2. **Start Server**:

   ```bash
   serena-mcp start --port 8080
   ```

3. **Verify Health**:
   ```bash
   curl http://localhost:8080/health
   ```

### Run Evaluation

```bash
python run_evaluation.py
```

The framework will:

- Load Serena configuration
- Check server health
- Run 3 scenarios in baseline and enhanced mode
- Generate comparison reports
- Save results to `results/serena_TIMESTAMP/`

## Understanding Results

### Report Structure

```markdown
# MCP Tool Evaluation Report

## Executive Summary

- Overall verdict: INTEGRATE / CONSIDER / DON'T INTEGRATE
- Performance: +42% faster on average
- Quality: +15% more accurate

## Detailed Results

- Per-scenario comparison tables
- Token usage, time, file operations
- Correctness improvements

## Capability Analysis

- Which features were used
- How effective they were
- VALUE rating: HIGH / MEDIUM / LOW

## Recommendations

- Actionable next steps
- Integration recommendations
```

### Interpreting Recommendations

**INTEGRATE**: Clear value demonstrated

- Significant time savings (>40%)
- OR improved quality (>15%)
- AND no major drawbacks

**CONSIDER**: Mixed results

- Some scenarios benefit
- But not consistent across all tests
- Evaluate specific use cases

**DON'T INTEGRATE**: No clear advantage

- No significant speed improvement
- No quality improvement
- Not worth setup complexity

## Adding a New Tool

### Step 1: Create Configuration

Create `tools/my_tool_config.yaml`:

```yaml
tool_id: my_tool
tool_name: "My MCP Tool"
version: "1.0.0"
description: "Brief description"

capabilities:
  - id: my_capability
    name: "My Capability"
    description: "What it does"
    relevant_scenarios: [NAVIGATION]
    expected_improvement: faster
    mcp_commands: ["my_tool/command"]

adapter_class: "MyToolAdapter"
setup_required: true
setup_instructions: "How to set up"

health_check_url: "http://localhost:8081/health"

expected_advantages:
  NAVIGATION:
    - "Expected benefit 1"

baseline_comparison_mode: "with_vs_without"
```

### Step 2: Create Adapter

Create `tools/my_tool_adapter.py`:

```python
from tests.mcp_evaluation.framework import ToolAdapter

class MyToolAdapter(ToolAdapter):
    def __init__(self, config):
        self.config = config

    def enable(self):
        # Enable tool
        pass

    def disable(self):
        # Disable tool
        pass

    def is_available(self):
        # Check health
        return True

    def collect_tool_metrics(self):
        # Collect metrics
        pass

    def get_capabilities(self):
        return self.config.capabilities
```

### Step 3: Run Evaluation

```python
from tests.mcp_evaluation.tools import load_tool_config
from tests.mcp_evaluation.framework import MCPEvaluationFramework
from tests.mcp_evaluation.scenarios import get_all_scenarios

config = load_tool_config("my_tool")
framework = MCPEvaluationFramework(config)
report = framework.run_evaluation(get_all_scenarios())
```

## Common Issues

### Issue: "Configuration not found"

**Solution**: Check that config file exists in `tools/` directory with correct naming: `{tool_name}_config.yaml`

### Issue: "Health check failed"

**Solution**: Verify MCP server is running and accessible at configured URL

### Issue: "Adapter not found"

**Solution**: Ensure adapter class name in config matches actual class in adapter file

### Issue: "Import errors"

**Solution**: Run from project root or add to PYTHONPATH

## Framework Architecture

```
MCPEvaluationFramework
    ↓
load_tool_config("serena")
    ↓
SerenaToolAdapter
    ↓
run_evaluation(scenarios)
    ↓
For each scenario:
    - Run baseline (tool disabled)
    - Run enhanced (tool enabled)
    - Compare results
    - Calculate deltas
    ↓
Generate report
    ↓
Save to results/
```

## Key Files

- **Framework**: `framework/*.py` - Core evaluation logic
- **Adapters**: `tools/*_adapter.py` - Tool integrations
- **Configs**: `tools/*_config.yaml` - Tool configurations
- **Scenarios**: `scenarios/scenario_*.py` - Test scenarios
- **Test Code**: `scenarios/test_codebases/` - Realistic test code

## Next Steps

1. **Run mock evaluation** to understand the framework
2. **Set up Serena** following instructions in config
3. **Run real evaluation** and analyze results
4. **Make decision** based on report recommendations
5. **Add more tools** using the same pattern

## Support

- **Full Documentation**: See `README.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Architecture Specs**: See `Specs/MCP_EVALUATION_*.md`
- **Tests**: Run `python test_framework.py`

---

**Framework Version**: 1.0.0
**Status**: Production Ready
**Test Coverage**: 6/6 passing
