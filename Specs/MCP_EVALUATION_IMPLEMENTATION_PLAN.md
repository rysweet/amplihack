# MCP Evaluation Framework Implementation Plan

## Purpose

Detailed implementation plan for building the generic MCP evaluation framework and executing the first Serena case study.

## Implementation Strategy

**Approach**: Build minimal working core, validate with Serena, then document extensibility patterns.

**Timeline**: 2 weeks (10 business days)

**Success Metric**: Complete Serena evaluation producing actionable integrate/don't-integrate recommendation.

## Phase 1: Core Framework (Days 1-3)

### Module 1: Core Types and Data Structures

**File**: `tests/mcp_evaluation/framework/types.py`

**Purpose**: Define all data types used by evaluation framework

**Contract**:

- Input: None (pure type definitions)
- Output: Type classes for scenarios, metrics, results
- Side Effects: None

**Implementation**:

```python
# Key types to define:
- ScenarioCategory (enum)
- TestScenario (dataclass)
- Criterion (dataclass)
- QualityMetrics (dataclass)
- EfficiencyMetrics (dataclass)
- ToolMetrics (dataclass)
- ScenarioResult (dataclass)
- ComparisonResult (dataclass)
- EvaluationReport (dataclass)
```

**Test Requirements**:

- All dataclasses can be instantiated
- Enums have correct values
- Type annotations are complete

**Estimated Time**: 4 hours

---

### Module 2: Tool Adapter Interface

**File**: `tests/mcp_evaluation/framework/adapter.py`

**Purpose**: Abstract interface for tool-specific adapters

**Contract**:

- Input: ToolConfiguration
- Output: ToolAdapter interface
- Side Effects: Tool enablement/disablement

**Implementation**:

```python
class ToolAdapter(ABC):
    @abstractmethod
    def enable(self) -> None:
        """Enable tool for use."""

    @abstractmethod
    def disable(self) -> None:
        """Disable tool (baseline mode)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tool is working."""

    @abstractmethod
    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect tool-specific metrics."""

    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        """Return tool capabilities."""
```

**Test Requirements**:

- Interface is complete
- Mock adapter can be implemented
- All methods are abstract

**Estimated Time**: 2 hours

---

### Module 3: Metrics Collection System

**File**: `tests/mcp_evaluation/framework/metrics.py`

**Purpose**: Collect universal and tool-specific metrics during execution

**Contract**:

- Input: Execution context, tool adapter
- Output: QualityMetrics, EfficiencyMetrics, ToolMetrics
- Side Effects: Metric accumulation during execution

**Implementation**:

```python
class MetricsCollector:
    def __init__(self, adapter: Optional[ToolAdapter] = None):
        """Initialize metrics collector."""

    def start(self) -> None:
        """Start metrics collection."""

    def stop(self) -> Metrics:
        """Stop collection and return metrics."""

    def record_file_read(self, path: str) -> None:
        """Record a file read operation."""

    def record_file_write(self, path: str) -> None:
        """Record a file write operation."""

    def record_tool_call(self, command: str, latency: float, success: bool) -> None:
        """Record an MCP tool invocation."""

    def record_tokens(self, count: int) -> None:
        """Record token usage."""
```

**Test Requirements**:

- Metrics accumulate correctly
- Start/stop timing works
- Tool metrics separated from universal metrics

**Estimated Time**: 6 hours

---

### Module 4: Core Evaluator

**File**: `tests/mcp_evaluation/framework/evaluator.py`

**Purpose**: Main evaluation orchestration

**Contract**:

- Input: List[TestScenario], ToolConfiguration
- Output: EvaluationReport
- Side Effects: Executes scenarios, collects metrics

**Implementation**:

```python
class MCPEvaluationFramework:
    def __init__(self, tool_config: ToolConfiguration):
        """Initialize framework with tool configuration."""

    def run_evaluation(
        self,
        scenarios: List[TestScenario],
        mode: str = "with_vs_without"
    ) -> EvaluationReport:
        """Run full evaluation suite."""

    def _run_scenario(
        self,
        scenario: TestScenario,
        use_tool: bool
    ) -> ScenarioResult:
        """Execute single test scenario."""

    def _compare_results(
        self,
        baseline: ScenarioResult,
        enhanced: ScenarioResult,
        scenario: TestScenario
    ) -> ComparisonResult:
        """Compare baseline vs tool-enhanced execution."""
```

**Test Requirements**:

- Can run single scenario
- Collects metrics correctly
- Comparison logic is sound

**Estimated Time**: 8 hours

---

### Module 5: Report Generator

**File**: `tests/mcp_evaluation/framework/reporter.py`

**Purpose**: Generate human-readable evaluation reports

**Contract**:

- Input: EvaluationReport
- Output: Markdown report file
- Side Effects: Writes report to disk

**Implementation**:

```python
class ReportGenerator:
    def __init__(self, report: EvaluationReport):
        """Initialize with evaluation results."""

    def generate_markdown(self) -> str:
        """Generate markdown report."""

    def save(self, path: Path) -> None:
        """Save report to file."""

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""

    def _generate_scenario_details(self, result: ComparisonResult) -> str:
        """Generate detailed scenario results."""

    def _generate_recommendations(self) -> str:
        """Generate actionable recommendations."""
```

**Test Requirements**:

- Markdown is well-formatted
- All sections present
- Recommendations are clear

**Estimated Time**: 6 hours

---

## Phase 2: Serena Integration (Days 4-6)

### Module 6: Serena Tool Adapter

**File**: `tests/mcp_evaluation/tools/serena_adapter.py`

**Purpose**: Serena-specific tool adapter implementation

**Contract**:

- Input: ToolConfiguration for Serena
- Output: Working SerenaToolAdapter
- Side Effects: Serena server enablement/disablement

**Implementation**:

```python
class SerenaToolAdapter(ToolAdapter):
    def __init__(self, config: ToolConfiguration):
        """Initialize Serena adapter."""

    def enable(self) -> None:
        """Enable Serena via environment variables."""

    def disable(self) -> None:
        """Disable Serena."""

    def is_available(self) -> bool:
        """Check Serena health endpoint."""

    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect Serena-specific metrics from call log."""

    def get_capabilities(self) -> List[ToolCapability]:
        """Return Serena capabilities."""

    def _log_call(self, command: str, latency: float, success: bool) -> None:
        """Log MCP call for metrics."""
```

**Test Requirements**:

- Enable/disable works
- Health check correctly detects Serena
- Metrics collection is accurate

**Estimated Time**: 6 hours

---

### Module 7: Test Codebase Creation

**Files**: `tests/mcp_evaluation/scenarios/test_codebases/microservice_project/`

**Purpose**: Create realistic Python codebase for testing

**Contract**:

- Input: None (generated once)
- Output: 20+ file Python project with realistic structure
- Side Effects: None

**Requirements**:

- Multiple modules with imports
- Class definitions with inheritance
- Interface implementations
- Function definitions with type hints
- Documentation strings
- Realistic directory structure

**Structure**:

```
microservice_project/
├── services/
│   ├── __init__.py
│   ├── user_service.py
│   ├── auth_service.py
│   └── database_service.py
├── handlers/
│   ├── __init__.py
│   ├── http_handler.py
│   ├── grpc_handler.py
│   └── base_handler.py (interface)
├── models/
│   ├── __init__.py
│   ├── user.py
│   └── session.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── config.py
└── tests/
    └── test_services.py
```

**Test Requirements**:

- All files are valid Python
- Imports resolve correctly
- Type hints are present
- LSP can index the project

**Estimated Time**: 8 hours

---

### Module 8: Test Scenario Implementations

**Files**:

- `tests/mcp_evaluation/scenarios/scenario_1_navigation.py`
- `tests/mcp_evaluation/scenarios/scenario_2_analysis.py`
- `tests/mcp_evaluation/scenarios/scenario_3_modification.py`

**Purpose**: Define concrete test scenarios for evaluation

**Contract**:

- Input: Test codebase
- Output: TestScenario objects with success criteria
- Side Effects: None

**Implementation**: Each scenario needs:

- Clear task prompt
- Success criteria (computable)
- Expected results
- Baseline metrics to collect
- Tool metrics to collect

**Test Requirements**:

- Scenarios can be instantiated
- Success criteria are computable
- Task prompts are clear

**Estimated Time**: 10 hours (3-4 hours per scenario)

---

## Phase 3: Execution & Validation (Days 7-8)

### Module 9: Scenario Executor Integration

**File**: `tests/mcp_evaluation/framework/executor.py`

**Purpose**: Bridge between evaluation framework and Claude Code

**Contract**:

- Input: TaskPrompt, TestEnvironment
- Output: Execution result with captured metrics
- Side Effects: Claude Code invocation, metrics collection

**Implementation**:

```python
class ScenarioExecutor:
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize executor."""

    def execute_task(
        self,
        prompt: str,
        codebase_path: Path,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute task via Claude Code and capture metrics."""

    def _setup_environment(self, codebase_path: Path) -> None:
        """Set up execution environment."""

    def _capture_output(self) -> str:
        """Capture Claude Code output."""

    def _validate_result(self, output: str, criteria: List[Criterion]) -> bool:
        """Validate result against success criteria."""
```

**Test Requirements**:

- Can invoke Claude Code
- Metrics are captured during execution
- Output is parseable

**Estimated Time**: 10 hours

---

### Module 10: Integration Testing

**File**: `tests/mcp_evaluation/test_integration.py`

**Purpose**: End-to-end integration tests

**Tests**:

1. Load Serena configuration
2. Create framework instance
3. Run single scenario (baseline)
4. Run single scenario (with Serena)
5. Compare results
6. Generate report

**Test Requirements**:

- All tests pass
- Report is generated
- Metrics are collected

**Estimated Time**: 6 hours

---

## Phase 4: Serena Evaluation (Days 9-10)

### Task 11: Run Full Serena Evaluation

**Activities**:

1. Start Serena MCP server
2. Verify health check passes
3. Run all 3 scenarios (baseline)
4. Run all 3 scenarios (with Serena)
5. Generate comparison report
6. Analyze results

**Deliverables**:

- `results/serena_2025_01_16/baseline.json`
- `results/serena_2025_01_16/enhanced.json`
- `results/serena_2025_01_16/comparison.json`
- `results/serena_2025_01_16/report.md`

**Estimated Time**: 8 hours

---

### Task 12: Analysis and Recommendations

**Activities**:

1. Review all metrics
2. Identify patterns (where Serena helps most)
3. Assess cost/benefit
4. Make integrate/don't-integrate recommendation
5. Document findings

**Deliverables**:

- Executive summary
- Capability analysis
- Integration recommendations
- Next steps

**Estimated Time**: 4 hours

---

### Task 13: Documentation

**Activities**:

1. Framework usage guide
2. Adding new tools guide
3. Creating new scenarios guide
4. Serena-specific findings

**Deliverables**:

- `tests/mcp_evaluation/README.md`
- `tests/mcp_evaluation/ADDING_NEW_TOOLS.md`
- `tests/mcp_evaluation/CREATING_SCENARIOS.md`
- `results/serena_2025_01_16/FINDINGS.md`

**Estimated Time**: 6 hours

---

## Total Effort Estimate

| Phase                           | Tasks             | Hours  | Days   |
| ------------------------------- | ----------------- | ------ | ------ |
| Phase 1: Core Framework         | 5 modules         | 26     | 3      |
| Phase 2: Serena Integration     | 4 modules         | 24     | 3      |
| Phase 3: Execution & Validation | 2 modules         | 16     | 2      |
| Phase 4: Evaluation & Docs      | 3 tasks           | 18     | 2      |
| **Total**                       | **14 components** | **84** | **10** |

## Risks and Mitigations

### Risk 1: Serena Setup Complexity

**Impact**: High
**Probability**: Medium
**Mitigation**: Document setup thoroughly, create health check validation

### Risk 2: Claude Code Integration

**Impact**: High
**Probability**: Medium
**Mitigation**: Start with simple executor, iterate based on learnings

### Risk 3: Metrics Collection Overhead

**Impact**: Medium
**Probability**: Low
**Mitigation**: Use lightweight instrumentation, profile performance

### Risk 4: Test Codebase Realism

**Impact**: Medium
**Probability**: Medium
**Mitigation**: Base on real amplihack code, validate with LSP indexing

## Success Criteria

Framework implementation is successful if:

1. **Serena evaluation completes** - All 3 scenarios run baseline and enhanced
2. **Results are actionable** - Clear recommendation with supporting data
3. **Framework is reusable** - Can add GitHub Copilot MCP with only:
   - New config file
   - New adapter implementation
   - Same scenarios work unchanged
4. **Simple core maintained** - Core framework stays under 500 lines
5. **Reports are readable** - Stakeholders understand findings without deep dive

## Next Steps After Implementation

1. **If Serena evaluation positive**:
   - Integrate Serena adapter into amplihack
   - Update CLAUDE.md with Serena capabilities
   - Train agents to use Serena features

2. **If Serena evaluation negative**:
   - Document why (setup complexity, performance, limited value)
   - Keep framework for evaluating other tools
   - Try next MCP server candidate

3. **Framework evolution**:
   - Add GitHub Copilot MCP evaluation
   - Create more test scenarios
   - Refine metrics based on learnings

## Deliverables Checklist

### Code

- [ ] Core framework (5 modules)
- [ ] Serena adapter
- [ ] Test codebase (20+ files)
- [ ] Test scenarios (3 scenarios)
- [ ] Scenario executor
- [ ] Integration tests

### Documentation

- [ ] Framework architecture spec
- [ ] Tool configuration schema
- [ ] Serena configuration
- [ ] Implementation plan (this document)
- [ ] Usage guide
- [ ] Adding new tools guide
- [ ] Creating scenarios guide

### Results

- [ ] Serena evaluation report
- [ ] Baseline execution data
- [ ] Enhanced execution data
- [ ] Comparison metrics
- [ ] Integration recommendations
- [ ] Findings document

---

**Status**: Implementation plan complete
**Next**: Begin Phase 1 - Core Framework implementation
