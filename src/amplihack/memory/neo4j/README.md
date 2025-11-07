# Neo4j Code Ingestion Metadata Tracking

This module provides functionality for tracking code ingestion metadata in Neo4j, including codebase identity, ingestion timestamps, and audit trails.

## Overview

The code ingestion tracker solves the problem of identifying when a codebase has been indexed and whether a new ingestion represents a new codebase or an update to an existing one.

### Core Concepts

- **Codebase Identity**: Unique identification of a codebase based on Git remote URL and branch
- **Ingestion Metadata**: Timestamp and commit SHA of when code was ingested
- **Audit Trail**: Historical record of all ingestions with SUPERSEDED_BY relationships

### Decision Logic

The tracker uses the following logic:

1. **Same unique_key** (repo + branch) → **UPDATE**
   - Increment ingestion counter
   - Create new Ingestion node
   - Link to previous ingestion via SUPERSEDED_BY

2. **Different unique_key** → **NEW**
   - Create Codebase node
   - Create Ingestion node
   - Link via INGESTION_OF relationship

## Module Structure

```
neo4j/
├── __init__.py              # Public API exports
├── models.py                # Data models (CodebaseIdentity, IngestionMetadata, IngestionResult)
├── identifier.py            # Extract codebase identity from Git
├── neo4j_schema.py         # Schema initialization and management
├── query_builder.py        # Secure Cypher query construction
├── ingestion_tracker.py    # Main tracking logic
└── README.md               # This file
```

## Usage

### Basic Usage

```python
from pathlib import Path
from neo4j import GraphDatabase
from amplihack.memory.neo4j import IngestionTracker

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

# Create tracker
tracker = IngestionTracker(driver)

# Track ingestion from Git repository
repo_path = Path("/path/to/repo")
result = tracker.track_ingestion(repo_path)

if result.is_new():
    print(f"New codebase tracked: {result.codebase_identity.unique_key}")
elif result.is_update():
    print(f"Updated codebase: counter={result.ingestion_metadata.ingestion_counter}")
elif result.is_error():
    print(f"Error: {result.error_message}")

# Get ingestion history
history = tracker.get_ingestion_history(result.codebase_identity.unique_key)
for record in history:
    print(f"Ingestion {record['ingestion_counter']}: {record['timestamp']}")

# Clean up
tracker.close()
```

### Context Manager

```python
with IngestionTracker(driver) as tracker:
    result = tracker.track_ingestion(repo_path)
    # tracker.close() called automatically
```

### Manual Identity Creation

```python
from amplihack.memory.neo4j import CodebaseIdentifier

# Create identity without Git access
identity = CodebaseIdentifier.create_manual_identity(
    remote_url="https://github.com/org/repo.git",
    branch="main",
    commit_sha="a" * 40,
)

result = tracker.track_manual_ingestion(identity)
```

### Custom Metadata

```python
# Add custom metadata to ingestion
metadata = {
    "source": "cli",
    "user": "admin",
    "environment": "production"
}

result = tracker.track_ingestion(repo_path, metadata=metadata)
```

## Neo4j Schema

### Nodes

**Codebase**
- `unique_key` (string, unique): SHA-256 hash of remote_url + branch
- `remote_url` (string): Normalized Git remote URL
- `branch` (string): Branch name
- `commit_sha` (string): Current commit SHA
- `created_at` (datetime): When first tracked
- `updated_at` (datetime): When last updated
- `ingestion_count` (integer): Number of times ingested

**Ingestion**
- `ingestion_id` (string, unique): UUID for this ingestion
- `timestamp` (datetime): When ingestion occurred
- `commit_sha` (string): Commit SHA at ingestion time
- `ingestion_counter` (integer): Sequential counter for this codebase

### Relationships

- `(Ingestion)-[:INGESTION_OF]->(Codebase)`: Links ingestion to its codebase
- `(Ingestion)-[:SUPERSEDED_BY]->(Ingestion)`: Audit trail of ingestions
- `(Codebase)-[:FROM_CODEBASE]->(Ingestion)`: Implicit via INGESTION_OF

### Constraints

- `codebase_unique_key`: Ensures Codebase.unique_key is unique
- `ingestion_id`: Ensures Ingestion.ingestion_id is unique

### Indexes

- `codebase_remote_url`: Fast lookups by repository URL
- `codebase_branch`: Fast lookups by branch
- `ingestion_timestamp`: Temporal queries
- `ingestion_commit_sha`: Commit-based queries

## Security

### Parameterized Queries

All queries use parameter binding to prevent Cypher injection:

```python
# Safe - uses parameters
query = "MATCH (c:Codebase {unique_key: $unique_key}) RETURN c"
session.run(query, unique_key=user_input)

# Unsafe - string concatenation (NOT used)
query = f"MATCH (c:Codebase {{unique_key: '{user_input}'}}) RETURN c"
```

### Query Validation

The `QueryBuilder.validate_query_params()` method checks for dangerous patterns:

```python
params = {"key": "MATCH (n) DELETE n"}
QueryBuilder.validate_query_params(params)  # Returns False
```

### URL Normalization

Remote URLs are normalized to remove authentication:

```python
# Input: https://user:pass@github.com/org/repo.git
# Output: https://github.com/org/repo.git
```

## Data Models

### CodebaseIdentity

Represents a codebase with stable identification:

```python
@dataclass
class CodebaseIdentity:
    remote_url: str       # Normalized Git URL
    branch: str           # Branch name
    commit_sha: str       # Current commit (40-char hex)
    unique_key: str       # SHA-256 hash (64-char hex)
    metadata: Dict[str, str]  # Additional metadata
```

### IngestionMetadata

Tracks a single ingestion operation:

```python
@dataclass
class IngestionMetadata:
    ingestion_id: str     # UUID
    timestamp: datetime   # When ingestion occurred
    commit_sha: str       # Commit at ingestion time
    ingestion_counter: int  # Sequential counter (>= 1)
    metadata: Dict[str, str]  # Additional metadata
```

### IngestionResult

Result of tracking operation:

```python
@dataclass
class IngestionResult:
    status: IngestionStatus  # NEW, UPDATE, or ERROR
    codebase_identity: CodebaseIdentity
    ingestion_metadata: IngestionMetadata
    previous_ingestion_id: Optional[str]  # If UPDATE
    error_message: Optional[str]  # If ERROR
```

## Testing

### Running Tests

```bash
# Set Neo4j connection
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

# Run all tests
pytest tests/neo4j/

# Run with coverage
pytest tests/neo4j/ --cov=amplihack.memory.neo4j --cov-report=term-missing
```

### Test Organization

- `test_models.py`: Data model validation
- `test_identifier.py`: Git extraction and normalization
- `test_schema.py`: Schema initialization and constraints
- `test_query_builder.py`: Query construction and security
- `test_ingestion_tracker.py`: End-to-end tracking logic

### Coverage Target

The test suite maintains >85% coverage following the 60/30/10 pyramid:
- 60% unit tests (models, identifier, query builder)
- 30% integration tests (schema, tracker)
- 10% end-to-end tests (full tracking workflows)

## Examples

### Example 1: First Ingestion

```python
# First time indexing a codebase
result = tracker.track_ingestion(Path("/path/to/repo"))

assert result.is_new()
assert result.ingestion_metadata.ingestion_counter == 1
assert result.previous_ingestion_id is None
```

### Example 2: Subsequent Ingestion

```python
# Second time indexing the same codebase
result = tracker.track_ingestion(Path("/path/to/repo"))

assert result.is_update()
assert result.ingestion_metadata.ingestion_counter == 2
assert result.previous_ingestion_id is not None
```

### Example 3: Different Branch

```python
# Different branch = different codebase
result_main = tracker.track_ingestion(main_branch_path)
result_dev = tracker.track_ingestion(dev_branch_path)

assert result_main.is_new()
assert result_dev.is_new()
assert result_main.codebase_identity.unique_key != result_dev.codebase_identity.unique_key
```

### Example 4: Error Handling

```python
# Invalid path
result = tracker.track_ingestion(Path("/nonexistent"))

assert result.is_error()
assert result.error_message is not None
print(f"Error: {result.error_message}")
```

## Performance

### Query Performance

All queries are optimized with proper indexes:
- Codebase lookups by unique_key: O(1) with constraint index
- Latest ingestion query: O(log n) with timestamp index
- History queries: O(n) where n = number of ingestions for codebase

### Transaction Safety

Operations use Neo4j transactions for ACID guarantees:
- New codebase: Single transaction creates both nodes and relationship
- Update: Single transaction updates codebase and creates ingestion
- Rollback on failure

## Troubleshooting

### Connection Issues

```python
from neo4j.exceptions import ServiceUnavailable

try:
    tracker = IngestionTracker(driver)
except ServiceUnavailable:
    print("Neo4j is not running or not accessible")
```

### Schema Issues

```python
# Verify schema is initialized
if not tracker.schema.verify_schema():
    tracker.schema.initialize_schema()
```

### Clearing Test Data

```python
# WARNING: Deletes all data
tracker.schema.clear_all_data()
```

## Integration

### With Existing Memory System

```python
from amplihack.memory.manager import MemoryManager
from amplihack.memory.neo4j import IngestionTracker

# Use alongside existing SQLite memory
memory = MemoryManager()
ingestion_tracker = IngestionTracker(neo4j_driver)

# Track ingestion before indexing
result = ingestion_tracker.track_ingestion(repo_path)
if result.is_new():
    # First time - do full indexing
    memory.index_codebase(repo_path)
elif result.is_update():
    # Update - do incremental indexing
    memory.update_codebase(repo_path)
```

## Future Enhancements

Possible future additions:
- Query by commit SHA to find which ingestion indexed specific commit
- Query by timestamp range to find ingestions in time window
- Support for multiple remotes per repository
- Ingestion metadata tags for categorization
- Performance metrics tracking per ingestion

## References

- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Constraints](https://neo4j.com/docs/cypher-manual/current/constraints/)
- [Issue #1181](https://github.com/amplihack/repo/issues/1181)
