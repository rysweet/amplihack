"""Shared test fixtures for memory system tests.

This module provides reusable fixtures for all memory-related tests.
Follows pytest best practices for fixture organization.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from amplihack.memory.models import MemoryEntry, MemoryType

# =============================================================================
# Mock Backend Fixtures
# =============================================================================


@pytest.fixture
def mock_backend():
    """Mock memory backend for unit tests.

    Provides a fully mocked backend interface with sensible defaults.
    All methods return success values unless configured otherwise.
    """
    backend = MagicMock()

    # Store method returns memory ID
    backend.store.return_value = "mock_memory_id"

    # Query method returns empty list by default
    backend.query.return_value = []

    # Delete method returns success
    backend.delete.return_value = True
    backend.delete_by_query.return_value = 0

    # Initialize/close methods succeed
    backend.initialize.return_value = None
    backend.close.return_value = None

    return backend


@pytest.fixture
def mock_storage_pipeline():
    """Mock storage pipeline for testing coordinator."""
    pipeline = MagicMock()
    pipeline.process.return_value = MagicMock(
        success=True, memory_id="pipeline_mem_id", execution_time_ms=50
    )
    return pipeline


@pytest.fixture
def mock_retrieval_pipeline():
    """Mock retrieval pipeline for testing coordinator."""
    pipeline = MagicMock()
    pipeline.query.return_value = MagicMock(success=True, memories=[], execution_time_ms=25)
    return pipeline


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_memory_entry():
    """Sample memory entry for testing.

    Returns a valid MemoryEntry with all required fields populated.
    """
    return MemoryEntry(
        id="mem_test_001",
        session_id="sess_test",
        agent_id="test_agent",
        memory_type=MemoryType.EPISODIC,
        title="Test Memory",
        content="Sample content for testing",
        metadata={"test": True},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=5,
    )


@pytest.fixture
def sample_episodic_memory():
    """Sample episodic memory (conversation event)."""
    return MemoryEntry(
        id="episodic_001",
        session_id="sess_episodic",
        agent_id="architect",
        memory_type=MemoryType.EPISODIC,
        title="Discussion about authentication",
        content="User asked about JWT vs session-based auth. Explained trade-offs.",
        metadata={"topic": "security", "user_question": True},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=7,
    )


@pytest.fixture
def sample_semantic_memory():
    """Sample semantic memory (knowledge fact)."""
    return MemoryEntry(
        id="semantic_001",
        session_id="sess_semantic",
        agent_id="knowledge_base",
        memory_type=MemoryType.SEMANTIC,
        title="JWT authentication best practices",
        content="JWTs should use HS256 or RS256. Always validate expiration.",
        metadata={"category": "security", "verified": True},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=9,
    )


@pytest.fixture
def sample_procedural_memory():
    """Sample procedural memory (how-to knowledge)."""
    return MemoryEntry(
        id="procedural_001",
        session_id="sess_procedural",
        agent_id="builder",
        memory_type=MemoryType.PROCEDURAL,
        title="How to fix import errors",
        content=(
            "1. Check requirements.txt for missing dependencies\n"
            "2. Verify PYTHONPATH includes project root\n"
            "3. Restart IDE to clear cache\n"
            "4. Run pip install -e . to reinstall in dev mode"
        ),
        metadata={"success_rate": 0.95, "times_used": 12},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=8,
    )


@pytest.fixture
def sample_working_memory():
    """Sample working memory (temporary context)."""
    from datetime import timedelta

    return MemoryEntry(
        id="working_001",
        session_id="sess_working",
        agent_id="builder",
        memory_type=MemoryType.WORKING,
        title="Current task context",
        content="Implementing authentication endpoint. Step 3 of 5: JWT validation",
        metadata={"task_id": "task_auth_123", "step": 3, "total_steps": 5},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=5,
        expires_at=datetime.now() + timedelta(hours=1),
    )


@pytest.fixture
def sample_prospective_memory():
    """Sample prospective memory (future reminder)."""
    return MemoryEntry(
        id="prospective_001",
        session_id="sess_prospective",
        agent_id="planner",
        memory_type=MemoryType.PROSPECTIVE,
        title="TODO: Update documentation",
        content="After auth implementation, update API docs with new endpoints",
        metadata={"task_type": "documentation", "priority": "medium"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=6,
    )


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path for integration tests."""
    db_path = tmp_path / "test_memory.db"
    return db_path


@pytest.fixture
def temp_kuzu_db_path(tmp_path):
    """Temporary Kùzu database path for integration tests."""
    db_path = tmp_path / "test_kuzu_db"
    db_path.mkdir(exist_ok=True)
    return db_path


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_codebase(tmp_path):
    """Create sample codebase for testing.

    Returns a Path to a temporary directory with sample code files.
    """
    codebase_path = tmp_path / "sample_codebase"
    codebase_path.mkdir()

    # Create singleton pattern example
    (codebase_path / "singleton.py").write_text("""
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        pass
""")

    # Create factory pattern example
    (codebase_path / "factory.py").write_text("""
class ShapeFactory:
    def create_shape(self, shape_type):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
        return None

class Circle:
    def draw(self):
        pass

class Square:
    def draw(self):
        pass
""")

    # Create observer pattern example
    (codebase_path / "observer.py").write_text("""
class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def notify(self):
        for observer in self._observers:
            observer.update()

class Observer:
    def update(self):
        pass
""")

    return codebase_path


@pytest.fixture
def sample_documents(tmp_path):
    """Create sample documentation files for testing."""
    docs_path = tmp_path / "documents"
    docs_path.mkdir()

    # Azure authentication docs
    (docs_path / "azure_auth.md").write_text("""
# Azure Authentication

Azure supports multiple authentication mechanisms:
- Azure Active Directory (AAD)
- Managed Identities
- Service Principals
- OAuth 2.0 / OpenID Connect

## Best Practices
1. Use managed identities when possible
2. Implement token caching
3. Handle token refresh gracefully
""")

    # Azure RBAC docs
    (docs_path / "azure_rbac.md").write_text("""
# Azure Role-Based Access Control (RBAC)

RBAC provides fine-grained access management.

## Key Concepts
- Roles: Collections of permissions
- Assignments: Linking roles to principals
- Scopes: Resources where access applies

## Common Roles
- Owner: Full access
- Contributor: Manage resources but not access
- Reader: View-only access
""")

    # Azure Storage docs
    (docs_path / "azure_storage.md").write_text("""
# Azure Storage

Azure Storage provides scalable cloud storage.

## Services
- Blob Storage: Object storage
- Queue Storage: Message queuing
- Table Storage: NoSQL data
- File Storage: SMB file shares

## Security
- Storage Account Keys
- Shared Access Signatures (SAS)
- Azure AD integration
""")

    return docs_path


# =============================================================================
# Agent Test Fixtures
# =============================================================================


@pytest.fixture
def mock_doc_analyzer():
    """Mock document analyzer agent."""
    agent = MagicMock()
    agent.analyze.return_value = MagicMock(
        summary="Document summary",
        key_concepts=["concept1", "concept2"],
        processing_time=1000,
        quality_score=85,
    )
    return agent


@pytest.fixture
def mock_pattern_recognizer():
    """Mock pattern recognizer agent."""
    agent = MagicMock()
    agent.find_patterns.return_value = MagicMock(
        patterns_found=["Singleton", "Factory"],
        confidence_scores={"Singleton": 0.95, "Factory": 0.88},
        analysis_time=2000,
    )
    return agent


@pytest.fixture
def mock_bug_predictor():
    """Mock bug predictor agent."""
    agent = MagicMock()
    agent.predict_bugs.return_value = MagicMock(
        predicted_bugs=[
            {"type": "sql_injection", "confidence": 0.9, "line": 42},
            {"type": "null_pointer", "confidence": 0.75, "line": 56},
        ],
        analysis_time=1500,
    )
    return agent


@pytest.fixture
def mock_performance_optimizer():
    """Mock performance optimizer agent."""
    agent = MagicMock()
    agent.optimize.return_value = MagicMock(
        suggested_changes="Add database index on user_id column",
        expected_improvement_pct=80,
        confidence_score=0.85,
        analysis_time=1200,
    )
    return agent


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed_ms = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            if self.start_time is None:
                raise RuntimeError("Timer not started")
            end_time = time.perf_counter()
            self.elapsed_ms = (end_time - self.start_time) * 1000
            return self.elapsed_ms

        def assert_under(self, max_ms: float):
            """Assert operation completed under max_ms."""
            if self.elapsed_ms is None:
                raise RuntimeError("Timer not stopped")
            assert self.elapsed_ms < max_ms, (
                f"Operation took {self.elapsed_ms:.2f}ms, exceeds limit of {max_ms}ms"
            )

    return Timer()


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (requires database)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full system)")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "agent_learning: Agent learning validation tests")
    config.addinivalue_line("markers", "slow: Tests that take >5 seconds")


# =============================================================================
# Helper Functions
# =============================================================================


def create_mock_memory(
    memory_id: str,
    session_id: str,
    memory_type: MemoryType = MemoryType.EPISODIC,
    importance: int = 5,
    content: str = "Test content",
    agent_id: str = "test_agent",
) -> MemoryEntry:
    """Create a mock memory entry for testing.

    Args:
        memory_id: Unique identifier
        session_id: Session identifier
        memory_type: Type of memory
        importance: Importance score (1-10)
        content: Memory content
        agent_id: Agent identifier

    Returns:
        MemoryEntry: Configured memory entry
    """
    return MemoryEntry(
        id=memory_id,
        session_id=session_id,
        agent_id=agent_id,
        memory_type=memory_type,
        title=f"Test Memory {memory_id}",
        content=content,
        metadata={},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=importance,
    )


def load_sample_doc(filename: str, docs_path: Path) -> str:
    """Load sample documentation for testing.

    Args:
        filename: Name of the document file
        docs_path: Path to documents directory

    Returns:
        str: Document content
    """
    doc_file = docs_path / filename
    if not doc_file.exists():
        raise FileNotFoundError(f"Sample document not found: {filename}")
    return doc_file.read_text()
