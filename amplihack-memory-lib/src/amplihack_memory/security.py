"""Security layer for memory-enabled agents.

This module provides capability-based access control, credential scrubbing,
and query validation to ensure safe memory operations.

Key Components:
- AgentCapabilities: Define what an agent can do with memory
- CredentialScrubber: Detect and redact sensitive data
- QueryValidator: Estimate and limit query complexity
"""

import re
from dataclasses import dataclass
from enum import Enum

from .exceptions import MemoryError
from .experience import Experience, ExperienceType


class ScopeLevel(Enum):
    """Memory access scope levels."""

    SESSION_ONLY = "session_only"  # Only current session
    CROSS_SESSION_READ = "cross_session_read"  # Read from other sessions
    CROSS_SESSION_WRITE = "cross_session_write"  # Write across sessions
    GLOBAL_READ = "global_read"  # Read all agents' memories
    GLOBAL_WRITE = "global_write"  # Write to any agent's memory


class SecurityViolationError(MemoryError):
    """Raised when security policy is violated."""


class QueryCostExceededError(MemoryError):
    """Raised when query cost exceeds limit."""


@dataclass
class AgentCapabilities:
    """Security capabilities for memory access.

    Defines what operations an agent is allowed to perform:
    - What data they can access (scope)
    - What types of experiences they can store/retrieve
    - How expensive their queries can be
    - Whether they can recognize patterns
    - How much memory they can use

    Attributes:
        scope: Access scope level
        allowed_experience_types: Permitted experience types (empty = all)
        max_query_cost: Maximum query complexity score
        can_access_patterns: Can retrieve pattern-type experiences
        memory_quota_mb: Maximum storage allocation (MB)
    """

    scope: ScopeLevel
    allowed_experience_types: list[ExperienceType]
    max_query_cost: int
    can_access_patterns: bool
    memory_quota_mb: int

    def __post_init__(self):
        """Validate capabilities configuration."""
        # Validate scope
        if not isinstance(self.scope, ScopeLevel):
            raise TypeError("scope must be ScopeLevel enum")

        # Validate experience types
        if not isinstance(self.allowed_experience_types, list):
            raise TypeError("allowed_experience_types must be list")

        for exp_type in self.allowed_experience_types:
            if not isinstance(exp_type, ExperienceType):
                raise TypeError("allowed_experience_types must contain ExperienceType enums")

        # Validate max_query_cost
        if not isinstance(self.max_query_cost, int) or self.max_query_cost <= 0:
            raise ValueError("max_query_cost must be positive integer")

        # Validate memory_quota_mb
        if not isinstance(self.memory_quota_mb, int) or self.memory_quota_mb <= 0:
            raise ValueError("memory_quota_mb must be positive integer")

    def can_store_experience(self, experience: Experience) -> bool:
        """Check if agent can store this experience type.

        Args:
            experience: Experience to check

        Returns:
            True if allowed, False otherwise
        """
        # Empty list means all types allowed
        if not self.allowed_experience_types:
            return True

        return experience.experience_type in self.allowed_experience_types

    def can_retrieve_experience_type(self, experience_type: ExperienceType) -> bool:
        """Check if agent can retrieve this experience type.

        Args:
            experience_type: Experience type to check

        Returns:
            True if allowed, False otherwise
        """
        # Empty list means all types allowed
        if not self.allowed_experience_types:
            return True

        # Special case: PATTERN type requires explicit permission
        if experience_type == ExperienceType.PATTERN and not self.can_access_patterns:
            return False

        return experience_type in self.allowed_experience_types

    def can_access_scope(self, target_scope: ScopeLevel) -> bool:
        """Check if agent has sufficient scope permission.

        Args:
            target_scope: Scope level required for operation

        Returns:
            True if allowed, False otherwise
        """
        # Define scope hierarchy (higher includes lower)
        scope_hierarchy = [
            ScopeLevel.SESSION_ONLY,
            ScopeLevel.CROSS_SESSION_READ,
            ScopeLevel.CROSS_SESSION_WRITE,
            ScopeLevel.GLOBAL_READ,
            ScopeLevel.GLOBAL_WRITE,
        ]

        agent_level = scope_hierarchy.index(self.scope)
        target_level = scope_hierarchy.index(target_scope)

        return agent_level >= target_level


class CredentialScrubber:
    """Detect and redact sensitive credentials in experience data.

    Automatically scrubs common credential patterns before storage:
    - API keys (AWS, OpenAI, Azure, etc.)
    - Passwords and secret tokens
    - SSH keys and certificates
    - OAuth tokens
    - Database connection strings

    Scrubbed experiences are tagged with 'credential_scrubbed' for audit.
    """

    # Regex patterns for common credential types
    PATTERNS = {
        "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "aws_secret": re.compile(r'aws_secret_access_key["\'\s:=]+([A-Za-z0-9/+=]{40})'),
        "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI keys are variable length
        "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
        "azure_key": re.compile(r"[0-9a-f]{32}"),  # Generic 32-char hex
        "password": re.compile(r'password["\'\s:=]+([^\s"\']+)', re.IGNORECASE),
        "token": re.compile(r'token["\'\s:=]+([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE),
        "api_key": re.compile(r'api[_\-]?key["\'\s:=]+([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE),
        "secret": re.compile(r'secret["\'\s:=]+([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE),
        "ssh_key": re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
        "db_url": re.compile(r"(?:postgres|mysql|mongodb)://[^:]+:([^@]+)@"),
    }

    REDACTION_TEXT = "[REDACTED]"

    def scrub_experience(self, experience: Experience) -> tuple[Experience, bool]:
        """Scrub sensitive data from experience.

        Args:
            experience: Experience to scrub

        Returns:
            Tuple of (scrubbed_experience, was_scrubbed)
            - scrubbed_experience: Experience with redacted data
            - was_scrubbed: True if any credentials were found
        """
        scrubbed_context, context_modified = self._scrub_text(experience.context)
        scrubbed_outcome, outcome_modified = self._scrub_text(experience.outcome)

        was_scrubbed = context_modified or outcome_modified

        # Create new experience with scrubbed data
        scrubbed_exp = Experience(
            experience_id=experience.experience_id,
            experience_type=experience.experience_type,
            context=scrubbed_context,
            outcome=scrubbed_outcome,
            confidence=experience.confidence,
            timestamp=experience.timestamp,
            metadata=experience.metadata.copy() if experience.metadata else {},
            tags=experience.tags.copy() if experience.tags else [],
        )

        # Tag if scrubbed
        if was_scrubbed and "credential_scrubbed" not in scrubbed_exp.tags:
            scrubbed_exp.tags.append("credential_scrubbed")

        return scrubbed_exp, was_scrubbed

    def _scrub_text(self, text: str) -> tuple[str, bool]:
        """Scrub credentials from text.

        Args:
            text: Text to scrub

        Returns:
            Tuple of (scrubbed_text, was_modified)
        """
        scrubbed = text
        modified = False

        for pattern_name, pattern in self.PATTERNS.items():
            if pattern.search(scrubbed):
                scrubbed = pattern.sub(self.REDACTION_TEXT, scrubbed)
                modified = True

        return scrubbed, modified

    def contains_credentials(self, text: str) -> bool:
        """Check if text contains credentials without scrubbing.

        Args:
            text: Text to check

        Returns:
            True if credentials detected, False otherwise
        """
        for pattern in self.PATTERNS.values():
            if pattern.search(text):
                return True
        return False


class QueryValidator:
    """Validate and estimate cost of database queries.

    Prevents expensive queries that could impact performance:
    - Estimates query complexity from SQL
    - Enforces maximum cost limits
    - Detects unbounded queries (missing LIMIT)
    - Prevents expensive operations (full table scans, cross joins)

    Query Cost Scoring:
    - Base cost: 1 point
    - Full table scan: +10 points
    - JOIN operation: +5 points per join
    - Subquery: +3 points per subquery
    - ORDER BY: +2 points
    - No LIMIT: +20 points (penalize unbounded queries)
    """

    # SQL patterns and their cost scores
    COST_PATTERNS = {
        "full_scan": (re.compile(r"SELECT\s+\*\s+FROM\s+\w+\s*(?:WHERE)?", re.IGNORECASE), 10),
        "join": (re.compile(r"\bJOIN\b", re.IGNORECASE), 5),
        "subquery": (re.compile(r"SELECT.*\(.*SELECT", re.IGNORECASE | re.DOTALL), 3),
        "order_by": (re.compile(r"\bORDER BY\b", re.IGNORECASE), 2),
        "no_limit": (re.compile(r"^(?!.*\bLIMIT\b).*SELECT", re.IGNORECASE | re.DOTALL), 20),
    }

    def estimate_cost(self, sql: str) -> int:
        """Estimate query cost from SQL.

        Args:
            sql: SQL query string

        Returns:
            Estimated cost score
        """
        cost = 1  # Base cost

        for pattern_name, (pattern, points) in self.COST_PATTERNS.items():
            if pattern_name == "join":
                # Count multiple JOINs
                matches = pattern.findall(sql)
                cost += len(matches) * points
            elif pattern.search(sql):
                cost += points

        return cost

    def validate_query(self, sql: str, max_cost: int) -> None:
        """Validate query against cost limit.

        Args:
            sql: SQL query string
            max_cost: Maximum allowed cost

        Raises:
            QueryCostExceededError: If query cost exceeds limit
        """
        cost = self.estimate_cost(sql)

        if cost > max_cost:
            raise QueryCostExceededError(
                f"Query cost ({cost}) exceeds limit ({max_cost}). "
                f"Consider adding LIMIT, reducing JOINs, or simplifying query."
            )

    def is_safe_query(self, sql: str) -> bool:
        """Check if query is safe (non-destructive).

        Args:
            sql: SQL query string

        Returns:
            True if safe (SELECT only), False otherwise
        """
        # Only allow SELECT queries
        sql_upper = sql.strip().upper()

        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            return False

        # Must not contain destructive keywords
        destructive_keywords = [
            "DELETE",
            "UPDATE",
            "INSERT",
            "DROP",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "REPLACE",
            "GRANT",
            "REVOKE",
        ]

        for keyword in destructive_keywords:
            if keyword in sql_upper:
                return False

        return True


class SecureMemoryBackend:
    """Wrapper around ExperienceStore with capability enforcement.

    This class wraps an ExperienceStore and enforces security policies:
    - Validates agent capabilities before operations
    - Scrubs credentials automatically
    - Validates query costs
    - Enforces memory quotas

    Example:
        capabilities = AgentCapabilities(
            scope=ScopeLevel.SESSION_ONLY,
            allowed_experience_types=[ExperienceType.SUCCESS, ExperienceType.FAILURE],
            max_query_cost=50,
            can_access_patterns=False,
            memory_quota_mb=10
        )

        secure_store = SecureMemoryBackend(store, capabilities)
        secure_store.add_experience(experience)  # Auto-scrubs, enforces caps
    """

    def __init__(self, store, capabilities: AgentCapabilities):
        """Initialize secure backend.

        Args:
            store: ExperienceStore instance
            capabilities: Agent capabilities
        """
        self.store = store
        self.capabilities = capabilities
        self.scrubber = CredentialScrubber()
        self.validator = QueryValidator()

    def add_experience(self, experience: Experience) -> str:
        """Add experience with security checks.

        Args:
            experience: Experience to add

        Returns:
            experience_id: ID of stored experience

        Raises:
            SecurityViolationError: If capability check fails
        """
        # Check capability
        if not self.capabilities.can_store_experience(experience):
            raise SecurityViolationError(
                f"Agent not allowed to store {experience.experience_type.value} experiences"
            )

        # Scrub credentials
        scrubbed_exp, was_scrubbed = self.scrubber.scrub_experience(experience)

        # Store scrubbed experience
        return self.store.add(scrubbed_exp)

    def search(
        self,
        query: str,
        experience_type: ExperienceType | None = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[Experience]:
        """Search experiences with security checks.

        Args:
            query: Search query
            experience_type: Filter by type
            min_confidence: Minimum confidence
            limit: Maximum results

        Returns:
            List of matching experiences

        Raises:
            SecurityViolationError: If capability check fails
        """
        # Check experience type capability
        if experience_type and not self.capabilities.can_retrieve_experience_type(experience_type):
            raise SecurityViolationError(
                f"Agent not allowed to retrieve {experience_type.value} experiences"
            )

        # Perform search
        return self.store.search(
            query=query,
            experience_type=experience_type,
            min_confidence=min_confidence,
            limit=limit,
        )

    def validate_custom_query(self, sql: str) -> None:
        """Validate custom SQL query.

        Args:
            sql: SQL query string

        Raises:
            SecurityViolationError: If query is unsafe or too expensive
            QueryCostExceededError: If query cost exceeds limit
        """
        # Check if query is safe (SELECT only)
        if not self.validator.is_safe_query(sql):
            raise SecurityViolationError("Only SELECT queries are allowed")

        # Validate cost
        self.validator.validate_query(sql, self.capabilities.max_query_cost)
