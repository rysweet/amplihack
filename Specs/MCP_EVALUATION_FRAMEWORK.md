# MCP Evaluation Framework

## Purpose

Generic, reusable framework for evaluating ANY MCP server integration with amplihack. Measures real value through controlled comparisons of baseline vs tool-enhanced coding workflows.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│         Evaluation Framework (Generic)              │
│  ┌────────────┐  ┌──────────┐  ┌────────────────┐ │
│  │  Scenario  │→ │ Executor │→ │ Metrics        │ │
│  │  Runner    │  │          │  │ Collector      │ │
│  └────────────┘  └──────────┘  └────────────────┘ │
│         ↓              ↓               ↓            │
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

### Design Principles

1. **Brick Design**: Framework is regeneratable, each component has ONE responsibility
2. **Ruthless Simplicity**: Core framework is <500 lines, complexity in adapters
3. **Measurement-Driven**: Real execution data, not synthetic benchmarks
4. **Zero Future-Proofing**: Design for Serena NOW, extend naturally later

## Test Scenario Design

### Generic Test Categories

Three categories that reveal MCP tool value WITHOUT assuming specific capabilities:

#### Test Category 1: Cross-File Code Navigation

**Generic Skill**: Finding code across multiple files
**Baseline Approach**: grep, glob, sequential file reading
**MCP Enhancement**: Tool-specific navigation features

**Example Test**: "Find all implementations of interface `Handler` across codebase"

**Evaluation Points**:
- How many files examined?
- How many false positives?
- How long did it take?
- Did tool provide shortcuts?

#### Test Category 2: Code Understanding and Analysis

**Generic Skill**: Understanding code structure, relationships, dependencies
**Baseline Approach**: Read files, manual analysis, pattern matching
**MCP Enhancement**: Tool-specific analysis features

**Example Test**: "What are all the dependencies of class `DatabaseManager`?"

**Evaluation Points**:
- Completeness of analysis
- Accuracy of relationships
- Time to understanding
- Tool-specific insights

#### Test Category 3: Targeted Code Modification

**Generic Skill**: Making precise, context-aware edits
**Baseline Approach**: File read/edit/write with manual context
**MCP Enhancement**: Tool-specific editing features

**Example Test**: "Add logging to all public methods in service classes"

**Evaluation Points**:
- Edit precision (correct locations)
- Context awareness (proper imports, formatting)
- Modification count
- Error rate

### Scenario Structure

Each test scenario is a brick:

```python
@dataclass
class TestScenario:
    """A single evaluation test scenario."""

    # Identity
    id: str                          # "cross_file_nav_001"
    category: ScenarioCategory       # NAVIGATION, ANALYSIS, MODIFICATION
    name: str                        # "Find interface implementations"
    description: str                 # Human-readable description

    # Test Setup
    test_codebase: Path              # Path to test code
    initial_state: Dict              # Starting conditions

    # Test Execution
    task_prompt: str                 # What to ask Claude Code to do
    success_criteria: List[Criterion] # How to judge success

    # Measurement
    baseline_metrics: List[str]      # Which metrics to collect
    tool_metrics: List[str]          # Tool-specific measurements
```

## Metrics System

### Universal Metrics (Tool-Independent)

**Quality Metrics**:
```python
@dataclass
class QualityMetrics:
    """Metrics that apply to ANY tool evaluation."""

    # Correctness
    correctness_score: float         # 0.0-1.0, matches expected output
    test_failures: int               # If automated tests exist

    # Completeness
    requirements_met: int            # How many criteria satisfied
    requirements_total: int          # Total criteria

    # Code Quality
    follows_best_practices: bool     # Language-specific quality
    introduces_bugs: int             # Regression count
```

**Efficiency Metrics**:
```python
@dataclass
class EfficiencyMetrics:
    """Performance measurements."""

    # Resource Usage
    total_tokens: int                # LLM token consumption
    wall_clock_seconds: float        # Real time elapsed

    # Operations
    file_reads: int                  # Files read
    file_writes: int                 # Files modified
    tool_invocations: int            # MCP tool calls made

    # Optimization
    unnecessary_operations: int      # Redundant work detected
```

### Tool-Specific Metrics (Configurable)

```python
@dataclass
class ToolMetrics:
    """Tool-specific measurements."""

    # Tool Usage
    features_used: List[str]         # Which capabilities invoked
    feature_effectiveness: Dict[str, float]  # Success rate per feature

    # Tool Performance
    tool_call_latency: List[float]   # Per-call response time
    tool_failures: int               # Failed tool invocations
    fallback_count: int              # Times baseline approach used

    # Tool Value
    unique_insights: int             # Information ONLY tool provided
    time_saved_estimate: float       # Estimated speedup vs baseline
```

## Tool Configuration Schema

### ToolConfiguration

Describes ANY MCP tool's capabilities and expected advantages:

```python
@dataclass
class ToolCapability:
    """A single capability an MCP tool provides."""

    id: str                          # "symbol_navigation"
    name: str                        # "Symbol Navigation"
    description: str                 # What it does
    relevant_scenarios: List[ScenarioCategory]  # Where it helps
    expected_improvement: str        # "faster", "more_accurate", "both"

@dataclass
class ToolConfiguration:
    """Configuration for a specific MCP tool."""

    # Identity
    tool_id: str                     # "serena"
    tool_name: str                   # "Serena MCP Server"
    version: str                     # "1.0.0"
    description: str                 # What the tool does

    # Capabilities
    capabilities: List[ToolCapability]  # What it can do

    # Integration
    adapter_class: str               # Python class name
    setup_required: bool             # Needs configuration?
    setup_instructions: str          # How to set up

    # Evaluation
    expected_advantages: Dict[ScenarioCategory, List[str]]
    baseline_comparison_mode: str    # "with_vs_without", "before_vs_after"
```

### Example: Serena Configuration

```yaml
# tools/serena_config.yaml

tool_id: serena
tool_name: "Serena MCP Server"
version: "1.0.0"
description: "LSP-powered code intelligence for Python/TypeScript/Go"

capabilities:
  - id: symbol_navigation
    name: "Symbol Navigation"
    description: "Jump to definitions, find references across files"
    relevant_scenarios: [NAVIGATION, ANALYSIS]
    expected_improvement: "faster"

  - id: hover_documentation
    name: "Hover Documentation"
    description: "Get inline documentation and type information"
    relevant_scenarios: [ANALYSIS]
    expected_improvement: "more_accurate"

  - id: semantic_search
    name: "Semantic Search"
    description: "Find code by meaning, not just text"
    relevant_scenarios: [NAVIGATION, ANALYSIS]
    expected_improvement: "both"

adapter_class: "SerenaToolAdapter"
setup_required: true
setup_instructions: "Start Serena MCP server on port 8080"

expected_advantages:
  NAVIGATION:
    - "Faster symbol location across files"
    - "No false positives from text search"
  ANALYSIS:
    - "Accurate type information"
    - "Complete dependency graphs"
  MODIFICATION:
    - "Context-aware edit suggestions"

baseline_comparison_mode: "with_vs_without"
```

## Framework Implementation

### Core Evaluator

```python
class MCPEvaluationFramework:
    """Generic framework for evaluating MCP tool integrations."""

    def __init__(self, tool_config: ToolConfiguration):
        """Initialize with tool-specific configuration."""
        self.tool_config = tool_config
        self.adapter = self._load_adapter(tool_config.adapter_class)
        self.metrics_collector = MetricsCollector()

    def run_evaluation(
        self,
        scenarios: List[TestScenario],
        mode: str = "with_vs_without"
    ) -> EvaluationReport:
        """
        Run full evaluation suite.

        Args:
            scenarios: Test scenarios to run
            mode: "with_vs_without" or "before_vs_after"

        Returns:
            Complete evaluation report with all metrics
        """
        results = []

        for scenario in scenarios:
            # Run baseline (without tool)
            baseline_result = self._run_scenario(
                scenario,
                use_tool=False
            )

            # Run enhanced (with tool)
            enhanced_result = self._run_scenario(
                scenario,
                use_tool=True
            )

            # Compare and collect metrics
            comparison = self._compare_results(
                baseline_result,
                enhanced_result,
                scenario
            )

            results.append(comparison)

        return self._generate_report(results)

    def _run_scenario(
        self,
        scenario: TestScenario,
        use_tool: bool
    ) -> ScenarioResult:
        """
        Execute a single test scenario.

        Returns:
            Captured execution data and results
        """
        # Set up test environment
        test_env = self._setup_environment(scenario)

        # Configure tool availability
        if use_tool:
            self.adapter.enable()
        else:
            self.adapter.disable()

        # Start metrics collection
        self.metrics_collector.start()

        # Execute scenario via Claude Code
        # (Implementation delegates to Claude Code SDK)
        result = self._execute_task(
            scenario.task_prompt,
            test_env
        )

        # Collect metrics
        metrics = self.metrics_collector.stop()

        return ScenarioResult(
            scenario=scenario,
            use_tool=use_tool,
            output=result,
            metrics=metrics
        )

    def _compare_results(
        self,
        baseline: ScenarioResult,
        enhanced: ScenarioResult,
        scenario: TestScenario
    ) -> ComparisonResult:
        """Compare baseline vs tool-enhanced execution."""

        return ComparisonResult(
            scenario=scenario,
            quality_delta=self._compare_quality(baseline, enhanced),
            efficiency_delta=self._compare_efficiency(baseline, enhanced),
            tool_value=self._assess_tool_value(baseline, enhanced),
            recommendation=self._make_recommendation(baseline, enhanced)
        )

    def _generate_report(
        self,
        results: List[ComparisonResult]
    ) -> EvaluationReport:
        """Generate comprehensive evaluation report."""

        return EvaluationReport(
            tool_config=self.tool_config,
            timestamp=datetime.now(),
            results=results,
            summary=self._summarize_results(results),
            recommendations=self._aggregate_recommendations(results)
        )
```

### Tool Adapter Interface

```python
class ToolAdapter(ABC):
    """Abstract interface for tool-specific adapters."""

    @abstractmethod
    def enable(self) -> None:
        """Enable tool for Claude Code to use."""
        pass

    @abstractmethod
    def disable(self) -> None:
        """Disable tool (baseline mode)."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tool is available and working."""
        pass

    @abstractmethod
    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect tool-specific metrics."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        """Return tool's capabilities."""
        pass
```

### Serena Adapter (First Implementation)

```python
class SerenaToolAdapter(ToolAdapter):
    """Adapter for Serena MCP Server."""

    def __init__(self, config: ToolConfiguration):
        self.config = config
        self.server_url = "http://localhost:8080"
        self.enabled = False
        self.call_log: List[Dict] = []

    def enable(self) -> None:
        """Enable Serena for Claude Code to use."""
        # Set environment variable that Claude Code checks
        os.environ["SERENA_MCP_ENABLED"] = "1"
        os.environ["SERENA_MCP_URL"] = self.server_url
        self.enabled = True

    def disable(self) -> None:
        """Disable Serena (baseline mode)."""
        os.environ.pop("SERENA_MCP_ENABLED", None)
        self.enabled = False

    def is_available(self) -> bool:
        """Check if Serena is available and working."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def collect_tool_metrics(self) -> ToolMetrics:
        """Collect Serena-specific metrics."""

        # Analyze call log
        features_used = set()
        feature_success = defaultdict(list)
        latencies = []
        failures = 0

        for call in self.call_log:
            features_used.add(call["feature"])
            feature_success[call["feature"]].append(call["success"])
            latencies.append(call["latency"])
            if not call["success"]:
                failures += 1

        return ToolMetrics(
            features_used=list(features_used),
            feature_effectiveness={
                feature: sum(successes) / len(successes)
                for feature, successes in feature_success.items()
            },
            tool_call_latency=latencies,
            tool_failures=failures,
            fallback_count=self._count_fallbacks(),
            unique_insights=self._count_unique_insights(),
            time_saved_estimate=self._estimate_time_saved()
        )

    def get_capabilities(self) -> List[ToolCapability]:
        """Return Serena's capabilities."""
        return self.config.capabilities
```

## Test Scenario Definitions

### Scenario 1: Cross-File Navigation

```python
scenario_1 = TestScenario(
    id="cross_file_nav_001",
    category=ScenarioCategory.NAVIGATION,
    name="Find Interface Implementations",
    description="Locate all classes implementing a specific interface",

    test_codebase=Path("test_codebases/microservice_project"),
    initial_state={
        "target_interface": "Handler",
        "expected_implementations": 7,
        "expected_files": ["handlers/http.py", "handlers/grpc.py", ...]
    },

    task_prompt="""
    Find all classes that implement the Handler interface in this codebase.
    List each implementation with its file path and class name.
    """,

    success_criteria=[
        Criterion("find_all_implementations", lambda r: len(r.found) == 7),
        Criterion("no_false_positives", lambda r: all(r.valid)),
        Criterion("correct_file_paths", lambda r: r.paths_correct)
    ],

    baseline_metrics=["file_reads", "wall_clock_seconds", "correctness_score"],
    tool_metrics=["features_used", "tool_call_latency", "unique_insights"]
)
```

### Scenario 2: Code Understanding

```python
scenario_2 = TestScenario(
    id="code_analysis_001",
    category=ScenarioCategory.ANALYSIS,
    name="Map Class Dependencies",
    description="Identify all dependencies of a specific class",

    test_codebase=Path("test_codebases/microservice_project"),
    initial_state={
        "target_class": "DatabaseManager",
        "expected_direct_deps": 5,
        "expected_transitive_deps": 12
    },

    task_prompt="""
    Analyze the DatabaseManager class and identify:
    1. All direct dependencies (imports, instantiations)
    2. All methods it calls from other classes
    3. All classes that depend on it

    Provide a complete dependency graph.
    """,

    success_criteria=[
        Criterion("all_direct_deps", lambda r: len(r.direct) == 5),
        Criterion("transitive_complete", lambda r: len(r.transitive) >= 12),
        Criterion("no_missing_edges", lambda r: r.graph_complete)
    ],

    baseline_metrics=["file_reads", "wall_clock_seconds", "completeness_score"],
    tool_metrics=["features_used", "tool_call_latency", "unique_insights"]
)
```

### Scenario 3: Targeted Modification

```python
scenario_3 = TestScenario(
    id="code_modification_001",
    category=ScenarioCategory.MODIFICATION,
    name="Add Logging to Public Methods",
    description="Add structured logging to all public methods in service classes",

    test_codebase=Path("test_codebases/microservice_project"),
    initial_state={
        "target_pattern": "services/*.py",
        "expected_modifications": 23,
        "logging_format": "logger.info('method_name', extra={...})"
    },

    task_prompt="""
    Add structured logging to all public methods in the services/ directory.

    Requirements:
    - Use logger.info() at method entry
    - Include method name and parameters
    - Preserve existing code exactly
    - Add proper imports if needed
    """,

    success_criteria=[
        Criterion("all_methods_logged", lambda r: r.logged_count == 23),
        Criterion("correct_format", lambda r: r.format_correct),
        Criterion("no_breaks", lambda r: r.tests_pass),
        Criterion("imports_added", lambda r: r.imports_correct)
    ],

    baseline_metrics=["file_writes", "wall_clock_seconds", "correctness_score"],
    tool_metrics=["features_used", "edit_precision", "context_awareness"]
)
```

## Directory Structure

```
tests/mcp_evaluation/
├── framework/
│   ├── __init__.py
│   ├── evaluator.py              # MCPEvaluationFramework
│   ├── metrics.py                # Metrics collection and types
│   ├── reporter.py               # Report generation
│   ├── types.py                  # Core data types
│   └── adapter.py                # ToolAdapter interface
│
├── scenarios/
│   ├── __init__.py
│   ├── scenario_1_navigation.py  # Cross-file navigation tests
│   ├── scenario_2_analysis.py    # Code understanding tests
│   ├── scenario_3_modification.py # Targeted edit tests
│   └── test_codebases/           # Realistic test code
│       ├── microservice_project/ # Python microservice
│       ├── typescript_frontend/  # TypeScript React app
│       └── go_backend/           # Go service
│
├── tools/
│   ├── __init__.py
│   ├── serena_config.yaml        # Serena tool configuration
│   ├── serena_adapter.py         # SerenaToolAdapter implementation
│   └── future_tools/             # Future tool adapters
│
├── results/
│   ├── serena_2025_01_16/        # Date-stamped results
│   │   ├── baseline.json         # Baseline execution data
│   │   ├── enhanced.json         # Tool-enhanced data
│   │   ├── comparison.json       # Side-by-side comparison
│   │   └── report.md             # Human-readable report
│   └── README.md                 # Result archive guide
│
├── README.md                      # Framework documentation
└── run_evaluation.py              # Main entry point
```

## Usage

### Running Serena Evaluation

```python
# Load Serena configuration
serena_config = ToolConfiguration.from_yaml("tools/serena_config.yaml")

# Create framework instance
framework = MCPEvaluationFramework(serena_config)

# Define test scenarios
scenarios = [
    scenario_1_navigation,
    scenario_2_analysis,
    scenario_3_modification
]

# Run evaluation
report = framework.run_evaluation(scenarios, mode="with_vs_without")

# Save results
report.save("results/serena_2025_01_16/")

# Print summary
print(report.summary())
```

### Adding a New Tool (Future)

```python
# 1. Create tool configuration
copilot_config = ToolConfiguration(
    tool_id="github_copilot_mcp",
    tool_name="GitHub Copilot MCP Server",
    version="1.0.0",
    capabilities=[
        ToolCapability(
            id="semantic_search",
            name="Semantic Code Search",
            relevant_scenarios=[ScenarioCategory.NAVIGATION],
            expected_improvement="both"
        )
    ],
    adapter_class="CopilotToolAdapter"
)

# 2. Implement adapter
class CopilotToolAdapter(ToolAdapter):
    def enable(self):
        os.environ["COPILOT_MCP_ENABLED"] = "1"
    # ... implement other methods

# 3. Run same evaluation
framework = MCPEvaluationFramework(copilot_config)
report = framework.run_evaluation(scenarios)
```

## Report Format

### Evaluation Report Structure

```markdown
# MCP Tool Evaluation Report

**Tool**: Serena MCP Server v1.0.0
**Date**: 2025-01-16
**Scenarios**: 3 (Navigation, Analysis, Modification)

## Executive Summary

- **Overall Improvement**: 42% faster, 23% more accurate
- **Most Valuable Feature**: Symbol navigation (67% time savings)
- **Recommendation**: INTEGRATE with confidence

## Detailed Results

### Scenario 1: Cross-File Navigation

**Task**: Find all Handler interface implementations

| Metric | Baseline | With Serena | Delta |
|--------|----------|-------------|-------|
| Time | 45.3s | 12.1s | -73% |
| File Reads | 127 | 8 | -94% |
| Correctness | 85% | 100% | +15% |
| False Positives | 3 | 0 | -100% |

**Tool Usage**:
- `find_symbol`: 8 calls, 100% success
- `get_references`: 4 calls, 100% success

**Analysis**: Serena's symbol navigation eliminated false positives from text-based search and reduced file operations by 94%.

### Scenario 2: Code Understanding

[Similar detailed breakdown]

### Scenario 3: Targeted Modification

[Similar detailed breakdown]

## Capability Analysis

### Symbol Navigation
- **Usage**: 8/3 scenarios
- **Success Rate**: 100%
- **Time Savings**: 67%
- **Value**: HIGH

### Hover Documentation
- **Usage**: 2/3 scenarios
- **Success Rate**: 95%
- **Accuracy Gain**: 23%
- **Value**: MEDIUM

## Recommendations

1. **INTEGRATE**: Serena provides measurable value in navigation and analysis tasks
2. **Primary Use Cases**: Cross-file navigation, dependency analysis
3. **Setup Cost**: Low (single server, simple config)
4. **Risk**: Low (degrades gracefully to baseline)

## Next Steps

- [ ] Integrate Serena adapter into amplihack
- [ ] Document Serena setup in CLAUDE.md
- [ ] Add Serena capabilities to agent workflows
- [ ] Monitor real-world usage metrics
```

## Extension Points

### Adding New Test Scenarios

```python
# Create new scenario following template
scenario_4 = TestScenario(
    id="refactoring_001",
    category=ScenarioCategory.MODIFICATION,
    name="Extract Common Code",
    description="Identify and extract duplicate code into shared utilities",
    # ... rest of scenario definition
)

# Scenarios automatically work with ANY tool
framework.run_evaluation([scenario_4])
```

### Adding New Metrics

```python
# Define new metric type
@dataclass
class CustomMetric:
    name: str
    value: float
    description: str

# Register with metrics collector
metrics_collector.register_custom_metric(CustomMetric)

# Automatically collected and reported
```

### Supporting New Tool Types

```python
# Framework supports ANY tool that implements ToolAdapter interface
class CustomToolAdapter(ToolAdapter):
    def enable(self):
        # Tool-specific enablement
        pass

    def disable(self):
        # Tool-specific disablement
        pass

    # ... implement other methods

# No framework changes needed
```

## Success Criteria

Framework is successful if:

1. **Serena evaluation completes** - First case study works end-to-end
2. **Results are actionable** - Clear integrate/don't-integrate recommendation
3. **Reusable without redesign** - Adding GitHub Copilot MCP requires only:
   - New config file
   - New adapter implementation
   - Same scenarios work unchanged
4. **Simple core** - Core framework <500 lines, complexity in adapters
5. **Measurement-driven** - Real execution data, not opinions

## Implementation Plan

### Phase 1: Core Framework (Week 1)
- [ ] Implement `MCPEvaluationFramework` class
- [ ] Implement `MetricsCollector` system
- [ ] Define core data types
- [ ] Create `ToolAdapter` interface

### Phase 2: Serena Integration (Week 1-2)
- [ ] Implement `SerenaToolAdapter`
- [ ] Create Serena configuration
- [ ] Build test codebases
- [ ] Define 3 test scenarios

### Phase 3: Execution & Reporting (Week 2)
- [ ] Implement scenario runner
- [ ] Build comparison logic
- [ ] Create report generator
- [ ] Run Serena evaluation

### Phase 4: Documentation & Handoff (Week 2)
- [ ] Write framework documentation
- [ ] Document Serena results
- [ ] Create "Adding New Tools" guide
- [ ] Integrate findings into amplihack

## Philosophy Alignment

- **Ruthless Simplicity**: Core framework does ONE thing - run scenarios and collect metrics
- **Brick Design**: Each component (framework, adapter, scenario) is regeneratable
- **Zero-BS**: No mocks, no stubs - real execution with real metrics
- **Emergence**: Complex insights emerge from simple comparisons
- **Measurement-Driven**: Real data drives decisions, not assumptions

---

**Status**: Specification Complete
**Next**: Implement core framework and Serena adapter
