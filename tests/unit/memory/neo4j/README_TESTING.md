# Neo4j Memory System Test Strategy

## Overview

This document describes the comprehensive testing strategy for the Neo4j memory system foundation. All tests follow **Test-Driven Development (TDD)** principles: tests are written FIRST and should FAIL until implementation is complete.

## Testing Pyramid

We follow the testing pyramid principle with the following distribution:

- **60% Unit Tests**: Fast, isolated, mocked dependencies
- **30% Integration Tests**: Real Neo4j container, testcontainers
- **10% E2E Tests**: Full session startup flow

## Test Organization

```
tests/
├── unit/memory/neo4j/
│   ├── conftest.py                      # Unit test fixtures
│   ├── test_container_manager.py        # Container lifecycle tests
│   ├── test_schema_manager.py           # Schema initialization tests
│   └── test_dependency_agent.py         # Dependency checking tests
└── integration/memory/neo4j/
    ├── conftest.py                      # Integration test fixtures
    ├── test_neo4j_foundation_e2e.py     # End-to-end workflow tests
    └── test_container_lifecycle.py      # Container lifecycle integration
```

## Test Categories

### 1. Unit Tests (`tests/unit/memory/neo4j/`)

**Purpose**: Test individual components in isolation without external dependencies.

**Characteristics**:
- No real Docker required (all mocked)
- No real Neo4j required (all mocked)
- Fast execution (< 100ms per test)
- High coverage of edge cases and error handling

**Test Files**:

#### `test_container_manager.py`
Tests for Neo4j container lifecycle management:
- ✅ `test_WHEN_start_container_called_THEN_docker_compose_up_executed`
- ✅ `test_WHEN_container_already_running_THEN_start_is_idempotent`
- ✅ `test_WHEN_docker_not_available_THEN_appropriate_error_raised`
- ✅ `test_WHEN_stop_container_called_THEN_docker_compose_down_executed`
- ✅ `test_WHEN_container_healthy_THEN_health_check_returns_true`
- ✅ `test_WHEN_health_check_times_out_THEN_returns_false`
- ✅ `test_WHEN_container_running_THEN_status_returns_running`
- ✅ `test_WHEN_wait_for_ready_times_out_THEN_returns_false`

**Total**: 20+ tests covering startup, shutdown, health checks, and status monitoring.

#### `test_schema_manager.py`
Tests for Neo4j schema initialization:
- ✅ `test_WHEN_initialize_schema_called_THEN_constraints_created`
- ✅ `test_WHEN_initialize_schema_called_twice_THEN_no_errors` (idempotency)
- ✅ `test_WHEN_create_agent_type_constraint_THEN_unique_id_enforced`
- ✅ `test_WHEN_schema_valid_THEN_verify_returns_true`
- ✅ `test_WHEN_constraints_missing_THEN_verify_returns_false`
- ✅ `test_WHEN_seed_agent_types_THEN_core_types_created`

**Total**: 25+ tests covering constraints, indexes, verification, and agent types.

#### `test_dependency_agent.py`
Tests for goal-seeking dependency agent:
- ✅ `test_WHEN_docker_installed_and_running_THEN_check_passes`
- ✅ `test_WHEN_docker_not_installed_THEN_check_fails_with_guidance`
- ✅ `test_WHEN_docker_compose_v2_available_THEN_check_passes`
- ✅ `test_WHEN_neo4j_package_installed_THEN_check_passes`
- ✅ `test_WHEN_ports_available_THEN_check_passes`
- ✅ `test_WHEN_all_prerequisites_met_THEN_report_success`
- ✅ `test_WHEN_get_remediation_for_docker_THEN_returns_install_steps`

**Total**: 30+ tests covering all prerequisite checks and remediation guidance.

### 2. Integration Tests (`tests/integration/memory/neo4j/`)

**Purpose**: Test components working together with real Neo4j instances.

**Characteristics**:
- Requires Docker daemon
- Uses testcontainers or real Neo4j
- Slower execution (< 30 seconds per test)
- Tests real database operations

**Test Files**:

#### `test_neo4j_foundation_e2e.py`
End-to-end workflow tests:
- ✅ `test_WHEN_session_starts_THEN_neo4j_container_starts_automatically`
- ✅ `test_WHEN_neo4j_ready_THEN_can_connect_successfully`
- ✅ `test_WHEN_schema_initialized_THEN_constraints_exist`
- ✅ `test_WHEN_neo4j_ready_THEN_can_create_and_retrieve_node` (smoke test)
- ✅ `test_WHEN_docker_unavailable_THEN_session_starts_with_warning` (fallback)
- ✅ `test_WHEN_session_starts_THEN_completes_within_500ms` (performance)

**Total**: 15+ tests covering full startup flow and basic operations.

#### `test_container_lifecycle.py`
Container lifecycle integration tests:
- ✅ `test_WHEN_container_started_THEN_status_is_running`
- ✅ `test_WHEN_container_restarted_THEN_becomes_running_again`
- ✅ `test_WHEN_data_created_and_container_stopped_THEN_data_persists_on_restart`
- ✅ `test_WHEN_container_stopped_THEN_ports_released`
- ✅ `test_WHEN_concurrent_sessions_start_THEN_no_race_conditions`

**Total**: 15+ tests covering start/stop cycles and data persistence.

## Running Tests

### Run All Tests
```bash
pytest tests/unit/memory/neo4j/ tests/integration/memory/neo4j/
```

### Run Only Unit Tests (Fast)
```bash
pytest tests/unit/memory/neo4j/ -m unit
```

### Run Only Integration Tests (Requires Docker)
```bash
pytest tests/integration/memory/neo4j/ -m integration
```

### Run Specific Test File
```bash
pytest tests/unit/memory/neo4j/test_container_manager.py -v
```

### Run Tests Matching Pattern
```bash
pytest -k "docker" -v  # Run all Docker-related tests
pytest -k "schema" -v  # Run all schema tests
```

### Skip Slow Tests
```bash
pytest -m "not slow"
```

### Run with Coverage
```bash
pytest --cov=amplihack.memory.neo4j tests/unit/memory/neo4j/
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.unit`: Fast unit tests with mocked dependencies
- `@pytest.mark.integration`: Integration tests requiring Docker
- `@pytest.mark.e2e`: End-to-end tests (full workflow)
- `@pytest.mark.slow`: Tests taking > 5 seconds
- `@pytest.mark.performance`: Performance benchmark tests
- `@pytest.mark.requires_docker`: Explicitly requires Docker daemon

## Test Fixtures

### Unit Test Fixtures (`tests/unit/memory/neo4j/conftest.py`)

**Mock Docker**:
- `mock_docker_client`: Mock Docker client for container operations
- `mock_docker_subprocess`: Mock subprocess calls for Docker commands
- `mock_docker_available`: Mock Docker as available
- `mock_docker_not_available`: Mock Docker as unavailable

**Mock Neo4j**:
- `mock_neo4j_connector`: Mock Neo4j connector
- `mock_neo4j_driver`: Mock Neo4j driver (low-level)

**Configuration**:
- `neo4j_config`: Test configuration dictionary
- `docker_compose_file`: Temporary docker-compose file

**Test Data**:
- `sample_agent_types`: Sample agent type data
- `sample_memory_nodes`: Sample memory node data
- `sample_cypher_queries`: Sample Cypher queries

**Helpers**:
- `assert_cypher_valid`: Validate Cypher query syntax
- `assert_docker_command_safe`: Validate Docker command safety

### Integration Test Fixtures (`tests/integration/memory/neo4j/conftest.py`)

**Real Containers**:
- `neo4j_test_container`: Session-scoped Neo4j container (testcontainers)
- `running_neo4j_container`: Running container for tests
- `container_manager`: ContainerManager instance

**Connections**:
- `neo4j_connector`: Connected Neo4j connector
- `clean_neo4j_db`: Neo4j with clean database (cleanup before/after)

**Components**:
- `schema_manager`: SchemaManager instance
- `initialized_schema`: Neo4j with initialized schema
- `dependency_agent`: DependencyAgent instance

**Performance**:
- `performance_benchmark`: Helper for timing operations

**Cleanup**:
- `cleanup_test_containers`: Auto-cleanup test containers
- `cleanup_test_volumes`: Auto-cleanup test volumes

## Test Naming Convention

Tests follow the pattern: `test_WHEN_<condition>_THEN_<expected_outcome>`

**Examples**:
- `test_WHEN_container_started_THEN_status_is_running`
- `test_WHEN_docker_not_available_THEN_appropriate_error_raised`
- `test_WHEN_schema_initialized_THEN_constraints_exist`

This makes test intent crystal clear and improves readability.

## Mocking Strategy

### Unit Tests: Full Mocking
- **Docker operations**: Mock `subprocess.run` for all Docker commands
- **Neo4j operations**: Mock connector, driver, and query execution
- **File system**: Mock file I/O when needed
- **Network**: Mock port checks with `socket.socket`

### Integration Tests: Minimal Mocking
- **Use real Docker**: Via testcontainers or local Docker daemon
- **Use real Neo4j**: Running in container
- **Real database operations**: Actual Cypher queries
- **Mock only external systems**: External APIs, file systems outside test scope

## Test Isolation

### Unit Tests
- Each test is completely isolated
- No shared state between tests
- All external dependencies mocked
- Tests can run in any order
- Tests can run in parallel

### Integration Tests
- Tests share Neo4j container (session-scoped)
- Database cleaned between tests (`clean_neo4j_db` fixture)
- Tests use unique IDs to avoid collisions
- Tests clean up created resources

## Expected Test Results (TDD)

**ALL TESTS SHOULD FAIL INITIALLY** because the implementation doesn't exist yet.

### Expected Failures

1. **Import Errors**: Modules not yet created
   ```
   ImportError: cannot import name 'ContainerManager' from 'amplihack.memory.neo4j.container_manager'
   ```

2. **Module Not Found**: Files not created
   ```
   ModuleNotFoundError: No module named 'amplihack.memory.neo4j'
   ```

3. **Attribute Errors**: Methods not implemented
   ```
   AttributeError: 'ContainerManager' object has no attribute 'start_container'
   ```

### Making Tests Pass

As implementation progresses, tests should transition from:
1. ❌ **Import Error** → ✅ **File/class created**
2. ❌ **Attribute Error** → ✅ **Method implemented**
3. ❌ **Assertion Error** → ✅ **Correct behavior implemented**
4. ❌ **Mock not called** → ✅ **Integration working**

## Performance Requirements

Tests validate performance requirements from `IMPLEMENTATION_REQUIREMENTS.md`:

### Session Start Time
```python
@pytest.mark.performance
def test_WHEN_session_starts_THEN_completes_within_500ms():
    # Validates: Session start < 500ms (non-blocking)
    assert duration_ms < 500
```

### Container Start Time
```python
@pytest.mark.performance
def test_WHEN_container_starts_THEN_ready_within_30_seconds():
    # Validates: Container ready < 30 seconds
    assert duration < 30
```

### Query Performance
```python
@pytest.mark.performance
def test_WHEN_query_executed_THEN_completes_within_100ms():
    # Validates: Basic query < 100ms
    assert duration_ms < 100
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Neo4j Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/unit/memory/neo4j/ -m unit

  integration-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration/memory/neo4j/ -m integration
```

### Pre-commit Hook

```bash
#!/bin/bash
# Run fast unit tests before commit
pytest tests/unit/memory/neo4j/ -m unit --maxfail=1
```

## Coverage Goals

- **Unit Tests**: 90%+ coverage of core logic
- **Integration Tests**: 80%+ coverage of integration points
- **Combined**: 85%+ total coverage

### Measuring Coverage

```bash
pytest --cov=amplihack.memory.neo4j \
       --cov-report=html \
       --cov-report=term-missing \
       tests/unit/memory/neo4j/ tests/integration/memory/neo4j/
```

## Troubleshooting Tests

### Test Failures

**Import errors**:
```bash
# Expected during TDD - implementation not yet created
# Solution: Create the missing module/class
```

**Docker not available**:
```bash
# Integration tests require Docker
pytest -m "not integration"  # Skip integration tests
```

**Port conflicts**:
```bash
# Neo4j ports already in use
docker ps  # Check for existing containers
docker stop amplihack-neo4j  # Stop if needed
```

**Testcontainers issues**:
```bash
# Install testcontainers
pip install testcontainers
# Or skip tests requiring it
pytest -k "not container"
```

### Debugging Tests

**Verbose output**:
```bash
pytest -v -s tests/unit/memory/neo4j/test_container_manager.py
```

**Show print statements**:
```bash
pytest -s tests/unit/memory/neo4j/
```

**Debug specific test**:
```bash
pytest --pdb tests/unit/memory/neo4j/test_container_manager.py::TestClass::test_method
```

**See all fixtures**:
```bash
pytest --fixtures tests/unit/memory/neo4j/
```

## Best Practices

### 1. Test One Thing Per Test
```python
# Good: Tests one specific behavior
def test_WHEN_container_started_THEN_status_is_running():
    assert manager.get_status() == ContainerStatus.RUNNING

# Bad: Tests multiple unrelated things
def test_container_operations():
    manager.start_container()
    assert manager.get_status() == ContainerStatus.RUNNING
    manager.stop_container()
    assert manager.get_status() == ContainerStatus.STOPPED
```

### 2. Use Descriptive Test Names
```python
# Good: Intent is clear
def test_WHEN_docker_not_installed_THEN_check_fails_with_guidance()

# Bad: Vague
def test_docker_check()
```

### 3. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange: Set up test conditions
    manager = ContainerManager()

    # Act: Perform the action
    result = manager.start_container()

    # Assert: Verify the outcome
    assert result is True
```

### 4. Clean Up Resources
```python
@pytest.fixture
def resource():
    resource = create_resource()
    yield resource
    cleanup_resource(resource)  # Always cleanup
```

### 5. Mock External Dependencies
```python
# Good: Mock external Docker calls
with patch('subprocess.run') as mock_run:
    manager.start_container()

# Bad: Call real Docker (in unit tests)
manager.start_container()  # Actually starts Docker
```

## Next Steps

After tests are written and failing (TDD):

1. **Create module structure**: `src/amplihack/memory/neo4j/__init__.py`
2. **Implement ContainerManager**: Make container tests pass
3. **Implement SchemaManager**: Make schema tests pass
4. **Implement DependencyAgent**: Make dependency tests pass
5. **Integration**: Make E2E tests pass
6. **Iterate**: Fix any failing tests
7. **Coverage**: Ensure 85%+ coverage

## Summary

This comprehensive test suite provides:

✅ **80+ tests** covering all foundation functionality
✅ **TDD approach** - tests written FIRST
✅ **Testing pyramid** - 60% unit, 30% integration, 10% E2E
✅ **Clear fixtures** - Reusable test setup
✅ **Performance validation** - Meets all requirements
✅ **CI/CD ready** - Can run in automated pipelines
✅ **Well documented** - Clear testing strategy

All tests WILL FAIL initially - that's the point of TDD!
