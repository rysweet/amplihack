# Data Flow Template

## When to Use This Template

Use this template when investigating or explaining:

- Data processing pipelines
- ETL (Extract, Transform, Load) systems
- Data transformation workflows
- Stream processing architectures
- Request/response data flows
- Data validation and sanitization pipelines

**Trigger Conditions:**

- Data flows through multiple processing stages
- Data is transformed or enriched at each stage
- System processes data from input to output
- Multiple data transformations in sequence

**Examples:**

- Data processing pipelines (Spark, Airflow)
- API request/response transformations
- File processing workflows
- Stream processing (Kafka, event streams)
- Data validation and cleaning pipelines
- Machine learning data preprocessing

## Template Diagram

```mermaid
graph TD
    A[Input<br/>Raw Data Source] -->|Transform 1| B[Stage 1<br/>Parse/Extract]
    B -->|Transform 2| C[Stage 2<br/>Validate/Filter]
    C -->|Transform 3| D[Stage 3<br/>Enrich/Augment]
    D -->|Transform 4| E[Output<br/>Final Result]

    F[Error Handler<br/>Failure Recovery] -.->|On Failure| B
    F -.->|On Failure| C
    F -.->|On Failure| D

    G[Metadata<br/>Context/Config] -.->|Enhances| D

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bfb,stroke:#333,stroke-width:2px
    style F fill:#fbb,stroke:#333
```

## Customization Guide

Replace these placeholders with your specific data flow stages:

1. **Input** → Your data source (e.g., "API Request", "CSV File", "Event Stream")
2. **Stage 1** → First transformation (e.g., "Parse JSON", "Extract Fields", "Deserialize")
3. **Stage 2** → Second transformation (e.g., "Validate Schema", "Filter Invalid", "Sanitize")
4. **Stage 3** → Third transformation (e.g., "Enrich with DB Data", "Calculate Fields", "Aggregate")
5. **Output** → Final result (e.g., "API Response", "Database Record", "Published Event")

**Optional Components:**

- **Error Handler** → If failures at any stage are handled (dotted line)
- **Metadata/Config** → If context enhances processing (dotted line)

### Example: API Request Processing

```mermaid
graph TD
    A[HTTP Request<br/>Raw JSON Payload] -->|Parse| B[JSON Parser<br/>Deserialize Body]
    B -->|Validate| C[Schema Validator<br/>Check Required Fields]
    C -->|Authenticate| D[Auth Service<br/>Verify Token]
    D -->|Process| E[Business Logic<br/>Execute Operation]
    E -->|Format| F[Response Formatter<br/>Serialize Result]
    F -->|Return| G[HTTP Response<br/>JSON Result]

    H[Error Handler<br/>400/401/500 Errors] -.->|On Failure| B
    H -.->|On Failure| C
    H -.->|On Failure| D
    H -.->|On Failure| E

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
    style H fill:#fbb,stroke:#333
```

## Branching Data Flow Variation

For pipelines where data splits and merges:

```mermaid
graph TD
    A[Input] -->|Parse| B[Parsed Data]
    B -->|Split| C{Router}
    C -->|Type A| D[Process A]
    C -->|Type B| E[Process B]
    C -->|Type C| F[Process C]
    D -->|Merge| G[Combiner]
    E -->|Merge| G
    F -->|Merge| G
    G -->|Output| H[Result]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#ff9,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bbf,stroke:#333
    style F fill:#bbf,stroke:#333
    style H fill:#bfb,stroke:#333,stroke-width:2px
```

## Parallel Processing Variation

For pipelines with independent parallel stages:

```mermaid
graph TD
    A[Input] -->|Distribute| B[Stage 1a<br/>Parse Metadata]
    A -->|Distribute| C[Stage 1b<br/>Parse Content]
    A -->|Distribute| D[Stage 1c<br/>Parse Links]

    B -->|Merge| E[Combiner]
    C -->|Merge| E
    D -->|Merge| E

    E -->|Validate| F[Validator]
    F -->|Output| G[Result]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#ff9,stroke:#333
    style G fill:#bfb,stroke:#333,stroke-width:2px
```

## Quality Checklist

Before using this diagram, verify:

- [ ] **Input is clear** - What data enters the pipeline?
- [ ] **Transformations are labeled** - What happens at each stage?
- [ ] **Output is explicit** - What is the final result?
- [ ] **Flow direction is obvious** - Follows left-to-right or top-to-bottom
- [ ] **Error handling shown** - What happens when stages fail?
- [ ] **Side effects visible** (if any) - Logging, metrics, external calls
- [ ] **Branching is clear** (if applicable) - How data splits/merges
- [ ] **Labels describe transformations** - Not just "Step 1", "Step 2"

## Common Variations

### Variation 1: Simple Linear Pipeline

```mermaid
graph LR
    A[Input] -->|Parse| B[Parsed]
    B -->|Validate| C[Valid]
    C -->|Transform| D[Output]

    style A fill:#f9f,stroke:#333
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bfb,stroke:#333
```

### Variation 2: Pipeline with Side Effects

```mermaid
graph TD
    A[Input] -->|Process| B[Stage 1]
    B -->|Process| C[Stage 2]
    C -->|Process| D[Output]

    B -.->|Log| E[Logger]
    C -.->|Metric| F[Metrics]
    D -.->|Notify| G[Notification]

    style A fill:#f9f,stroke:#333
    style D fill:#bfb,stroke:#333
```

### Variation 3: Feedback Loop

```mermaid
graph TD
    A[Input] -->|Process| B[Stage 1]
    B -->|Validate| C{Valid?}
    C -->|Yes| D[Output]
    C -->|No| E[Retry Logic]
    E -->|Retry| B

    style A fill:#f9f,stroke:#333
    style C fill:#ff9,stroke:#333
    style D fill:#bfb,stroke:#333
```

### Variation 4: Stream Processing

```mermaid
graph LR
    A[Event Stream<br/>Kafka Topic] -->|Consume| B[Consumer]
    B -->|Process| C[Transformer]
    C -->|Aggregate| D[Window Aggregator]
    D -->|Publish| E[Output Stream]

    F[State Store] -.->|Read/Write| D

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
    style F fill:#ff9,stroke:#333
```

## Usage Tips

**When to use this template:**

- User asks "how does data flow through X?"
- Explaining processing pipelines
- Documenting ETL workflows
- Showing data transformations

**What to emphasize:**

- Input format and source
- Transformation at each stage (be specific)
- Output format and destination
- Error handling (critical for pipelines)
- Branching/merging logic (if applicable)

**What to avoid:**

- Too many stages (>6-7) - group related stages
- Vague labels ("Process", "Handle") - be specific about transformation
- Missing error handling - always show failure paths
- Unclear data format - label with types when relevant

## Real-World Example: Document Processing Pipeline

```mermaid
graph TD
    A[PDF Upload<br/>Multipart Form] -->|Extract| B[PDF Parser<br/>Text + Metadata]
    B -->|Split| C[Chunker<br/>Page-Level Chunks]
    C -->|Analyze| D[NLP Service<br/>Extract Entities]
    D -->|Enrich| E[Knowledge Graph<br/>Link Related Docs]
    E -->|Index| F[Search Index<br/>Elasticsearch]
    F -->|Complete| G[Processing Result<br/>Document ID + Stats]

    H[Error Queue<br/>Failed Uploads] -.->|Retry| A
    I[Audit Log] -.->|Record| B
    I -.->|Record| D
    I -.->|Record| F

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
    style H fill:#fbb,stroke:#333
```

**Caption:** This diagram shows how uploaded PDF documents flow through a processing pipeline. Documents are parsed, chunked, analyzed for entities, enriched with knowledge graph links, and indexed for search. Failed uploads go to an error queue for retry, and key stages are logged for audit.

## Related Templates

- **EXECUTION_SEQUENCE.md** - For showing detailed step-by-step execution (more granular)
- **COMPONENT_RELATIONSHIPS.md** - For showing how pipeline components integrate
- **HOOK_SYSTEM_FLOW.md** - For showing pipeline hooks/interceptors

## Anti-Patterns

**Too Generic:**

```
Input → Process → Output
```

(Not helpful - no context about transformations)

**Too Detailed:**

```
Read File → Open Buffer → Read Line 1 → Parse Line 1 → Validate Line 1 → Write Line 1 → Read Line 2 → ...
```

(Too granular - show batch operations, not per-item)

**Missing Error Handling:**

```
A → B → C → D
```

(What happens if B or C fails? Always show failure paths)

**Better:**

```
A → B → C → D
Error Handler -.->|Retry| B
Error Handler -.->|Retry| C
```

**Unclear Transformations:**

```
Data → Step 1 → Step 2 → Step 3 → Result
```

(What does each step do? Be specific)

**Better:**

```
Raw JSON → Parse → Validate Schema → Enrich with DB → Final JSON
```

## Complex Example: ETL Pipeline with Multiple Sources

```mermaid
graph TD
    A[Database<br/>PostgreSQL] -->|Extract| D[Data Lake<br/>Raw Storage]
    B[API<br/>REST Endpoints] -->|Extract| D
    C[Files<br/>S3 Bucket] -->|Extract| D

    D -->|Transform| E[Spark Job<br/>Clean + Normalize]
    E -->|Transform| F[Aggregator<br/>Calculate Metrics]
    F -->|Load| G[Data Warehouse<br/>Redshift]
    F -->|Load| H[Analytics DB<br/>TimescaleDB]

    I[Orchestrator<br/>Airflow DAG] -.->|Schedule| A
    I -.->|Schedule| B
    I -.->|Schedule| C

    J[Monitoring<br/>DataDog] -.->|Track| E
    J -.->|Track| F

    style A fill:#f9f,stroke:#333
    style B fill:#f9f,stroke:#333
    style C fill:#f9f,stroke:#333
    style D fill:#ff9,stroke:#333
    style E fill:#bbf,stroke:#333
    style F fill:#bbf,stroke:#333
    style G fill:#bfb,stroke:#333
    style H fill:#bfb,stroke:#333
```

**Caption:** Multi-source ETL pipeline showing data extraction from database, API, and files into a data lake, transformation with Spark and aggregation, then loading into both a data warehouse and analytics database. Airflow orchestrates the pipeline schedule, and DataDog monitors transformation stages.

## Advanced: Real-Time Stream Processing

```mermaid
graph LR
    A[Event Source<br/>IoT Devices] -->|Produce| B[Message Queue<br/>Kafka]
    B -->|Consume| C[Stream Processor<br/>Flink/Storm]
    C -->|Windowed Agg| D[Aggregator<br/>5-min Windows]
    D -->|Publish| E[Output Topic<br/>Aggregated Events]
    E -->|Subscribe| F[Alert Service]
    E -->|Subscribe| G[Dashboard]

    H[State Backend<br/>RocksDB] -.->|Checkpoint| C

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#ff9,stroke:#333
    style E fill:#bfb,stroke:#333,stroke-width:2px
    style H fill:#ddd,stroke:#333
```

**Caption:** Real-time stream processing showing IoT device events flowing through Kafka, processed with windowed aggregation in Flink, and published to an output topic consumed by alert service and dashboard. State backend provides checkpointing for fault tolerance.
