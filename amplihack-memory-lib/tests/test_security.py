"""Tests for security layer components.

Test coverage:
- AgentCapabilities: Initialization, validation, permission checks
- CredentialScrubber: Pattern detection, scrubbing, tagging
- QueryValidator: Cost estimation, validation, safety checks
- SecureMemoryBackend: Integrated security enforcement
"""

import pytest
from amplihack_memory.experience import Experience, ExperienceType
from amplihack_memory.security import (
    AgentCapabilities,
    CredentialScrubber,
    QueryCostExceededError,
    QueryValidator,
    ScopeLevel,
    SecureMemoryBackend,
    SecurityViolationError,
)
from amplihack_memory.store import ExperienceStore

# =============================================================================
# AgentCapabilities Tests
# =============================================================================


class TestAgentCapabilitiesInitialization:
    """Test AgentCapabilities initialization and validation."""

    def test_creates_with_valid_params(self):
        """Test creating capabilities with valid parameters."""
        caps = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[ExperienceType.SUCCESS],
            max_query_cost=100,
            can_access_patterns=False,
            memory_quota_mb=10,
        )

        assert caps.scope == ScopeLevel.SESSION_ONLY
        assert caps.allowed_experience_types == [ExperienceType.SUCCESS]
        assert caps.max_query_cost == 100
        assert caps.can_access_patterns is False
        assert caps.memory_quota_mb == 10

    def test_creates_with_empty_experience_types(self):
        """Test that empty experience types list means all allowed."""
        caps = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[],
            max_query_cost=100,
            can_access_patterns=True,
            memory_quota_mb=10,
        )

        assert caps.allowed_experience_types == []

    def test_rejects_invalid_scope_type(self):
        """Test that invalid scope type raises TypeError."""
        with pytest.raises(TypeError, match="scope must be ScopeLevel enum"):
            AgentCapabilities(
                scope="invalid",
                allowed_experience_types=[],
                max_query_cost=100,
                can_access_patterns=False,
                memory_quota_mb=10,
            )

    def test_rejects_non_list_experience_types(self):
        """Test that non-list experience types raises TypeError."""
        with pytest.raises(TypeError, match="allowed_experience_types must be list"):
            AgentCapabilities(
                scope=ScopeLevel.SESSION_ONLY,
                allowed_experience_types=ExperienceType.SUCCESS,
                max_query_cost=100,
                can_access_patterns=False,
                memory_quota_mb=10,
            )

    def test_rejects_invalid_experience_type_in_list(self):
        """Test that invalid items in experience types raises TypeError."""
        with pytest.raises(
            TypeError, match="allowed_experience_types must contain ExperienceType enums"
        ):
            AgentCapabilities(
                scope=ScopeLevel.SESSION_ONLY,
                allowed_experience_types=["invalid"],
                max_query_cost=100,
                can_access_patterns=False,
                memory_quota_mb=10,
            )

    def test_rejects_non_positive_query_cost(self):
        """Test that non-positive query cost raises ValueError."""
        with pytest.raises(ValueError, match="max_query_cost must be positive integer"):
            AgentCapabilities(
                scope=ScopeLevel.SESSION_ONLY,
                allowed_experience_types=[],
                max_query_cost=0,
                can_access_patterns=False,
                memory_quota_mb=10,
            )

    def test_rejects_non_positive_memory_quota(self):
        """Test that non-positive memory quota raises ValueError."""
        with pytest.raises(ValueError, match="memory_quota_mb must be positive integer"):
            AgentCapabilities(
                scope=ScopeLevel.SESSION_ONLY,
                allowed_experience_types=[],
                max_query_cost=100,
                can_access_patterns=False,
                memory_quota_mb=-5,
            )


class TestAgentCapabilitiesPermissions:
    """Test AgentCapabilities permission checking."""

    @pytest.fixture
    def restricted_caps(self):
        """Create restricted capabilities."""
        return AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[ExperienceType.SUCCESS, ExperienceType.FAILURE],
            max_query_cost=50,
            can_access_patterns=False,
            memory_quota_mb=10,
        )

    @pytest.fixture
    def permissive_caps(self):
        """Create permissive capabilities."""
        return AgentCapabilities(
            scope=ScopeLevel.GLOBAL_WRITE,
            allowed_experience_types=[],  # All allowed
            max_query_cost=1000,
            can_access_patterns=True,
            memory_quota_mb=100,
        )

    def test_allows_storing_permitted_experience_type(self, restricted_caps):
        """Test that agent can store permitted experience types."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="test",
            outcome="test",
            confidence=0.8,
        )

        assert restricted_caps.can_store_experience(exp) is True

    def test_blocks_storing_unpermitted_experience_type(self, restricted_caps):
        """Test that agent cannot store unpermitted experience types."""
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="test",
            outcome="test",
            confidence=0.8,
        )

        assert restricted_caps.can_store_experience(exp) is False

    def test_allows_all_types_when_list_empty(self, permissive_caps):
        """Test that empty list allows all experience types."""
        for exp_type in ExperienceType:
            exp = Experience(
                experience_type=exp_type,
                context="test",
                outcome="test",
                confidence=0.8,
            )
            assert permissive_caps.can_store_experience(exp) is True

    def test_allows_retrieving_permitted_type(self, restricted_caps):
        """Test that agent can retrieve permitted experience types."""
        assert restricted_caps.can_retrieve_experience_type(ExperienceType.SUCCESS) is True
        assert restricted_caps.can_retrieve_experience_type(ExperienceType.FAILURE) is True

    def test_blocks_retrieving_patterns_without_permission(self, restricted_caps):
        """Test that PATTERN type requires explicit permission."""
        assert restricted_caps.can_access_patterns is False
        assert restricted_caps.can_retrieve_experience_type(ExperienceType.PATTERN) is False

    def test_allows_retrieving_patterns_with_permission(self, permissive_caps):
        """Test that agent with pattern permission can retrieve patterns."""
        assert permissive_caps.can_access_patterns is True
        assert permissive_caps.can_retrieve_experience_type(ExperienceType.PATTERN) is True

    def test_scope_hierarchy_session_only(self, restricted_caps):
        """Test SESSION_ONLY scope has lowest permissions."""
        assert restricted_caps.can_access_scope(ScopeLevel.SESSION_ONLY) is True
        assert restricted_caps.can_access_scope(ScopeLevel.CROSS_SESSION_READ) is False
        assert restricted_caps.can_access_scope(ScopeLevel.GLOBAL_WRITE) is False

    def test_scope_hierarchy_global_write(self, permissive_caps):
        """Test GLOBAL_WRITE scope has highest permissions."""
        assert permissive_caps.can_access_scope(ScopeLevel.SESSION_ONLY) is True
        assert permissive_caps.can_access_scope(ScopeLevel.CROSS_SESSION_READ) is True
        assert permissive_caps.can_access_scope(ScopeLevel.GLOBAL_WRITE) is True


# =============================================================================
# CredentialScrubber Tests
# =============================================================================


class TestCredentialScrubberDetection:
    """Test CredentialScrubber pattern detection."""

    @pytest.fixture
    def scrubber(self):
        """Create scrubber instance."""
        return CredentialScrubber()

    def test_detects_aws_access_key(self, scrubber):
        """Test detection of AWS access keys."""
        text = "My key is AKIAIOSFODNN7EXAMPLE"
        assert scrubber.contains_credentials(text) is True

    def test_detects_openai_key(self, scrubber):
        """Test detection of OpenAI API keys."""
        text = "OpenAI key: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH"
        assert scrubber.contains_credentials(text) is True

    def test_detects_github_token(self, scrubber):
        """Test detection of GitHub tokens."""
        text = "Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        assert scrubber.contains_credentials(text) is True

    def test_detects_password(self, scrubber):
        """Test detection of passwords."""
        text = "password: mysecretpass123"
        assert scrubber.contains_credentials(text) is True

    def test_detects_api_key(self, scrubber):
        """Test detection of generic API keys."""
        text = "api_key: abc123xyz789"
        assert scrubber.contains_credentials(text) is True

    def test_detects_ssh_key(self, scrubber):
        """Test detection of SSH private keys."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ..."
        assert scrubber.contains_credentials(text) is True

    def test_detects_database_url(self, scrubber):
        """Test detection of database URLs with passwords."""
        text = "postgres://user:secretpass@localhost:5432/db"
        assert scrubber.contains_credentials(text) is True

    def test_ignores_clean_text(self, scrubber):
        """Test that clean text is not flagged."""
        text = "This is a normal log message with no credentials"
        assert scrubber.contains_credentials(text) is False


class TestCredentialScrubberScrubbing:
    """Test CredentialScrubber scrubbing functionality."""

    @pytest.fixture
    def scrubber(self):
        """Create scrubber instance."""
        return CredentialScrubber()

    @pytest.fixture
    def sample_experience(self):
        """Create sample experience."""
        return Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Connected to API",
            outcome="Successfully authenticated",
            confidence=0.9,
        )

    def test_scrubs_aws_key_in_context(self, scrubber, sample_experience):
        """Test scrubbing AWS key from context."""
        sample_experience.context = "Used key AKIAIOSFODNN7EXAMPLE to connect"
        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert was_modified is True
        assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed.context
        assert "[REDACTED]" in scrubbed.context

    def test_scrubs_password_in_outcome(self, scrubber, sample_experience):
        """Test scrubbing password from outcome."""
        sample_experience.outcome = "Logged in with password: secret123"
        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert was_modified is True
        assert "secret123" not in scrubbed.outcome
        assert "[REDACTED]" in scrubbed.outcome

    def test_tags_scrubbed_experience(self, scrubber, sample_experience):
        """Test that scrubbed experiences are tagged."""
        sample_experience.context = "API key: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH"
        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert was_modified is True
        assert "credential_scrubbed" in scrubbed.tags

    def test_preserves_clean_experience(self, scrubber, sample_experience):
        """Test that clean experiences are not modified."""
        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert was_modified is False
        assert scrubbed.context == sample_experience.context
        assert scrubbed.outcome == sample_experience.outcome
        assert "credential_scrubbed" not in scrubbed.tags

    def test_scrubs_multiple_patterns(self, scrubber, sample_experience):
        """Test scrubbing multiple credential types."""
        sample_experience.context = (
            "AWS key AKIAIOSFODNN7EXAMPLE and OpenAI sk-1234567890abcdefghijklmnop"
        )
        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert was_modified is True
        assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed.context
        assert "sk-1234567890abcdefghijklmnop" not in scrubbed.context
        assert scrubbed.context.count("[REDACTED]") == 2

    def test_preserves_experience_metadata(self, scrubber, sample_experience):
        """Test that scrubbing preserves other experience fields."""
        sample_experience.metadata = {"test": "value"}
        sample_experience.tags = ["existing_tag"]
        sample_experience.context = "password: secret"

        scrubbed, was_modified = scrubber.scrub_experience(sample_experience)

        assert scrubbed.experience_id == sample_experience.experience_id
        assert scrubbed.experience_type == sample_experience.experience_type
        assert scrubbed.confidence == sample_experience.confidence
        assert scrubbed.metadata == sample_experience.metadata
        assert "existing_tag" in scrubbed.tags


# =============================================================================
# QueryValidator Tests
# =============================================================================


class TestQueryValidatorCostEstimation:
    """Test QueryValidator cost estimation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return QueryValidator()

    def test_estimates_simple_query_low_cost(self, validator):
        """Test that simple SELECT with LIMIT has low cost."""
        sql = "SELECT * FROM experiences LIMIT 10"
        cost = validator.estimate_cost(sql)
        assert cost < 20  # Base + full_scan + no unbounded penalty

    def test_estimates_no_limit_high_cost(self, validator):
        """Test that query without LIMIT has high cost."""
        sql = "SELECT * FROM experiences"
        cost = validator.estimate_cost(sql)
        assert cost >= 20  # Should include no_limit penalty

    def test_counts_multiple_joins(self, validator):
        """Test that multiple JOINs increase cost."""
        sql = """
            SELECT * FROM experiences e
            JOIN table1 t1 ON e.id = t1.id
            JOIN table2 t2 ON e.id = t2.id
            LIMIT 10
        """
        cost = validator.estimate_cost(sql)
        # Should include cost for 2 JOINs (5 points each)
        assert cost >= 10

    def test_detects_subquery_cost(self, validator):
        """Test that subqueries increase cost."""
        sql = """
            SELECT * FROM experiences
            WHERE id IN (SELECT id FROM other_table)
            LIMIT 10
        """
        cost = validator.estimate_cost(sql)
        assert cost >= 3  # Should include subquery cost

    def test_detects_order_by_cost(self, validator):
        """Test that ORDER BY increases cost."""
        sql = "SELECT * FROM experiences ORDER BY timestamp DESC LIMIT 10"
        cost = validator.estimate_cost(sql)
        assert cost >= 2  # Should include ORDER BY cost


class TestQueryValidatorValidation:
    """Test QueryValidator validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return QueryValidator()

    def test_accepts_cheap_query(self, validator):
        """Test that cheap queries pass validation."""
        sql = "SELECT * FROM experiences LIMIT 10"
        validator.validate_query(sql, max_cost=50)  # Should not raise

    def test_rejects_expensive_query(self, validator):
        """Test that expensive queries fail validation."""
        sql = "SELECT * FROM experiences"  # No LIMIT = expensive
        with pytest.raises(QueryCostExceededError, match="Query cost .* exceeds limit"):
            validator.validate_query(sql, max_cost=10)

    def test_accepts_query_at_limit(self, validator):
        """Test that query at exactly the limit passes."""
        sql = "SELECT * FROM experiences LIMIT 10"
        cost = validator.estimate_cost(sql)
        validator.validate_query(sql, max_cost=cost)  # Should not raise

    def test_error_message_includes_cost(self, validator):
        """Test that error message includes actual and max cost."""
        sql = "SELECT * FROM experiences"
        try:
            validator.validate_query(sql, max_cost=5)
        except QueryCostExceededError as e:
            assert "exceeds limit" in str(e)
            assert "(5)" in str(e)


class TestQueryValidatorSafety:
    """Test QueryValidator safety checks."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return QueryValidator()

    def test_allows_select_query(self, validator):
        """Test that SELECT queries are safe."""
        assert validator.is_safe_query("SELECT * FROM experiences") is True

    def test_blocks_delete_query(self, validator):
        """Test that DELETE queries are unsafe."""
        assert validator.is_safe_query("DELETE FROM experiences") is False

    def test_blocks_update_query(self, validator):
        """Test that UPDATE queries are unsafe."""
        assert validator.is_safe_query("UPDATE experiences SET confidence = 1.0") is False

    def test_blocks_insert_query(self, validator):
        """Test that INSERT queries are unsafe."""
        assert validator.is_safe_query("INSERT INTO experiences VALUES (...)") is False

    def test_blocks_drop_query(self, validator):
        """Test that DROP queries are unsafe."""
        assert validator.is_safe_query("DROP TABLE experiences") is False

    def test_blocks_create_query(self, validator):
        """Test that CREATE queries are unsafe."""
        assert validator.is_safe_query("CREATE TABLE new_table (...)") is False

    def test_case_insensitive_safety_check(self, validator):
        """Test that safety check is case insensitive."""
        assert validator.is_safe_query("select * from experiences") is True
        assert validator.is_safe_query("delete from experiences") is False


# =============================================================================
# SecureMemoryBackend Integration Tests
# =============================================================================


class TestSecureMemoryBackendStorage:
    """Test SecureMemoryBackend storage operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create test store."""
        return ExperienceStore(
            agent_name="test_agent",
            storage_path=tmp_path / "memory",
        )

    @pytest.fixture
    def restricted_backend(self, store):
        """Create restricted secure backend."""
        caps = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[ExperienceType.SUCCESS],
            max_query_cost=50,
            can_access_patterns=False,
            memory_quota_mb=10,
        )
        return SecureMemoryBackend(store, caps)

    def test_stores_permitted_experience(self, restricted_backend):
        """Test that permitted experiences can be stored."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="test context",
            outcome="test outcome",
            confidence=0.8,
        )

        exp_id = restricted_backend.add_experience(exp)
        assert exp_id is not None

    def test_blocks_unpermitted_experience(self, restricted_backend):
        """Test that unpermitted experiences are blocked."""
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="test context",
            outcome="test outcome",
            confidence=0.8,
        )

        with pytest.raises(SecurityViolationError, match="not allowed to store"):
            restricted_backend.add_experience(exp)

    def test_auto_scrubs_credentials(self, restricted_backend, store):
        """Test that credentials are automatically scrubbed."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Used API key: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH",
            outcome="Successfully connected",
            confidence=0.8,
        )

        _ = restricted_backend.add_experience(exp)

        # Retrieve and verify scrubbing
        stored_list = store.connector.retrieve_experiences(limit=1)
        assert len(stored_list) > 0
        stored = stored_list[0]
        assert "sk-1234567890" not in stored.context
        assert "[REDACTED]" in stored.context
        assert "credential_scrubbed" in stored.tags


class TestSecureMemoryBackendRetrieval:
    """Test SecureMemoryBackend retrieval operations."""

    @pytest.fixture
    def store_with_data(self, tmp_path):
        """Create store with sample data."""
        store = ExperienceStore(
            agent_name="test_agent",
            storage_path=tmp_path / "memory",
        )

        # Add sample experiences
        for i in range(3):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"context {i}",
                    outcome=f"outcome {i}",
                    confidence=0.8,
                )
            )

        return store

    @pytest.fixture
    def restricted_backend(self, store_with_data):
        """Create restricted backend."""
        caps = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[ExperienceType.SUCCESS],
            max_query_cost=50,
            can_access_patterns=False,
            memory_quota_mb=10,
        )
        return SecureMemoryBackend(store_with_data, caps)

    def test_searches_permitted_experiences(self, restricted_backend):
        """Test searching for permitted experience types."""
        results = restricted_backend.search(
            query="context",
            experience_type=ExperienceType.SUCCESS,
        )

        assert len(results) > 0
        assert all(exp.experience_type == ExperienceType.SUCCESS for exp in results)

    def test_blocks_unpermitted_experience_type_search(self, restricted_backend):
        """Test that searching for unpermitted types fails."""
        with pytest.raises(SecurityViolationError, match="not allowed to retrieve"):
            restricted_backend.search(
                query="test",
                experience_type=ExperienceType.PATTERN,
            )


class TestSecureMemoryBackendQueryValidation:
    """Test SecureMemoryBackend custom query validation."""

    @pytest.fixture
    def backend(self, tmp_path):
        """Create backend."""
        store = ExperienceStore(
            agent_name="test_agent",
            storage_path=tmp_path / "memory",
        )
        caps = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[],
            max_query_cost=20,
            can_access_patterns=True,
            memory_quota_mb=10,
        )
        return SecureMemoryBackend(store, caps)

    def test_validates_safe_query(self, backend):
        """Test that safe queries are allowed."""
        sql = "SELECT * FROM experiences LIMIT 10"
        backend.validate_custom_query(sql)  # Should not raise

    def test_blocks_unsafe_query(self, backend):
        """Test that unsafe queries are blocked."""
        sql = "DELETE FROM experiences"
        with pytest.raises(SecurityViolationError, match="Only SELECT queries"):
            backend.validate_custom_query(sql)

    def test_blocks_expensive_query(self, backend):
        """Test that expensive queries are blocked."""
        sql = "SELECT * FROM experiences"  # No LIMIT = expensive
        with pytest.raises(QueryCostExceededError):
            backend.validate_custom_query(sql)
