# Knowledge Module Design

## Overview

The Knowledge Module is responsible for synthesizing, storing, and querying knowledge from multiple document sources. It implements a sophisticated pipeline for document processing, graph construction, and information retrieval while maintaining source attribution and detecting contradictions.

## Requirements Coverage

This module addresses the following requirements:
- **SYN-*** : Synthesis pipeline requirements
- **KGO-*** : Knowledge graph operations requirements
- **MKS-*** : Multi-knowledge store requirements

## Module Structure

```
knowledge/
├── __init__.py           # Public API exports
├── synthesizer.py        # Document processing pipeline
├── graph.py             # Graph operations and queries
├── store.py             # Persistence layer (updated for multi-store)
├── registry.py          # Multi-store registry management
├── config.py            # Store configurations and mappings
├── agent_connector.py   # Agent-specific knowledge access
├── triage.py            # Document filtering and relevance
├── exporters/           # Export format handlers
│   ├── __init__.py
│   ├── json_exporter.py
│   ├── graphml_exporter.py
│   └── rdf_exporter.py
└── tests/               # Module tests
    ├── test_synthesizer.py
    ├── test_graph.py
    ├── test_store.py
    ├── test_registry.py
    └── test_multi_store.py
```

## Component Specifications

### Synthesizer Component

**Purpose**: Process documents and extract structured knowledge

**Class Design**:
```python
class KnowledgeSynthesizer:
    """Main document processing pipeline"""

    def __init__(self, config: SynthesizerConfig):
        self.triage = TriageEngine(config.triage_settings)
        self.extractors = self._load_extractors(config.extractors)
        self.integrator = Integrator()

    async def synthesize(
        self,
        documents: List[Document],
        query: Optional[str] = None
    ) -> KnowledgeGraph:
        """Process documents into knowledge graph"""

    async def synthesize_incremental(
        self,
        documents: List[Document],
        existing_graph: KnowledgeGraph
    ) -> KnowledgeGraph:
        """Update existing graph with new documents"""
```

**Key Methods**:
- `triage_documents()`: Filter and rank documents
- `extract_knowledge()`: Extract structured data
- `integrate_sources()`: Merge information from multiple sources
- `detect_conflicts()`: Identify contradictions

### Graph Component

**Purpose**: Manage graph operations and queries

**Class Design**:
```python
class KnowledgeGraph:
    """Graph data structure and operations"""

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[Edge] = []
        self.index = GraphIndex()

    def add_node(self, node: KnowledgeNode) -> None:
        """Add node with automatic indexing"""

    def find_paths(
        self,
        start: str,
        end: str,
        max_length: int = 5
    ) -> List[Path]:
        """Find paths between nodes"""

    def get_neighborhood(
        self,
        node_id: str,
        hops: int = 2
    ) -> Subgraph:
        """Extract subgraph around node"""

    def find_contradictions(self) -> List[Contradiction]:
        """Detect contradictory relationships"""
```

**Query Interface**:
```python
class GraphQuery:
    """Fluent query interface for graph"""

    def nodes(self) -> 'GraphQuery':
        """Start node query"""

    def edges(self) -> 'GraphQuery':
        """Start edge query"""

    def where(self, condition: Callable) -> 'GraphQuery':
        """Filter results"""

    def limit(self, n: int) -> 'GraphQuery':
        """Limit results"""

    def execute(self) -> QueryResult:
        """Execute query"""
```

### Store Component

**Purpose**: Persist and retrieve knowledge graphs

**Class Design**:
```python
class KnowledgeStore:
    """Persistence layer for knowledge graphs"""

    def __init__(self, storage_path: Path):
        self.path = storage_path
        self.metadata = self._load_metadata()

    async def save(
        self,
        graph: KnowledgeGraph,
        version: Optional[str] = None
    ) -> str:
        """Persist graph with versioning"""

    async def load(
        self,
        graph_id: str,
        version: Optional[str] = None
    ) -> KnowledgeGraph:
        """Load specific graph version"""

    async def query(
        self,
        query: str,
        limit: int = 10
    ) -> List[KnowledgeNode]:
        """Query across all stored graphs"""
```

**Storage Format**:
```json
{
    "metadata": {
        "id": "graph_123",
        "version": "v1.0",
        "created": "2024-01-20T10:00:00Z",
        "source_count": 5
    },
    "nodes": [
        {
            "id": "node_1",
            "type": "concept",
            "content": "...",
            "properties": {}
        }
    ],
    "edges": [
        {
            "source": "node_1",
            "target": "node_2",
            "predicate": "relates_to",
            "weight": 0.8
        }
    ]
}
```

### Triage Component

**Purpose**: Filter and rank documents by relevance

**Class Design**:
```python
class TriageEngine:
    """Document filtering and relevance scoring"""

    def __init__(self, config: TriageConfig):
        self.scorers = self._load_scorers(config)
        self.threshold = config.relevance_threshold

    async def triage(
        self,
        documents: List[Document],
        query: str
    ) -> List[RankedDocument]:
        """Filter and rank documents"""

    def score_relevance(
        self,
        document: Document,
        query: str
    ) -> float:
        """Calculate relevance score"""
```

**Scoring Methods**:
- Keyword matching
- Semantic similarity
- Metadata relevance
- Custom scoring rules

## Data Models

### Core Models

```python
@dataclass
class KnowledgeNode:
    """Node in knowledge graph"""
    id: str
    type: NodeType
    content: str
    properties: Dict[str, Any]
    source_ids: List[str]
    confidence: float
    created_at: datetime

@dataclass
class Edge:
    """Relationship between nodes"""
    source_id: str
    target_id: str
    predicate: str
    weight: float
    properties: Dict[str, Any]
    source_ids: List[str]

@dataclass
class Contradiction:
    """Detected contradiction in graph"""
    node_ids: List[str]
    edge_ids: List[str]
    description: str
    severity: float
    resolution_suggestions: List[str]
```

## Processing Pipeline

### Synthesis Flow

```
1. Document Input
   │
   ├─→ Triage
   │   ├─→ Relevance Scoring
   │   └─→ Filtering
   │
   ├─→ Extraction
   │   ├─→ Entity Extraction
   │   ├─→ Relationship Extraction
   │   └─→ Property Extraction
   │
   ├─→ Integration
   │   ├─→ Entity Resolution
   │   ├─→ Relationship Merging
   │   └─→ Conflict Detection
   │
   └─→ Graph Construction
       ├─→ Node Creation
       ├─→ Edge Creation
       └─→ Index Update
```

### Query Processing

```
1. Query Input
   │
   ├─→ Query Parsing
   │   ├─→ Intent Detection
   │   └─→ Parameter Extraction
   │
   ├─→ Index Lookup
   │   ├─→ Node Search
   │   └─→ Edge Search
   │
   ├─→ Graph Traversal
   │   ├─→ Path Finding
   │   └─→ Neighborhood Exploration
   │
   └─→ Result Ranking
       ├─→ Relevance Scoring
       └─→ Result Limiting
```

## Integration Points

### Event Emissions

```python
# Events emitted by this module
EVENTS = {
    'knowledge.document_triaged': {
        'document_id': str,
        'relevance_score': float,
        'passed': bool
    },
    'knowledge.synthesized': {
        'graph_id': str,
        'node_count': int,
        'edge_count': int,
        'source_count': int
    },
    'knowledge.contradiction_found': {
        'contradiction_id': str,
        'severity': float,
        'node_ids': List[str]
    },
    'knowledge.queried': {
        'query': str,
        'result_count': int,
        'execution_time': float
    }
}
```

### External Dependencies

- `models`: Shared data models
- `events`: Event bus for notifications
- No direct dependencies on other application modules

## Configuration

### Module Configuration

```yaml
knowledge:
  synthesis:
    batch_size: 100
    parallel_extractors: 4
    chunk_size: 1000  # tokens

  triage:
    relevance_threshold: 0.5
    keyword_weight: 0.3
    semantic_weight: 0.7

  storage:
    path: ./data/knowledge/
    version_retention: 10
    compression: true

  query:
    default_limit: 10
    max_limit: 1000
    timeout_seconds: 30

  export:
    formats: [json, graphml, rdf, gexf]
    max_export_size: 100MB
```

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: Process documents in configurable batches
2. **Parallel Extraction**: Run multiple extractors concurrently
3. **Index Caching**: Cache frequently accessed graph indices
4. **Incremental Updates**: Support partial graph updates
5. **Lazy Loading**: Load graph data on demand

### Scalability Limits

- Maximum nodes: 1M per graph
- Maximum edges: 10M per graph
- Query response time: < 500ms for 100K nodes
- Synthesis throughput: 100 documents/minute

## Testing Strategy

### Unit Tests

```python
class TestSynthesizer:
    """Test document synthesis"""

    def test_triage_filters_irrelevant_documents(self):
        """Verify triage removes low-relevance documents"""

    def test_synthesis_creates_valid_graph(self):
        """Verify graph structure after synthesis"""

    def test_incremental_update_preserves_existing(self):
        """Verify incremental updates don't lose data"""
```

### Integration Tests

```python
class TestKnowledgeIntegration:
    """Test module integration"""

    async def test_end_to_end_synthesis(self):
        """Test complete synthesis pipeline"""

    async def test_query_after_synthesis(self):
        """Test querying synthesized knowledge"""

    async def test_export_import_roundtrip(self):
        """Test export and re-import preserves data"""
```

## Error Handling

### Exception Hierarchy

```python
class KnowledgeException(Exception):
    """Base exception for knowledge module"""

class SynthesisException(KnowledgeException):
    """Synthesis pipeline errors"""

class GraphException(KnowledgeException):
    """Graph operation errors"""

class StorageException(KnowledgeException):
    """Storage operation errors"""

class QueryException(KnowledgeException):
    """Query processing errors"""
```

### Recovery Strategies

- **Partial Failures**: Continue processing valid documents
- **Storage Errors**: Retry with exponential backoff
- **Query Timeouts**: Return partial results with warning
- **Corruption Detection**: Validate and repair graph structure

## Security Considerations

### Input Validation
- Sanitize document content
- Validate query parameters
- Check file sizes and formats
- Rate limit API requests

### Access Control
- Graph-level permissions
- Query result filtering
- Export restrictions
- Audit logging

## Future Enhancements

### Planned Features
1. **Machine Learning Integration**: Smart entity resolution
2. **Real-time Updates**: WebSocket-based graph updates
3. **Distributed Processing**: Multi-node synthesis
4. **Advanced Analytics**: Graph neural networks
5. **Natural Language Queries**: LLM-powered query interface

### Extension Points
- Custom extractors via plugin system
- Additional export formats
- External graph database backends
- Custom scoring algorithms

## Module Contract

### Inputs
- Documents in various formats (text, markdown, JSON)
- Query strings for retrieval
- Configuration for processing

### Outputs
- Knowledge graphs with nodes and edges
- Query results ranked by relevance
- Export data in multiple formats
- Contradiction reports

### Side Effects
- Persists graphs to `./data/knowledge/`
- Emits events via event bus
- Logs operations and errors

### Guarantees
- Thread-safe operations
- Atomic graph updates
- Consistent persistence
- Graceful degradation on errors

## Multi-Store Capabilities (Enhanced)

### Overview

The Knowledge Module now supports multiple independent knowledge stores, enabling agents to maintain specialized domain expertise while sharing common knowledge. This enhancement maintains backward compatibility while adding powerful specialization capabilities.

### Store Registry Component

**Purpose**: Manage multiple knowledge stores and their lifecycle

**Class Design**:
```python
class KnowledgeStoreRegistry:
    """Central registry for all knowledge stores"""

    def __init__(self, config: RegistryConfig):
        self.stores: Dict[str, KnowledgeStore] = {}
        self.config = config
        self.default_store = "shared"
        self._initialize_default_stores()

    def get_store(self, name: str) -> KnowledgeStore:
        """Get or create a knowledge store"""
        if name not in self.stores:
            self.stores[name] = self._create_store(name)
        return self.stores[name]

    def create_store(
        self,
        name: str,
        config: StoreConfig
    ) -> KnowledgeStore:
        """Create a new specialized store"""

    def get_stores_for_agent(
        self,
        agent_name: str
    ) -> List[KnowledgeStore]:
        """Get all stores accessible to an agent"""

    def list_stores(self) -> List[str]:
        """List all available store names"""
```

### Agent Connector Component

**Purpose**: Simplify agent access to their knowledge domains

**Class Design**:
```python
class AgentKnowledgeConnector:
    """Agent-specific knowledge interface"""

    def __init__(
        self,
        agent_name: str,
        registry: KnowledgeStoreRegistry
    ):
        self.agent_name = agent_name
        self.registry = registry
        self.stores = self._load_agent_stores()
        self.primary_store = self._determine_primary_store()

    async def query(
        self,
        query: str,
        stores: Optional[List[str]] = None
    ) -> List[KnowledgeNode]:
        """Query across agent's knowledge stores"""

    async def add_knowledge(
        self,
        node: KnowledgeNode,
        store: Optional[str] = None
    ) -> None:
        """Add knowledge to appropriate store"""

    async def query_cross_domain(
        self,
        query: str
    ) -> Dict[str, List[KnowledgeNode]]:
        """Query all accessible stores with domain grouping"""
```

### Store Configuration Component

**Purpose**: Define store configurations and agent mappings

**Class Design**:
```python
@dataclass
class StoreConfig:
    """Configuration for a knowledge store"""
    name: str
    description: str
    persistence: bool = True
    vector_enabled: bool = True
    max_size_mb: int = 1000
    agents: List[str] = field(default_factory=list)
    shared: bool = False

class StoreConfigManager:
    """Manage store configurations"""

    DEFAULT_STORES = {
        "shared": StoreConfig(
            name="shared",
            description="Common knowledge for all agents",
            shared=True
        ),
        "architecture": StoreConfig(
            name="architecture",
            description="Design patterns and principles",
            agents=["zen-architect", "refactor-architect"]
        ),
        "security": StoreConfig(
            name="security",
            description="Security vulnerabilities and patterns",
            agents=["security-guardian"]
        ),
        "performance": StoreConfig(
            name="performance",
            description="Performance optimization patterns",
            agents=["performance-optimizer"]
        ),
        "bugs": StoreConfig(
            name="bugs",
            description="Common bug patterns and fixes",
            agents=["bug-hunter"]
        ),
        "testing": StoreConfig(
            name="testing",
            description="Test patterns and strategies",
            agents=["test-coverage"]
        )
    }
```

### Enhanced Store Component

**Purpose**: Update existing KnowledgeStore for multi-store support

**Modifications**:
```python
class KnowledgeStore:
    """Enhanced with store isolation"""

    def __init__(
        self,
        storage_path: Path,
        store_name: str = "default"  # New parameter
    ):
        self.store_name = store_name
        self.path = storage_path / "stores" / store_name
        self.path.mkdir(parents=True, exist_ok=True)
        self.metadata = self._load_metadata()
        self._init_indices()

    def _init_indices(self):
        """Initialize store-specific indices"""
        self.vector_index_path = self.path / "vectors"
        self.keyword_index_path = self.path / "keywords.idx"
        # Each store has isolated indices

    def clear_store(self) -> None:
        """Clear all data from this store"""
        # Safe clearing of single store
```

### Multi-Store Query Flow

```
1. Agent Query Request
   │
   ├─→ Identify Agent Stores
   │   ├─→ Primary Store
   │   └─→ Shared Stores
   │
   ├─→ Route to Stores
   │   ├─→ Parallel Queries
   │   └─→ Store Weights
   │
   ├─→ Aggregate Results
   │   ├─→ Deduplication
   │   └─→ Ranking
   │
   └─→ Return Unified Results
```

### Store Isolation Strategy

```
.data/knowledge/
├── stores/
│   ├── shared/           # Common knowledge
│   │   ├── entities.json
│   │   ├── relationships.json
│   │   └── vectors/
│   ├── architecture/      # Architecture expertise
│   │   ├── entities.json
│   │   ├── relationships.json
│   │   └── vectors/
│   ├── security/          # Security expertise
│   │   └── ...
│   └── performance/       # Performance expertise
│       └── ...
├── registry.json          # Store registry metadata
└── config.json           # Store configurations
```

### Agent Usage Patterns

```python
# Simple agent usage
class ZenArchitectAgent:
    def __init__(self):
        # Automatically gets architecture + shared stores
        self.knowledge = AgentKnowledgeConnector("zen-architect")

    async def analyze(self, code):
        # Query architecture patterns
        patterns = await self.knowledge.query("design patterns")

        # Add new learning to architecture store
        await self.knowledge.add_knowledge(
            KnowledgeNode("new_pattern", data)
        )

        # Query across all accessible stores
        all_info = await self.knowledge.query_cross_domain("SOLID")
```

### Migration Path

```python
class MigrationManager:
    """Migrate from single to multi-store"""

    async def migrate_to_multi_store(self):
        # 1. Create shared store
        shared_store = registry.create_store("shared", shared_config)

        # 2. Copy existing knowledge
        await self.copy_existing_knowledge(shared_store)

        # 3. Create specialized stores
        for store_name, config in DEFAULT_STORES.items():
            registry.create_store(store_name, config)

        # 4. Maintain backward compatibility
        # Old API calls default to shared store
```

### Performance Optimizations

1. **Store-Level Caching**: Each store maintains its own cache
2. **Lazy Store Loading**: Stores loaded only when accessed
3. **Parallel Query Execution**: Multi-store queries run concurrently
4. **Index Partitioning**: Indices partitioned by store
5. **Selective Store Activation**: Only active stores kept in memory

### Configuration Example

```yaml
knowledge:
  multi_store:
    enabled: true
    default_store: "shared"

  stores:
    shared:
      persistence: true
      max_size_mb: 5000
      vector_enabled: true

    architecture:
      agents: ["zen-architect", "refactor-architect"]
      max_size_mb: 1000

    security:
      agents: ["security-guardian"]
      max_size_mb: 500
      auto_update: true  # Pull OWASP updates

  agent_mappings:
    zen-architect:
      primary: "architecture"
      additional: ["shared"]

    bug-hunter:
      primary: "bugs"
      additional: ["shared", "testing"]
```

### Backward Compatibility

- Single-store APIs continue to work (route to shared store)
- Existing persistence format preserved
- Optional multi-store activation via configuration
- Gradual migration path available