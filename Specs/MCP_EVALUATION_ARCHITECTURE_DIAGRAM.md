# MCP Evaluation Framework - Architecture Diagrams

## System Overview

```mermaid
graph TB
    subgraph "Generic Evaluation Core"
        TS[TestScenario]
        EF[MCPEvaluationFramework]
        MC[MetricsCollector]
        RG[ReportGenerator]
        ER[EvaluationReport]
    end

    subgraph "Tool-Specific Adapters"
        TA[ToolAdapter Interface]
        SA[SerenaToolAdapter]
        CA[CopilotToolAdapter]
        FA[FutureToolAdapter]
    end

    subgraph "Configuration"
        TC[ToolConfiguration]
        SC[serena_config.yaml]
        CC[copilot_config.yaml]
    end

    TC --> EF
    SC --> SA
    CC --> CA
    TS --> EF
    EF --> MC
    EF --> TA
    TA -.implements.- SA
    TA -.implements.- CA
    TA -.implements.- FA
    MC --> RG
    RG --> ER

    style EF fill:#e1f5ff
    style TA fill:#fff4e1
    style TC fill:#f0f0f0
```

## Evaluation Flow

```mermaid
sequenceDiagram
    participant User
    participant Framework as MCPEvaluationFramework
    participant Adapter as ToolAdapter
    participant Executor as ScenarioExecutor
    participant Claude as Claude Code
    participant Collector as MetricsCollector
    participant Reporter as ReportGenerator

    User->>Framework: run_evaluation(scenarios, tool_config)
    Framework->>Adapter: load adapter from config

    loop For each scenario
        Note over Framework: Run baseline (tool disabled)
        Framework->>Adapter: disable()
        Framework->>Collector: start()
        Framework->>Executor: execute_task(prompt, codebase)
        Executor->>Claude: invoke with prompt
        Claude-->>Executor: execution result
        Executor-->>Framework: baseline_result
        Framework->>Collector: stop()
        Collector-->>Framework: baseline_metrics

        Note over Framework: Run enhanced (tool enabled)
        Framework->>Adapter: enable()
        Framework->>Collector: start()
        Framework->>Executor: execute_task(prompt, codebase)
        Executor->>Claude: invoke with prompt
        Note over Claude,Adapter: Claude uses MCP tool
        Claude->>Adapter: MCP commands
        Adapter-->>Claude: tool results
        Claude-->>Executor: execution result
        Executor-->>Framework: enhanced_result
        Framework->>Collector: stop()
        Collector-->>Framework: enhanced_metrics

        Framework->>Framework: compare_results(baseline, enhanced)
    end

    Framework->>Reporter: generate_report(all_results)
    Reporter-->>Framework: evaluation_report
    Framework-->>User: EvaluationReport
```

## Component Architecture

```mermaid
classDiagram
    class MCPEvaluationFramework {
        +ToolConfiguration tool_config
        +ToolAdapter adapter
        +MetricsCollector metrics_collector
        +run_evaluation(scenarios) EvaluationReport
        -_run_scenario(scenario, use_tool) ScenarioResult
        -_compare_results(baseline, enhanced) ComparisonResult
    }

    class ToolAdapter {
        <<interface>>
        +enable() void
        +disable() void
        +is_available() bool
        +collect_tool_metrics() ToolMetrics
        +get_capabilities() List~ToolCapability~
    }

    class SerenaToolAdapter {
        +server_url: str
        +call_log: List~Dict~
        +enable() void
        +disable() void
        +is_available() bool
        +collect_tool_metrics() ToolMetrics
        -_log_call(command, latency, success)
    }

    class TestScenario {
        +id: str
        +category: ScenarioCategory
        +task_prompt: str
        +success_criteria: List~Criterion~
        +baseline_metrics: List~str~
        +tool_metrics: List~str~
    }

    class MetricsCollector {
        +start() void
        +stop() Metrics
        +record_file_read(path) void
        +record_file_write(path) void
        +record_tool_call(command, latency, success) void
        +record_tokens(count) void
    }

    class EvaluationReport {
        +tool_config: ToolConfiguration
        +timestamp: datetime
        +results: List~ComparisonResult~
        +summary: Summary
        +recommendations: List~str~
        +save(path) void
    }

    class ToolConfiguration {
        +tool_id: str
        +tool_name: str
        +capabilities: List~ToolCapability~
        +adapter_class: str
        +expected_advantages: Dict
        +from_yaml(path) ToolConfiguration
        +validate() List~str~
    }

    MCPEvaluationFramework --> ToolConfiguration
    MCPEvaluationFramework --> ToolAdapter
    MCPEvaluationFramework --> MetricsCollector
    MCPEvaluationFramework --> TestScenario
    MCPEvaluationFramework --> EvaluationReport
    ToolAdapter <|-- SerenaToolAdapter
    ToolConfiguration --> ToolAdapter : creates
```

## Data Flow

```mermaid
flowchart LR
    subgraph Input
        TC[ToolConfiguration]
        TS[TestScenarios]
    end

    subgraph Processing
        EF[Framework]
        BL[Baseline Run]
        EN[Enhanced Run]
        CP[Compare]
    end

    subgraph Metrics
        QM[Quality Metrics]
        EM[Efficiency Metrics]
        TM[Tool Metrics]
    end

    subgraph Output
        CR[Comparison Results]
        ER[Evaluation Report]
        REC[Recommendations]
    end

    TC --> EF
    TS --> EF
    EF --> BL
    EF --> EN
    BL --> QM
    BL --> EM
    EN --> QM
    EN --> EM
    EN --> TM
    QM --> CP
    EM --> CP
    TM --> CP
    CP --> CR
    CR --> ER
    ER --> REC

    style EF fill:#e1f5ff
    style CP fill:#ffe1e1
    style ER fill:#e1ffe1
```

## Scenario Execution Flow

```mermaid
stateDiagram-v2
    [*] --> Setup
    Setup --> BaselineRun : Tool Disabled
    BaselineRun --> BaselineMetrics
    BaselineMetrics --> EnhancedRun : Tool Enabled
    EnhancedRun --> EnhancedMetrics
    EnhancedMetrics --> Comparison
    Comparison --> NextScenario : More Scenarios
    Comparison --> ReportGeneration : All Complete
    NextScenario --> Setup
    ReportGeneration --> [*]

    state BaselineRun {
        [*] --> StartMetrics
        StartMetrics --> ExecuteTask
        ExecuteTask --> ValidateResult
        ValidateResult --> StopMetrics
        StopMetrics --> [*]
    }

    state EnhancedRun {
        [*] --> StartMetrics
        StartMetrics --> ExecuteTask
        ExecuteTask --> LogToolCalls
        LogToolCalls --> ValidateResult
        ValidateResult --> StopMetrics
        StopMetrics --> [*]
    }
```

## Tool Adapter Integration

```mermaid
graph LR
    subgraph "Framework"
        EF[MCPEvaluationFramework]
    end

    subgraph "Adapter Interface"
        TA[ToolAdapter]
        EN[enable/disable]
        AV[is_available]
        MT[collect_metrics]
    end

    subgraph "Serena Adapter"
        SA[SerenaToolAdapter]
        ENV[Environment Variables]
        HC[Health Check]
        CL[Call Logging]
    end

    subgraph "Serena MCP Server"
        SRV[MCP Server :8080]
        LSP[LSP Features]
        SM[Symbol Navigation]
        HD[Hover Docs]
        SS[Semantic Search]
    end

    EF -->|uses| TA
    TA -->|implements| SA
    SA --> ENV
    SA --> HC
    SA --> CL
    SA -->|HTTP| SRV
    SRV --> LSP
    LSP --> SM
    LSP --> HD
    LSP --> SS

    style EF fill:#e1f5ff
    style TA fill:#fff4e1
    style SA fill:#e1ffe1
    style SRV fill:#ffe1e1
```

## Test Scenario Categories

```mermaid
mindmap
  root((MCP Evaluation))
    NAVIGATION
      Find Symbols
        Cross-file search
        Reference lookup
        Definition jumping
      Expected Improvement
        Faster execution
        No false positives
        Direct LSP access
    ANALYSIS
      Code Understanding
        Type information
        Dependency graphs
        Documentation
      Expected Improvement
        More accurate
        Complete analysis
        Authoritative data
    MODIFICATION
      Precise Edits
        Symbol-level changes
        Context-aware edits
        Error prevention
      Expected Improvement
        Faster implementation
        Fewer mistakes
        Better suggestions
```

## Metrics Hierarchy

```mermaid
graph TB
    M[All Metrics]

    M --> UM[Universal Metrics]
    M --> TM[Tool-Specific Metrics]

    UM --> QM[Quality Metrics]
    UM --> EM[Efficiency Metrics]

    QM --> COR[Correctness]
    QM --> COM[Completeness]
    QM --> CQ[Code Quality]

    EM --> TOK[Token Usage]
    EM --> TIME[Wall-Clock Time]
    EM --> OPS[File Operations]

    TM --> FU[Features Used]
    TM --> FE[Feature Effectiveness]
    TM --> LAT[Call Latency]
    TM --> FAIL[Failures]
    TM --> TS[Time Saved]

    style UM fill:#e1f5ff
    style TM fill:#ffe1e1
```

## Extension Pattern

```mermaid
graph TB
    subgraph "Existing"
        EF[Framework Core]
        TS[Test Scenarios]
        SA[Serena Adapter]
    end

    subgraph "Adding New Tool"
        NTC[1. New Tool Config]
        NAD[2. New Adapter]
        RS[3. Reuse Scenarios]
        RUN[4. Run Evaluation]
    end

    subgraph "No Changes Needed"
        NC1[Framework Core]
        NC2[Test Scenarios]
        NC3[Metrics System]
        NC4[Report Generator]
    end

    NTC -->|yaml| NAD
    NAD -->|implements ToolAdapter| EF
    RS -->|unchanged| TS
    RUN -->|same process| EF

    EF -.already exists.- NC1
    TS -.already exists.- NC2
    NC3 -.works automatically.-  RUN
    NC4 -.works automatically.- RUN

    style NTC fill:#e1ffe1
    style NAD fill:#e1ffe1
    style NC1 fill:#f0f0f0
    style NC2 fill:#f0f0f0
    style NC3 fill:#f0f0f0
    style NC4 fill:#f0f0f0
```

## Report Structure

```mermaid
graph TD
    ER[Evaluation Report]

    ER --> ES[Executive Summary]
    ER --> DR[Detailed Results]
    ER --> CA[Capability Analysis]
    ER --> REC[Recommendations]

    ES --> OI[Overall Improvement]
    ES --> MV[Most Valuable Feature]
    ES --> RC[Recommendation]

    DR --> S1[Scenario 1 Results]
    DR --> S2[Scenario 2 Results]
    DR --> S3[Scenario 3 Results]

    S1 --> MT[Metrics Table]
    S1 --> TU[Tool Usage]
    S1 --> AN[Analysis]

    CA --> C1[Capability 1]
    CA --> C2[Capability 2]
    CA --> C3[Capability 3]

    C1 --> US[Usage Stats]
    C1 --> SR[Success Rate]
    C1 --> VAL[Value Assessment]

    REC --> INT[Integration Decision]
    REC --> UC[Primary Use Cases]
    REC --> NS[Next Steps]

    style ER fill:#e1ffe1
    style ES fill:#e1f5ff
    style REC fill:#ffe1e1
```

## Implementation Phases

```mermaid
gantt
    title MCP Evaluation Framework Implementation
    dateFormat  YYYY-MM-DD
    section Phase 1: Core
    Core Types           :p1a, 2025-01-16, 1d
    Tool Adapter         :p1b, after p1a, 1d
    Metrics System       :p1c, after p1b, 1d
    Core Evaluator       :p1d, after p1c, 1d
    Report Generator     :p1e, after p1d, 1d

    section Phase 2: Serena
    Serena Adapter       :p2a, after p1e, 1d
    Test Codebase        :p2b, after p2a, 1d
    Test Scenarios       :p2c, after p2b, 2d

    section Phase 3: Execution
    Scenario Executor    :p3a, after p2c, 1d
    Integration Tests    :p3b, after p3a, 1d

    section Phase 4: Evaluation
    Run Evaluation       :p4a, after p3b, 1d
    Analysis             :p4b, after p4a, 1d
    Documentation        :p4c, after p4b, 1d
```

## Decision Points

```mermaid
flowchart TD
    START[Start Evaluation]
    LOAD[Load Tool Config]
    CHECK[Tool Available?]
    RUN[Run Scenarios]
    COMP[Compare Results]
    ANAL[Analyze Metrics]
    DEC{Recommendation}
    INT[Integrate Tool]
    NOINT[Don't Integrate]
    DOC[Document Findings]
    END[Complete]

    START --> LOAD
    LOAD --> CHECK
    CHECK -->|Yes| RUN
    CHECK -->|No| DOC
    RUN --> COMP
    COMP --> ANAL
    ANAL --> DEC
    DEC -->|Positive ROI| INT
    DEC -->|Negative ROI| NOINT
    INT --> DOC
    NOINT --> DOC
    DOC --> END

    style DEC fill:#ffe1e1
    style INT fill:#e1ffe1
    style NOINT fill:#ffe1e1
```

## Philosophy Alignment

```mermaid
mindmap
  root((Framework Design))
    Ruthless Simplicity
      Core <500 lines
      ONE clear purpose
      Complexity in adapters
    Brick Design
      Regeneratable components
      Clear contracts
      Self-contained modules
    Zero-BS
      Real execution
      No mocks
      Actual metrics
    Emergence
      Complex insights
      Simple comparisons
      Natural patterns
    Measurement-Driven
      Data over opinions
      Real usage
      Actionable results
```

---

## Diagram Usage Guide

- **System Overview**: High-level component relationships
- **Evaluation Flow**: Sequence of operations during evaluation
- **Component Architecture**: Detailed class structure
- **Data Flow**: How data moves through system
- **Scenario Execution**: State machine for running tests
- **Tool Adapter Integration**: Serena-specific example
- **Test Scenario Categories**: Three evaluation dimensions
- **Metrics Hierarchy**: Universal vs tool-specific metrics
- **Extension Pattern**: How to add new tools
- **Report Structure**: Output format
- **Implementation Phases**: Timeline and dependencies
- **Decision Points**: Evaluation outcome flow
- **Philosophy Alignment**: Design principles

These diagrams provide multiple perspectives on the framework architecture, from high-level concepts to implementation details.

---

**Status**: Architecture diagrams complete
**Format**: Mermaid (renders in GitHub, VS Code, and documentation tools)
**Coverage**: 13 diagrams covering all major architectural aspects
