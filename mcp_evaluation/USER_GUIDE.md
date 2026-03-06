# MCP Evaluation Framework - User Guide

This is your complete guide to evaluating MCP tools with the framework. Follow these steps and you'll have actionable data to guide your integration decisions.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Evaluation Workflow Overview](#evaluation-workflow-overview)
4. [Phase 1: Setup](#phase-1-setup)
5. [Phase 2: Understanding the Framework](#phase-2-understanding-the-framework)
6. [Phase 3: Running Your First Evaluation](#phase-3-running-your-first-evaluation)
7. [Phase 4: Analyzing Results](#phase-4-analyzing-results)
8. [Phase 5: Making Decisions](#phase-5-making-decisions)
9. [Real MCP Tool Evaluation](#real-mcp-tool-evaluation)
10. [Common Workflows](#common-workflows)
11. [Troubleshooting](#troubleshooting)
12. [Next Steps](#next-steps)

## Introduction

### What This Guide Covers

This guide walks you through the complete journey of evaluating MCP tools:

- Setting up the framework
- Running your first mock evaluation
- Understanding the results
- Making integration decisions
- Evaluating real MCP tools

**Time Investment:**

- First-time setup: 15 minutes
- Mock evaluation: 5 minutes
- Result analysis: 15 minutes
- Real tool evaluation: 30-60 minutes

### Prerequisites

Before you start, ensure you have:

**Required:**

- Python 3.10 or higher
- Basic command line familiarity
- Access to the amplihack repository

**Optional (for real evaluations):**

- MCP server installed and configured
- Tool-specific dependencies
- Test environment for tool operations

**Installation Check:**

```bash
# Check Python version
python --version  # Should be 3.10+

# Navigate to the repository root
cd /path/to/MicrosoftHackathon2025-AgenticCoding

# Verify framework files exist
ls tests/mcp_evaluation/
# Should show: test_framework.py, run_evaluation.py, adapters/, etc.
```

## Evaluation Workflow Overview

The evaluation process follows 5 phases:

```
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATION WORKFLOW                       │
└─────────────────────────────────────────────────────────────┘

Phase 1: SETUP
├── Install dependencies
├── Verify framework works
└── Understand directory structure

Phase 2: UNDERSTANDING
├── Learn test scenarios
├── Understand comparison approach
└── Review metric definitions

Phase 3: RUNNING
├── Execute mock evaluation
├── Monitor progress
└── Verify output generation

Phase 4: ANALYZING
├── Read executive summary
├── Review metrics tables
└── Understand capability analysis

Phase 5: DECIDING
├── Apply decision criteria
├── Document recommendation
└── Plan next steps (integrate/reconsider/reject)
```

Each phase builds on the previous one. You can pause between phases.

## Phase 1: Setup

### Step 1.1: Clone and Navigate

```bash
# Clone the repository (if not already done)
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding

# Navigate to evaluation tests
cd tests/mcp_evaluation
```

### Step 1.2: Install Dependencies

```bash
# Install required Python packages
pip install pytest pytest-asyncio

# Install amplihack in development mode (from repo root)
cd ../..
pip install -e .

# Return to evaluation directory
cd tests/mcp_evaluation
```

### Step 1.3: Verify Framework Works

Run the framework's self-tests:

```bash
# Run all framework tests
python test_framework.py

# Expected output:
# ✓ Test scenarios load correctly
# ✓ Adapter interface works
# ✓ Mock adapter functions properly
# ✓ Metrics collection works
# ✓ Report generation succeeds
# ✓ End-to-end evaluation completes
#
# 6/6 tests passed
```

**If tests fail**, see the [Troubleshooting](#troubleshooting) section.

### Step 1.4: Understand Directory Structure

```
tests/mcp_evaluation/
├── test_framework.py          # Framework tests (run these first)
├── run_evaluation.py           # Main evaluation script
├── framework/
│   ├── __init__.py
│   ├── core.py                 # Core evaluation logic
│   ├── scenarios.py            # Test scenario definitions
│   └── metrics.py              # Metrics collection
├── adapters/
│   ├── base_adapter.py         # Adapter interface
│   └── serena_adapter.py       # Serena filesystem adapter
└── results/
    └── serena_mock_YYYYMMDD_HHMMSS/  # Generated reports (timestamped)
        ├── report.md           # Main evaluation report
        └── raw_metrics.json    # Detailed metrics data
```

## Phase 2: Understanding the Framework

### What Gets Evaluated

The framework tests tools through **3 realistic scenarios**:

#### 1. Navigation Scenario

**Purpose**: Can the tool help agents find and traverse files?

**Tests:**

- Discover files in directories
- Resolve relative paths to absolute
- Navigate directory hierarchies
- List contents efficiently

**Example Task:**

> "Find all Python files in the src/ directory"

#### 2. Analysis Scenario

**Purpose**: Can the tool help agents understand file contents?

**Tests:**

- Read file contents
- Search for patterns
- Extract information
- Aggregate data from multiple files

**Example Task:**

> "Find all functions that contain error handling"

#### 3. Modification Scenario

**Purpose**: Can the tool help agents safely modify files?

**Tests:**

- Update file contents
- Create new files
- Handle concurrent modifications
- Rollback on errors

**Example Task:**

> "Add a new function to utils.py"

### How Comparison Works

The framework compares **Baseline** vs **Enhanced**:

**Baseline Execution:**

- Agent works WITHOUT the tool
- Uses only built-in capabilities
- Represents current state

**Enhanced Execution:**

- Agent works WITH the tool
- Tool provides additional capabilities
- Represents future state

**Comparison:**

```
Improvement = (Enhanced - Baseline) / Baseline * 100%

Example:
- Baseline: 10 seconds, 60% success rate
- Enhanced: 4 seconds, 95% success rate
- Improvement: 60% faster, +35% success rate
```

### What Metrics Mean

#### Quality Metrics

**Success Rate** (0-100%)

- Percentage of operations completed successfully
- Higher is better
- < 70%: Poor, 70-85%: Acceptable, > 85%: Good

**Accuracy** (0-100%)

- Correctness of results produced
- Only meaningful for successful operations
- < 80%: Concerning, 80-95%: Acceptable, > 95%: Excellent

**Scenario Quality** (Custom per scenario)

- Navigation: Path resolution accuracy
- Analysis: Pattern matching precision
- Modification: Change correctness

#### Efficiency Metrics

**Total Time** (seconds)

- End-to-end scenario execution time
- Lower is better
- Compare baseline vs enhanced

**Operation Count** (integer)

- Number of tool invocations or API calls
- Lower is better
- Indicates efficiency

**Per-Operation Time** (milliseconds)

- Average time per tool operation
- Lower is better
- Indicates overhead

#### Tool-Specific Metrics

Defined by the adapter, examples:

- File operations count
- Cache hit rate
- Memory usage
- Concurrent operation support

## Phase 3: Running Your First Evaluation

### Step 3.1: Start Mock Evaluation

The mock evaluation demonstrates the framework without needin' a real MCP server:

```bash
# From tests/mcp_evaluation directory
python run_evaluation.py

# Optional: Specify output directory
python run_evaluation.py --output-dir ./my_results
```

### Step 3.2: Understanding Console Output

As the evaluation runs, you'll see:

```
┌─────────────────────────────────────────┐
│  MCP Tool Evaluation Framework v1.0.0    │
│  Tool: Serena Filesystem Tools (Mock)    │
└─────────────────────────────────────────┘

[1/3] Running Navigation Scenario...
  ├── Baseline execution... ✓ (3.2s, 60% success)
  └── Enhanced execution... ✓ (1.4s, 95% success)

[2/3] Running Analysis Scenario...
  ├── Baseline execution... ✓ (5.1s, 55% success)
  └── Enhanced execution... ✓ (2.1s, 90% success)

[3/3] Running Modification Scenario...
  ├── Baseline execution... ✓ (4.8s, 50% success)
  └── Enhanced execution... ✓ (2.3s, 85% success)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evaluation complete! ✓

Report saved to: results/serena_mock_20251117_143022/report.md
Raw metrics saved to: results/serena_mock_20251117_143022/raw_metrics.json

Executive Summary: INTEGRATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 3.3: Where Results Are Saved

```bash
# Results directory structure
results/serena_mock_20251117_143022/
├── report.md              # Main report (read this first!)
├── raw_metrics.json       # Detailed metrics data
└── evaluation_log.txt     # Execution log (for debugging)
```

**Tip:** Results are timestamped, so you can run multiple evaluations without overwriting previous ones.

## Phase 4: Analyzing Results

### Step 4.1: Reading the Executive Summary

Open the report:

```bash
cat results/serena_mock_*/report.md
# Or open in your preferred markdown viewer
```

Look for the **Executive Summary** at the top:

```markdown
## Executive Summary

**Recommendation: INTEGRATE**

The Serena filesystem tools provide significant value with 90% average success
rate (vs 55% baseline) and 58% reduction in execution time. The tool excels at
navigation and analysis scenarios with minimal overhead. Strong recommendation
for integration.

**Key Strengths:**

- 2.4x improvement in success rate
- 58% faster execution
- 67% reduction in operations
- Excellent navigation capabilities

**Considerations:**

- Modification scenario shows lower improvement (70% vs 85% for other scenarios)
- Requires MCP server infrastructure
```

**What this tells you:**

1. **Recommendation**: INTEGRATE (go ahead), CONSIDER (mixed), or DON'T INTEGRATE (stop)
2. **Key Strengths**: What the tool does well
3. **Considerations**: Potential concerns or limitations

### Step 4.2: Interpreting Metrics Tables

#### Quality Metrics Table

```markdown
| Metric               | Baseline | Enhanced | Improvement |
| -------------------- | -------- | -------- | ----------- |
| Success Rate         | 55%      | 90%      | +35 pp      |
| Accuracy             | 75%      | 98%      | +23 pp      |
| Navigation Quality   | 60%      | 95%      | +35 pp      |
| Analysis Quality     | 55%      | 90%      | +35 pp      |
| Modification Quality | 50%      | 85%      | +35 pp      |
```

**How to read this:**

- **pp** = percentage points (absolute difference)
- **Success Rate**: Big jump (55% → 90%) is excellent
- **Accuracy**: Nearly perfect in enhanced mode
- **Scenario Quality**: Consistent improvement across all scenarios

#### Efficiency Metrics Table

```markdown
| Metric             | Baseline | Enhanced | Improvement |
| ------------------ | -------- | -------- | ----------- |
| Total Time         | 13.1s    | 5.8s     | -56% (2.3x) |
| Operation Count    | 42       | 18       | -57%        |
| Avg Operation Time | 312ms    | 322ms    | +3%         |
```

**How to read this:**

- **Total Time**: 2.3x faster overall (excellent)
- **Operation Count**: Fewer operations needed (more efficient)
- **Avg Operation Time**: Slight overhead per operation (acceptable trade-off)

**Red Flags to Watch For:**

- Success rate < 70% in enhanced mode
- Efficiency worse than baseline
- High overhead per operation (> 500ms)
- Inconsistent results across scenarios

### Step 4.3: Understanding Capability Analysis

This section describes what the tool enables:

```markdown
## Capability Analysis

### Navigation Capabilities

- ✓ Fast directory traversal
- ✓ Efficient file discovery
- ✓ Path resolution and normalization
- ✓ Recursive directory walking

### Analysis Capabilities

- ✓ Content search with regex
- ✓ Multi-file pattern matching
- ✓ Metadata extraction
- ⚠ Limited binary file support

### Modification Capabilities

- ✓ Safe file updates
- ✓ Atomic operations
- ⚠ No built-in rollback
- ✗ Limited concurrent modification support
```

**Legend:**

- ✓ Full support, works well
- ⚠ Partial support, has limitations
- ✗ Not supported or problematic

### Step 4.4: Scenario Details

Each scenario section provides granular results:

```markdown
## Scenario 1: Navigation

**Objective:** Discover and traverse files efficiently

**Baseline Results:**

- Success Rate: 60%
- Total Time: 3.2s
- Operations: 15
- Issues: Slow directory traversal, path resolution errors

**Enhanced Results:**

- Success Rate: 95%
- Total Time: 1.4s
- Operations: 6
- Improvements: Fast file discovery, accurate path resolution

**Key Insights:**

- 2.3x faster with 60% fewer operations
- Eliminated path resolution errors
- Efficient handling of large directories
```

This tells you:

1. **What was tested**: Navigation tasks
2. **How baseline performed**: Slow and error-prone
3. **How tool improved things**: Much faster and reliable
4. **Specific wins**: What got better and why

## Phase 5: Making Decisions

### Decision Criteria

Use these criteria to decide on integration:

#### INTEGRATE Criteria

Proceed with integration if **ALL** of these are true:

1. **Quality Impact**: Enhanced success rate ≥ 85% AND improvement ≥ +20pp
2. **Efficiency Impact**: Time improvement ≥ 30% OR operation reduction ≥ 40%
3. **No Red Flags**: No critical limitations in key scenarios
4. **Executive Summary**: Recommendation is "INTEGRATE"

**Example:**

```
Success Rate: 90% (baseline 55%) → +35pp ✓
Time: -58% ✓
Critical scenarios: All good ✓
Recommendation: INTEGRATE ✓
→ Decision: INTEGRATE
```

#### CONSIDER Criteria

Proceed with caution if:

1. **Mixed Results**: Some scenarios excellent, others weak
2. **Modest Improvements**: 10-20pp quality boost OR 20-40% efficiency gain
3. **Known Limitations**: Tool has gaps but provides value
4. **Cost/Benefit Unclear**: Needs more investigation

**Action Steps:**

- Run additional focused evaluations
- Pilot in non-critical workflows
- Document known limitations
- Set success criteria for pilot

#### DON'T INTEGRATE Criteria

Do NOT integrate if **ANY** of these are true:

1. **Poor Quality**: Enhanced success rate < 70%
2. **Negative Efficiency**: Tool is slower or more operations than baseline
3. **Critical Failures**: Key scenarios fail or degrade
4. **Unacceptable Limitations**: Tool lacks must-have capabilities

**Example:**

```
Success Rate: 65% (baseline 55%) → +10pp (too low)
Time: +15% (slower!)
Critical scenario: Modification fails
→ Decision: DON'T INTEGRATE
```

### Making Your Decision

Follow this decision tree:

```
START
  │
  ├─→ Enhanced success rate ≥ 85%?
  │     ├─→ YES: Continue
  │     └─→ NO: DON'T INTEGRATE
  │
  ├─→ Time improvement ≥ 30% OR ops reduction ≥ 40%?
  │     ├─→ YES: Continue
  │     └─→ NO: CONSIDER (pilot first)
  │
  ├─→ Any critical scenario failures?
  │     ├─→ YES: DON'T INTEGRATE
  │     └─→ NO: Continue
  │
  └─→ Executive summary says INTEGRATE?
        ├─→ YES: INTEGRATE
        └─→ NO: CONSIDER (pilot first)
```

### Documenting Your Decision

Create a decision record:

```markdown
# MCP Tool Integration Decision: Serena Filesystem Tools

**Date:** 2025-11-17
**Evaluator:** [Your Name]
**Decision:** INTEGRATE

## Summary

Evaluation shows strong improvements across all scenarios with no critical
limitations. Tool meets all integration criteria.

## Metrics

- Success Rate: 90% (baseline 55%, +35pp)
- Time: 5.8s (baseline 13.1s, -56%)
- Operations: 18 (baseline 42, -57%)

## Decision Rationale

1. Quality impact exceeds threshold (85%+, 20pp+ improvement)
2. Efficiency impact exceeds threshold (56% time reduction)
3. No critical scenario failures
4. Framework recommends INTEGRATE

## Next Steps

1. Deploy MCP server in development environment
2. Integrate with agentic workflow
3. Monitor production metrics for 2 weeks
4. Re-evaluate if success rate drops below 80%

## Risks

- Requires MCP server infrastructure (manageable)
- Modification scenario slightly weaker (acceptable)
```

## Real MCP Tool Evaluation

Once you understand the framework with mock evaluations, you can evaluate real MCP tools.

### When You Need a Real Server

Use real server evaluation when:

- Making final integration decision
- Benchmarking actual performance
- Testing tool-specific features
- Validating mock results

### Step 1: Set Up Your MCP Server

```bash
# Example: Installing a generic MCP server
# (Replace with your tool's actual installation)

# Install MCP server package
npm install -g @your-vendor/mcp-server

# Start the server
mcp-server start --port 3000

# Verify server is running
curl http://localhost:3000/health
# Should return: {"status": "healthy"}
```

### Step 2: Create a Tool Adapter

Create an adapter for your tool in `adapters/`:

```python
# adapters/your_tool_adapter.py

from .base_adapter import BaseAdapter
from typing import Dict, Any

class YourToolAdapter(BaseAdapter):
    """Adapter for Your MCP Tool."""

    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url
        self.enabled = False

    async def enable(self, shared_context: Dict[str, Any]) -> None:
        """Make tool available to agent."""
        # Add tool to agent's available tools
        shared_context['tools'].append({
            'name': 'your_tool',
            'endpoint': self.server_url
        })
        self.enabled = True

    async def disable(self, shared_context: Dict[str, Any]) -> None:
        """Remove tool from agent."""
        shared_context['tools'] = [
            t for t in shared_context['tools']
            if t['name'] != 'your_tool'
        ]
        self.enabled = False

    async def measure(self) -> Dict[str, Any]:
        """Collect tool-specific metrics."""
        return {
            'api_calls': self.api_call_count,
            'cache_hits': self.cache_hit_count,
            'avg_latency_ms': self.avg_latency
        }
```

See [tests/mcp_evaluation/README.md](../../tests/mcp_evaluation/README.md) for complete adapter creation guide.

### Step 3: Run Real Evaluation

```bash
# Run evaluation with your adapter
python run_evaluation.py --adapter your_tool --server http://localhost:3000

# Expected output:
# [1/3] Running Navigation Scenario...
#   ├── Baseline execution (no tool)... ✓
#   └── Enhanced execution (with tool)... ✓
# [2/3] Running Analysis Scenario...
#   ...
# Report saved to: results/your_tool_20251117_150000/report.md
```

### Step 4: Compare Mock vs Real Results

```bash
# Mock results
cat results/your_tool_mock_*/report.md

# Real results
cat results/your_tool_20251117_*/report.md

# Key differences to look for:
# - Success rates (real should be similar or better)
# - Timing (real will be actual server latency)
# - Error patterns (real may reveal server issues)
```

**Red Flags:**

- Real success rate significantly lower than mock
- Real timing 3x+ slower than mock
- Unexpected errors or failures

## Common Workflows

### Workflow 1: Evaluating a Single Tool

**Scenario:** You have one MCP tool to evaluate.

```bash
# 1. Run mock evaluation first
python run_evaluation.py --adapter serena

# 2. Review results
cat results/serena_mock_*/report.md

# 3. If promising, set up real server and re-run
python run_evaluation.py --adapter serena --server http://localhost:3000

# 4. Make decision based on real results
```

**Time:** 30-60 minutes total

### Workflow 2: Comparing Multiple Tools

**Scenario:** You need to choose between Tool A and Tool B.

```bash
# Evaluate Tool A
python run_evaluation.py --adapter tool_a
cat results/tool_a_*/report.md

# Evaluate Tool B
python run_evaluation.py --adapter tool_b
cat results/tool_b_*/report.md

# Compare side-by-side
python compare_evaluations.py results/tool_a_* results/tool_b_*
```

**Decision Factors:**

- Which has better success rate?
- Which is more efficient?
- Which scenarios matter most to your use case?
- Which has acceptable limitations?

### Workflow 3: Re-evaluating After Tool Updates

**Scenario:** Tool vendor released a new version.

```bash
# Run evaluation with new version
python run_evaluation.py --adapter tool_name --version v2.0

# Compare with previous evaluation
python compare_evaluations.py \
  results/tool_name_old_* \
  results/tool_name_v2_*

# Look for:
# - Improvements in weak scenarios
# - Regression in previously good scenarios
# - New capabilities or limitations
```

**Decision:** Re-integrate if improvements justify update effort.

## Troubleshooting

### Problem: Framework Tests Fail

**Symptom:**

```
python test_framework.py
ERROR: test_scenarios_load failed
```

**Solution:**

```bash
# Check Python version
python --version  # Must be 3.10+

# Reinstall dependencies
pip install -e . --force-reinstall

# Check file permissions
ls -la framework/
# All files should be readable

# Try running individual tests
python -m pytest test_framework.py::test_scenarios_load -v
```

### Problem: Import/Path Errors

**Symptom:**

```
ModuleNotFoundError: No module named 'framework'
```

**Solution:**

```bash
# Ensure you're in the correct directory
pwd
# Should be: .../tests/mcp_evaluation

# Add parent directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install amplihack package
cd ../..
pip install -e .
cd tests/mcp_evaluation
```

### Problem: Evaluation Hangs or Times Out

**Symptom:**

```
[1/3] Running Navigation Scenario...
  ├── Baseline execution... [hangs forever]
```

**Solution:**

```bash
# Stop the evaluation (Ctrl+C)

# Check if MCP server is responsive
curl http://localhost:3000/health

# Restart server if needed
mcp-server restart

# Run with timeout flag
python run_evaluation.py --timeout 60

# Check logs
cat results/*/evaluation_log.txt
```

### Problem: Results Don't Make Sense

**Symptom:**

```
Success Rate: 150%  # Invalid!
Time: -5.0s         # Impossible!
```

**Solution:**

```bash
# Check raw metrics
cat results/*/raw_metrics.json

# Verify adapter implementation
python -c "from adapters.your_tool import YourToolAdapter; print(YourToolAdapter.__doc__)"

# Run framework tests
python test_framework.py

# Report bug if framework issue
# https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues
```

### Problem: Can't Connect to MCP Server

**Symptom:**

```
ConnectionError: Cannot reach MCP server at http://localhost:3000
```

**Solution:**

```bash
# Verify server is running
ps aux | grep mcp-server

# Check server logs
tail -f ~/.mcp/server.log

# Test connectivity
curl -v http://localhost:3000/health

# Check firewall/port
netstat -an | grep 3000

# Try different port
python run_evaluation.py --server http://localhost:3001
```

### Getting Help

If you can't resolve the issue:

1. **Check existing issues**: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
2. **Review test logs**: `cat results/*/evaluation_log.txt`
3. **Create a bug report** with:
   - Command you ran
   - Error message
   - Environment (Python version, OS)
   - Relevant log excerpts

## Next Steps

### After Your First Evaluation

**If results look good:**

1. Review [MCP Evaluation Framework Architecture](../../Specs/MCP_EVALUATION_FRAMEWORK.md)
2. Plan integration timeline
3. Set up production MCP server
4. Integrate tool into agentic workflow

**If results are mixed:**

1. Identify weak scenarios
2. Test those scenarios individually
3. Consult tool documentation
4. Consider pilot program

**If results are poor:**

1. Document why tool doesn't meet needs
2. Evaluate alternative tools
3. Consider building custom solution

### Creating Custom Adapters

Want to evaluate your own tool? See:

- [tests/mcp_evaluation/README.md](../../tests/mcp_evaluation/README.md) - Complete adapter creation guide
- [adapters/base_adapter.py](../../tests/mcp_evaluation/adapters/base_adapter.py) - Interface reference
- [adapters/serena_adapter.py](../../tests/mcp_evaluation/adapters/serena_adapter.py) - Example implementation

### Custom Scenario Creation

Need to test specific capabilities? Create custom scenarios:

```python
# framework/custom_scenarios.py

from .scenarios import BaseScenario

class MyCustomScenario(BaseScenario):
    """Test my specific use case."""

    async def run(self, agent, context):
        # Your test logic here
        result = await agent.perform_task(context)
        return result
```

See [tests/mcp_evaluation/README.md](../../tests/mcp_evaluation/README.md) for details.

### Contributing Improvements

Found a bug or want to improve the framework?

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [DEVELOPING_AMPLIHACK.md](../DEVELOPING_AMPLIHACK.md) for contribution guidelines.

## Summary

You've learned how to:

- ✓ Set up and run the MCP Evaluation Framework
- ✓ Execute mock evaluations
- ✓ Interpret results and metrics
- ✓ Make integration decisions
- ✓ Evaluate real MCP tools
- ✓ Troubleshoot common issues

**Remember the key principles:**

1. **Evidence over opinion** - Real metrics guide decisions
2. **Quality AND efficiency** - Both matter
3. **Know the limitations** - Every tool has trade-offs
4. **Document decisions** - Help future you and your team

**Ready to evaluate your first real tool?**

```bash
cd tests/mcp_evaluation
python run_evaluation.py
```

---

_Last updated: November 2025 | Framework Version: 1.0.0_
_For technical details, see [tests/mcp_evaluation/README.md](../../tests/mcp_evaluation/README.md)_
