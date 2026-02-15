# Memory System Security Architecture

**Document Type**: Architecture Design
**Created**: 2026-02-14
**Status**: Design Specification
**Related**: Memory System (coordinator.py, backends/, models.py)

## Executive Summary

This document specifies a comprehensive security architecture for the amplihack memory-enabled goal-seeking agent system. The design prioritizes **ruthless simplicity** with **defense in depth**, implementing capability-based access control, credential protection, memory isolation, and query security without requiring enterprise authentication infrastructure.

**Key Principles:**

- Capability-based access control (not role-based)
- Fail-secure defaults (deny by default)
- Session-based isolation with controlled cross-session sharing
- <10% performance overhead
- Transparent to agent logic (middleware pattern)

## Current State Analysis

### Existing Architecture

The memory system consists of:

1. **MemoryCoordinator**: Main interface (coordinator.py)
   - Storage pipeline with quality review
   - Retrieval with token budget enforcement
   - Session isolation via session_id field

2. **Backend Layer**: Protocol-based storage (backends/base.py)
   - SQLiteBackend: Local file storage
   - KuzuBackend: Graph database with code context
   - Capability flags system exists but underutilized

3. **Memory Types**: 5 psychological types (types.py)
   - Episodic, Semantic, Procedural, Prospective, Working
   - Different sensitivity levels (Working = high, Semantic = medium)

### Security Gaps Identified

**CRITICAL VULNERABILITIES:**

1. **No Access Control** (models.py line 158-196)
   - MemoryQuery validation exists for SQL injection
   - But no capability checking before query execution
   - Any agent can query any memory type

2. **No Credential Protection** (coordinator.py)
   - Content stored as-is without scrubbing
   - No detection of API keys, tokens, passwords
   - No tagging of sensitive memories

3. **Weak Memory Isolation** (coordinator.py line 342-383)
   - Session isolation exists but easily bypassed
   - `clear_all()` validates session but other methods don't enforce
   - Cross-agent leakage possible via semantic search

4. **Query Cost Attacks** (coordinator.py line 214-306)
   - Token budget exists but after query execution
   - No pre-execution cost estimation
   - Cypher queries in KuzuBackend have no complexity limits

## Security Architecture Design

### 1. Capability-Based Access Control

#### 1.1 AgentCapabilities Class

```python
# File: src/amplihack/memory/security/capabilities.py

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from ..types import MemoryType


class ScopeLevel(Enum):
    """Memory access scope levels."""

    SESSION_ONLY = "session"          # Current session only
    CROSS_SESSION_READ = "cross_read" # Read from other sessions
    CROSS_SESSION_WRITE = "cross_write" # Write to other sessions
    GLOBAL = "global"                 # Read/write across all sessions


@dataclass(frozen=True)
class AgentCapabilities:
    """Defines what operations an agent can perform.

    Immutable capability set assigned at agent creation.
    Uses whitelist approach - only explicit capabilities granted.

    Example:
        # Basic agent (session-scoped)
        caps = AgentCapabilities(
            agent_id="builder-001",
            scope=ScopeLevel.SESSION_ONLY,
            allowed_memory_types=[MemoryType.WORKING, MemoryType.EPISODIC],
            max_query_complexity=100,
        )

        # Privileged agent (cross-session read)
        caps = AgentCapabilities(
            agent_id="semantic-learner-001",
            scope=ScopeLevel.CROSS_SESSION_READ,
            allowed_memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
            max_query_complexity=500,
            file_path_patterns=["src/**/*.py"],  # Code files only
        )
    """

    agent_id: str
    scope: ScopeLevel
    allowed_memory_types: list[MemoryType]

    # Query limits
    max_query_complexity: int = 100  # Query cost units
    max_results: int = 100
    max_token_budget: int = 8000

    # File path restrictions (for code context queries)
    file_path_patterns: list[str] = field(default_factory=lambda: ["**/*"])

    # Credential access (requires explicit grant)
    can_access_credentials: bool = False

    # Administrative operations
    can_clear_memories: bool = False
    can_delete_memories: bool = False

    def __post_init__(self):
        """Validate capability configuration."""
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if self.max_query_complexity < 1:
            raise ValueError("max_query_complexity must be positive")

        if self.max_results < 1 or self.max_results > 10000:
            raise ValueError("max_results must be 1-10000")

        if not self.allowed_memory_types:
            raise ValueError("allowed_memory_types cannot be empty")

    def can_query_memory_type(self, memory_type: MemoryType) -> bool:
        """Check if agent can query this memory type."""
        return memory_type in self.allowed_memory_types

    def can_access_session(self, current_session: str, target_session: str) -> bool:
        """Check if agent can access target session."""
        if current_session == target_session:
            return True  # Always allow same-session

        if self.scope == ScopeLevel.SESSION_ONLY:
            return False

        if self.scope in [ScopeLevel.CROSS_SESSION_READ, ScopeLevel.CROSS_SESSION_WRITE, ScopeLevel.GLOBAL]:
            return True

        return False

    def can_write_to_session(self, current_session: str, target_session: str) -> bool:
        """Check if agent can write to target session."""
        if current_session == target_session:
            return True  # Always allow same-session writes

        if self.scope in [ScopeLevel.CROSS_SESSION_WRITE, ScopeLevel.GLOBAL]:
            return True

        return False

    def matches_file_pattern(self, file_path: str) -> bool:
        """Check if file path matches allowed patterns."""
        from fnmatch import fnmatch

        file_path_obj = Path(file_path)

        for pattern in self.file_path_patterns:
            if fnmatch(str(file_path_obj), pattern):
                return True

        return False


# Predefined capability profiles for common agent types
DEFAULT_AGENT_CAPABILITIES = AgentCapabilities(
    agent_id="default",
    scope=ScopeLevel.SESSION_ONLY,
    allowed_memory_types=[MemoryType.EPISODIC, MemoryType.WORKING],
    max_query_complexity=100,
)

SEMANTIC_LEARNER_CAPABILITIES = AgentCapabilities(
    agent_id="semantic-learner",
    scope=ScopeLevel.CROSS_SESSION_READ,
    allowed_memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
    max_query_complexity=500,
)

ADMIN_CAPABILITIES = AgentCapabilities(
    agent_id="admin",
    scope=ScopeLevel.GLOBAL,
    allowed_memory_types=list(MemoryType),
    max_query_complexity=1000,
    can_clear_memories=True,
    can_delete_memories=True,
)
```

#### 1.2 Capability Enforcement

```python
# File: src/amplihack/memory/security/enforcer.py

from typing import Optional

from ..models import MemoryQuery
from .capabilities import AgentCapabilities, ScopeLevel


class SecurityViolation(Exception):
    """Raised when security policy is violated."""
    pass


class CapabilityEnforcer:
    """Enforces capability-based access control.

    Middleware that checks every operation against agent capabilities.
    Fail-secure: denies by default, requires explicit grants.
    """

    def __init__(self, capabilities: AgentCapabilities):
        """Initialize enforcer with agent capabilities."""
        self.capabilities = capabilities

    def check_query(
        self,
        query: MemoryQuery,
        current_session: str,
        estimated_cost: int,
    ) -> None:
        """Check if query is allowed under agent capabilities.

        Args:
            query: Memory query to validate
            current_session: Agent's current session ID
            estimated_cost: Estimated query complexity

        Raises:
            SecurityViolation: If query violates capabilities
        """
        # Check session access
        target_session = query.session_id or current_session
        if not self.capabilities.can_access_session(current_session, target_session):
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot access session {target_session}"
            )

        # Check memory type access
        if query.memory_type and not self.capabilities.can_query_memory_type(query.memory_type):
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot query {query.memory_type.value} memories"
            )

        # Check query complexity
        if estimated_cost > self.capabilities.max_query_complexity:
            raise SecurityViolation(
                f"Query complexity {estimated_cost} exceeds limit {self.capabilities.max_query_complexity}"
            )

        # Check result limit
        if query.limit and query.limit > self.capabilities.max_results:
            raise SecurityViolation(
                f"Query limit {query.limit} exceeds agent max {self.capabilities.max_results}"
            )

    def check_store(
        self,
        memory_type: MemoryType,
        target_session: str,
        current_session: str,
    ) -> None:
        """Check if agent can store memory.

        Args:
            memory_type: Type of memory to store
            target_session: Session to store in
            current_session: Agent's current session

        Raises:
            SecurityViolation: If store violates capabilities
        """
        # Check memory type access
        if not self.capabilities.can_query_memory_type(memory_type):
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot store {memory_type.value} memories"
            )

        # Check session write access
        if not self.capabilities.can_write_to_session(current_session, target_session):
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot write to session {target_session}"
            )

    def check_delete(self, memory_id: str) -> None:
        """Check if agent can delete memory.

        Args:
            memory_id: ID of memory to delete

        Raises:
            SecurityViolation: If delete violates capabilities
        """
        if not self.capabilities.can_delete_memories:
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot delete memories"
            )

    def check_clear(self, target_session: str, current_session: str) -> None:
        """Check if agent can clear session.

        Args:
            target_session: Session to clear
            current_session: Agent's current session

        Raises:
            SecurityViolation: If clear violates capabilities
        """
        if not self.capabilities.can_clear_memories:
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot clear memories"
            )

        if not self.capabilities.can_write_to_session(current_session, target_session):
            raise SecurityViolation(
                f"Agent {self.capabilities.agent_id} cannot clear session {target_session}"
            )
```

### 2. Credential Protection

#### 2.1 Credential Scrubbing Patterns

```python
# File: src/amplihack/memory/security/credentials.py

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrubPattern:
    """Pattern for detecting and scrubbing credentials."""

    name: str
    pattern: re.Pattern
    replacement: str = "[REDACTED]"

    def scrub(self, text: str) -> tuple[str, bool]:
        """Scrub credentials from text.

        Returns:
            (scrubbed_text, was_modified)
        """
        scrubbed, count = self.pattern.subn(self.replacement, text)
        return scrubbed, count > 0


# Comprehensive credential patterns
CREDENTIAL_PATTERNS = [
    # API Keys (generic patterns)
    ScrubPattern(
        name="generic_api_key",
        pattern=re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Long alphanumeric strings
        replacement="[API_KEY_REDACTED]",
    ),

    # AWS credentials
    ScrubPattern(
        name="aws_access_key",
        pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
        replacement="[AWS_KEY_REDACTED]",
    ),

    # GitHub tokens
    ScrubPattern(
        name="github_token",
        pattern=re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        replacement="[GITHUB_TOKEN_REDACTED]",
    ),

    # Private keys (PEM format)
    ScrubPattern(
        name="private_key",
        pattern=re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----.*?-----END (?:RSA |EC )?PRIVATE KEY-----', re.DOTALL),
        replacement="[PRIVATE_KEY_REDACTED]",
    ),

    # JWT tokens
    ScrubPattern(
        name="jwt_token",
        pattern=re.compile(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'),
        replacement="[JWT_REDACTED]",
    ),

    # Database connection strings
    ScrubPattern(
        name="db_connection",
        pattern=re.compile(r'(?:mysql|postgresql|mongodb)://[^@]+:[^@]+@[^\s]+'),
        replacement="[DB_CONNECTION_REDACTED]",
    ),

    # Generic password patterns
    ScrubPattern(
        name="password_field",
        pattern=re.compile(r'(?i)password\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        replacement=r'password: [PASSWORD_REDACTED]',
    ),

    # Environment variable secrets
    ScrubPattern(
        name="env_secret",
        pattern=re.compile(r'(?i)(?:secret|token|key|password)=[\'"]?([^\s\'"]+)', re.IGNORECASE),
        replacement=r'[SECRET_REDACTED]',
    ),
]


class CredentialScrubber:
    """Scrubs credentials from memory content."""

    def __init__(self, patterns: list[ScrubPattern] = None):
        """Initialize scrubber with patterns."""
        self.patterns = patterns or CREDENTIAL_PATTERNS

    def scrub(self, content: str) -> tuple[str, list[str]]:
        """Scrub all credential patterns from content.

        Returns:
            (scrubbed_content, detected_patterns)
        """
        scrubbed = content
        detected = []

        for pattern in self.patterns:
            scrubbed, was_modified = pattern.scrub(scrubbed)
            if was_modified:
                detected.append(pattern.name)

        return scrubbed, detected

    def contains_credentials(self, content: str) -> bool:
        """Check if content contains credentials without scrubbing."""
        for pattern in self.patterns:
            if pattern.pattern.search(content):
                return True
        return False

    def tag_sensitive_content(self, content: str) -> dict[str, bool]:
        """Generate sensitivity tags for content.

        Returns:
            Dictionary of sensitivity flags
        """
        tags = {
            "contains_credentials": False,
            "contains_api_keys": False,
            "contains_passwords": False,
            "sensitivity_level": "low",
        }

        for pattern in self.patterns:
            if pattern.pattern.search(content):
                tags["contains_credentials"] = True

                if "api_key" in pattern.name or "token" in pattern.name:
                    tags["contains_api_keys"] = True

                if "password" in pattern.name:
                    tags["contains_passwords"] = True

        if tags["contains_credentials"]:
            tags["sensitivity_level"] = "high"

        return tags
```

#### 2.2 Integration with Storage Pipeline

```python
# Modify coordinator.py store() method to integrate credential scrubbing:

async def store(self, request: StorageRequest) -> str | None:
    """Store a memory with security checks."""
    try:
        # 1. Credential scrubbing (NEW)
        scrubber = CredentialScrubber()
        scrubbed_content, detected_patterns = scrubber.scrub(request.content)

        if detected_patterns:
            logger.warning(
                f"Credentials detected and scrubbed: {detected_patterns}"
            )
            # Add security audit log
            await self._audit_log("credential_scrubbed", {
                "patterns": detected_patterns,
                "agent_id": request.context.get("agent_id"),
            })

            # Replace content with scrubbed version
            request.content = scrubbed_content

        # Tag sensitive memories
        sensitivity_tags = scrubber.tag_sensitive_content(request.content)
        request.metadata.update(sensitivity_tags)

        # 2. Capability check (NEW)
        if hasattr(self, 'enforcer'):
            self.enforcer.check_store(
                memory_type=request.memory_type,
                target_session=self.session_id,
                current_session=self.session_id,
            )

        # ... existing trivial check, duplicate check, quality review ...

        return memory_id
```

### 3. Memory Isolation

#### 3.1 Session-Based Boundaries

**Current State:**

- Session isolation exists via `session_id` field
- `clear_all()` validates session (coordinator.py line 342-383)
- Other methods don't consistently enforce isolation

**Enhancement:**

- Add session validation to ALL methods
- Enforce at backend layer (not just coordinator)
- Add session lineage for controlled cross-session sharing

```python
# File: src/amplihack/memory/security/isolation.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionLineage:
    """Tracks session relationships for controlled sharing.

    Allows cross-session memory access when sessions are related
    (e.g., child tasks spawned from parent session).
    """

    session_id: str
    parent_session: Optional[str] = None
    child_sessions: list[str] = None

    def __post_init__(self):
        if self.child_sessions is None:
            self.child_sessions = []

    def can_access(self, target_session: str) -> bool:
        """Check if this session can access target session."""
        # Always allow self
        if self.session_id == target_session:
            return True

        # Allow access to parent
        if self.parent_session == target_session:
            return True

        # Allow access to children
        if target_session in self.child_sessions:
            return True

        return False


class IsolationManager:
    """Manages session isolation and lineage."""

    def __init__(self):
        self._lineages: dict[str, SessionLineage] = {}

    def register_session(
        self,
        session_id: str,
        parent_session: Optional[str] = None,
    ) -> SessionLineage:
        """Register a new session with optional parent."""
        lineage = SessionLineage(
            session_id=session_id,
            parent_session=parent_session,
        )

        self._lineages[session_id] = lineage

        # Update parent's children list
        if parent_session and parent_session in self._lineages:
            parent_lineage = self._lineages[parent_session]
            if session_id not in parent_lineage.child_sessions:
                parent_lineage.child_sessions.append(session_id)

        return lineage

    def check_access(
        self,
        current_session: str,
        target_session: str,
    ) -> bool:
        """Check if current session can access target session."""
        if current_session == target_session:
            return True

        # Check lineage
        if current_session in self._lineages:
            lineage = self._lineages[current_session]
            return lineage.can_access(target_session)

        return False
```

### 4. Query Security

#### 4.1 Query Cost Estimation

```python
# File: src/amplihack/memory/security/query_validator.py

from dataclasses import dataclass

from ..models import MemoryQuery


@dataclass
class QueryCost:
    """Estimated cost of executing a query."""

    base_cost: int = 1
    filter_cost: int = 0
    result_cost: int = 0
    complexity_cost: int = 0

    @property
    def total_cost(self) -> int:
        """Calculate total query cost."""
        return self.base_cost + self.filter_cost + self.result_cost + self.complexity_cost


class QueryCostEstimator:
    """Estimates query execution cost before running."""

    # Cost weights
    FILTER_COST_PER_FIELD = 5
    RESULT_COST_PER_ROW = 1
    CONTENT_SEARCH_COST = 20
    TAG_SEARCH_COST = 10
    TIME_RANGE_COST = 5

    def estimate(self, query: MemoryQuery) -> QueryCost:
        """Estimate cost of executing query.

        Returns:
            QueryCost with breakdown
        """
        cost = QueryCost()

        # Count active filters
        filter_count = sum([
            bool(query.session_id),
            bool(query.agent_id),
            bool(query.memory_type),
            bool(query.min_importance),
            bool(query.created_after or query.created_before),
        ])

        cost.filter_cost = filter_count * self.FILTER_COST_PER_FIELD

        # Content search is expensive
        if query.content_search:
            cost.complexity_cost += self.CONTENT_SEARCH_COST

        # Tag search requires JSON parsing
        if query.tags:
            cost.complexity_cost += self.TAG_SEARCH_COST * len(query.tags)

        # Time range queries
        if query.created_after or query.created_before:
            cost.filter_cost += self.TIME_RANGE_COST

        # Estimate result cost
        if query.limit:
            cost.result_cost = query.limit * self.RESULT_COST_PER_ROW
        else:
            cost.result_cost = 100 * self.RESULT_COST_PER_ROW  # Default limit

        return cost


class QueryValidator:
    """Validates queries for security and performance."""

    def __init__(self, max_complexity: int = 100):
        """Initialize validator.

        Args:
            max_complexity: Maximum query complexity allowed
        """
        self.max_complexity = max_complexity
        self.estimator = QueryCostEstimator()

    def validate(self, query: MemoryQuery) -> QueryCost:
        """Validate query and return cost estimate.

        Args:
            query: Query to validate

        Returns:
            QueryCost if valid

        Raises:
            SecurityViolation: If query violates security policy
        """
        # Cost estimation
        cost = self.estimator.estimate(query)

        # Check complexity limit
        if cost.total_cost > self.max_complexity:
            from .enforcer import SecurityViolation
            raise SecurityViolation(
                f"Query complexity {cost.total_cost} exceeds limit {self.max_complexity}"
            )

        # Cypher injection prevention (existing in models.py, enhance here)
        self._check_injection(query)

        return cost

    def _check_injection(self, query: MemoryQuery) -> None:
        """Check for potential injection attacks.

        Args:
            query: Query to check

        Raises:
            SecurityViolation: If injection detected
        """
        # Already validated in MemoryQuery.__post_init__
        # This is defense in depth
        from .enforcer import SecurityViolation

        # Check for Cypher injection patterns
        if query.content_search:
            suspicious_patterns = [
                "MATCH", "CREATE", "DELETE", "MERGE", "SET",
                "REMOVE", "RETURN", "WITH", "UNION",
            ]
            search_upper = query.content_search.upper()
            for pattern in suspicious_patterns:
                if pattern in search_upper:
                    raise SecurityViolation(
                        f"Potential Cypher injection detected: {pattern}"
                    )
```

#### 4.2 Parameter Validation

**Enhancement to existing MemoryQuery validation:**

```python
# Add to models.py MemoryQuery.__post_init__:

def __post_init__(self):
    """Validate query parameters (ENHANCED)."""
    # ... existing validation ...

    # NEW: Additional injection checks
    if self.content_search:
        # Check length to prevent DoS
        if len(self.content_search) > 1000:
            raise ValueError("content_search too long (max 1000 chars)")

        # Check for null bytes (SQLite injection)
        if '\x00' in self.content_search:
            raise ValueError("content_search contains null bytes")

    # NEW: Validate tags are safe
    if self.tags:
        for tag in self.tags:
            if not tag.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Invalid tag format: {tag}")
```

### 5. Audit Logging

#### 5.1 Security Event Schema

```python
# File: src/amplihack/memory/security/audit.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SecurityEventType(Enum):
    """Types of security events to log."""

    # Access control
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Credential handling
    CREDENTIAL_SCRUBBED = "credential_scrubbed"
    CREDENTIAL_ACCESS_DENIED = "credential_access_denied"

    # Query security
    QUERY_BLOCKED = "query_blocked"
    QUERY_COMPLEXITY_EXCEEDED = "query_complexity_exceeded"
    INJECTION_ATTEMPT = "injection_attempt"

    # Session management
    SESSION_CREATED = "session_created"
    SESSION_CLEARED = "session_cleared"
    CROSS_SESSION_ACCESS = "cross_session_access"

    # Anomalies
    UNUSUAL_QUERY_PATTERN = "unusual_query_pattern"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


@dataclass
class SecurityEvent:
    """Represents a security event."""

    event_type: SecurityEventType
    timestamp: datetime
    agent_id: str
    session_id: str

    # Event details
    details: dict[str, Any]

    # Severity (1=info, 5=critical)
    severity: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "details": self.details,
            "severity": self.severity,
        }


class AuditLogger:
    """Logs security events for monitoring and forensics."""

    def __init__(self, log_file: Optional[str] = None):
        """Initialize audit logger.

        Args:
            log_file: Path to audit log file (None = memory only)
        """
        self.log_file = log_file
        self._events: list[SecurityEvent] = []

    async def log_event(
        self,
        event_type: SecurityEventType,
        agent_id: str,
        session_id: str,
        details: dict[str, Any],
        severity: int = 1,
    ) -> None:
        """Log a security event.

        Args:
            event_type: Type of security event
            agent_id: Agent that triggered event
            session_id: Session context
            details: Event-specific details
            severity: Event severity (1-5)
        """
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            agent_id=agent_id,
            session_id=session_id,
            details=details,
            severity=severity,
        )

        self._events.append(event)

        # Write to log file if configured
        if self.log_file:
            await self._write_to_file(event)

    async def _write_to_file(self, event: SecurityEvent) -> None:
        """Write event to log file."""
        import json
        from pathlib import Path

        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, 'a') as f:
            f.write(json.dumps(event.to_dict()) + '\n')

    def get_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        min_severity: int = 1,
    ) -> list[SecurityEvent]:
        """Retrieve events from memory buffer.

        Args:
            event_type: Filter by event type
            min_severity: Minimum severity to include

        Returns:
            List of matching events
        """
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if min_severity > 1:
            events = [e for e in events if e.severity >= min_severity]

        return events
```

#### 5.2 Anomaly Detection (Optional)

```python
# File: src/amplihack/memory/security/anomaly.py

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional


class AnomalyDetector:
    """Detects unusual patterns in memory access.

    Lightweight anomaly detection without ML:
    - Rate limiting (requests per minute)
    - Access pattern changes
    - Unusual query characteristics
    """

    def __init__(
        self,
        max_queries_per_minute: int = 60,
        max_failed_queries: int = 5,
    ):
        """Initialize detector.

        Args:
            max_queries_per_minute: Query rate limit
            max_failed_queries: Failed query threshold
        """
        self.max_queries_per_minute = max_queries_per_minute
        self.max_failed_queries = max_failed_queries

        # Tracking state
        self._query_timestamps: defaultdict[str, list[datetime]] = defaultdict(list)
        self._failed_queries: defaultdict[str, int] = defaultdict(int)

    def check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within rate limit.

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)

        # Get timestamps from last minute
        timestamps = self._query_timestamps[agent_id]
        recent = [t for t in timestamps if t > one_minute_ago]

        # Update tracking
        recent.append(now)
        self._query_timestamps[agent_id] = recent[-100:]  # Keep last 100

        # Check limit
        return len(recent) <= self.max_queries_per_minute

    def record_failed_query(self, agent_id: str) -> bool:
        """Record failed query attempt.

        Returns:
            True if within threshold, False if exceeded
        """
        self._failed_queries[agent_id] += 1
        return self._failed_queries[agent_id] <= self.max_failed_queries

    def reset_failed_queries(self, agent_id: str) -> None:
        """Reset failed query counter (on successful query)."""
        self._failed_queries[agent_id] = 0
```

### 6. SecureMemoryBackend Implementation

#### 6.1 Security Middleware Wrapper

```python
# File: src/amplihack/memory/security/backend.py

from typing import Optional

from ..backends.base import BackendCapabilities, MemoryBackend
from ..models import MemoryEntry, MemoryQuery, SessionInfo
from .audit import AuditLogger, SecurityEventType
from .capabilities import AgentCapabilities
from .credentials import CredentialScrubber
from .enforcer import CapabilityEnforcer, SecurityViolation
from .isolation import IsolationManager
from .query_validator import QueryValidator


class SecureMemoryBackend:
    """Security middleware wrapper for memory backends.

    Wraps any MemoryBackend implementation with security checks:
    - Capability enforcement
    - Credential scrubbing
    - Session isolation
    - Query validation
    - Audit logging

    Transparent to agent logic - same interface as MemoryBackend.

    Example:
        # Wrap existing backend
        base_backend = SQLiteBackend()
        secure_backend = SecureMemoryBackend(
            backend=base_backend,
            capabilities=agent_capabilities,
            audit_log_path=".amplihack/security/audit.log",
        )

        # Use normally
        await secure_backend.initialize()
        await secure_backend.store_memory(memory_entry)
    """

    def __init__(
        self,
        backend: MemoryBackend,
        capabilities: AgentCapabilities,
        current_session: str,
        audit_log_path: Optional[str] = None,
        enable_anomaly_detection: bool = True,
    ):
        """Initialize secure backend wrapper.

        Args:
            backend: Underlying backend to wrap
            capabilities: Agent capabilities for access control
            current_session: Current session ID
            audit_log_path: Path to audit log file
            enable_anomaly_detection: Enable anomaly detection
        """
        self.backend = backend
        self.capabilities = capabilities
        self.current_session = current_session

        # Security components
        self.enforcer = CapabilityEnforcer(capabilities)
        self.scrubber = CredentialScrubber()
        self.isolation = IsolationManager()
        self.validator = QueryValidator(max_complexity=capabilities.max_query_complexity)
        self.audit_logger = AuditLogger(log_file=audit_log_path)

        # Optional anomaly detection
        self.anomaly_detector = None
        if enable_anomaly_detection:
            from .anomaly import AnomalyDetector
            self.anomaly_detector = AnomalyDetector()

    def get_capabilities(self) -> BackendCapabilities:
        """Get backend capabilities."""
        return self.backend.get_capabilities()

    async def initialize(self) -> None:
        """Initialize backend."""
        # Register session
        self.isolation.register_session(self.current_session)

        # Initialize underlying backend
        await self.backend.initialize()

        # Log initialization
        await self.audit_logger.log_event(
            SecurityEventType.SESSION_CREATED,
            agent_id=self.capabilities.agent_id,
            session_id=self.current_session,
            details={"capabilities": str(self.capabilities)},
        )

    async def store_memory(self, memory: MemoryEntry) -> bool:
        """Store memory with security checks."""
        try:
            # 1. Credential scrubbing
            scrubbed_content, detected_patterns = self.scrubber.scrub(memory.content)

            if detected_patterns:
                await self.audit_logger.log_event(
                    SecurityEventType.CREDENTIAL_SCRUBBED,
                    agent_id=self.capabilities.agent_id,
                    session_id=self.current_session,
                    details={"patterns": detected_patterns, "memory_id": memory.id},
                    severity=3,
                )
                memory.content = scrubbed_content

            # 2. Capability check
            from ..types import MemoryType as NewMemoryType
            # Get new memory type from metadata
            new_type_str = memory.metadata.get("new_memory_type", "episodic")
            new_type = NewMemoryType(new_type_str)

            self.enforcer.check_store(
                memory_type=new_type,
                target_session=memory.session_id,
                current_session=self.current_session,
            )

            # 3. Session isolation check
            if not self.isolation.check_access(self.current_session, memory.session_id):
                raise SecurityViolation(
                    f"Cannot write to session {memory.session_id} from {self.current_session}"
                )

            # 4. Store in backend
            success = await self.backend.store_memory(memory)

            # 5. Audit log
            await self.audit_logger.log_event(
                SecurityEventType.ACCESS_GRANTED,
                agent_id=self.capabilities.agent_id,
                session_id=self.current_session,
                details={"operation": "store", "memory_id": memory.id},
            )

            return success

        except SecurityViolation as e:
            # Log security violation
            await self.audit_logger.log_event(
                SecurityEventType.ACCESS_DENIED,
                agent_id=self.capabilities.agent_id,
                session_id=self.current_session,
                details={"operation": "store", "reason": str(e)},
                severity=4,
            )
            raise

    async def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories with security checks."""
        try:
            # 1. Rate limiting (if enabled)
            if self.anomaly_detector:
                if not self.anomaly_detector.check_rate_limit(self.capabilities.agent_id):
                    raise SecurityViolation("Rate limit exceeded")

            # 2. Query validation and cost estimation
            cost = self.validator.validate(query)

            # 3. Capability enforcement
            self.enforcer.check_query(
                query=query,
                current_session=self.current_session,
                estimated_cost=cost.total_cost,
            )

            # 4. Session isolation
            target_session = query.session_id or self.current_session
            if not self.isolation.check_access(self.current_session, target_session):
                raise SecurityViolation(
                    f"Cannot access session {target_session} from {self.current_session}"
                )

            # 5. Execute query
            memories = await self.backend.retrieve_memories(query)

            # 6. Filter out credential-tagged memories (if not authorized)
            if not self.capabilities.can_access_credentials:
                memories = [
                    m for m in memories
                    if not m.metadata.get("contains_credentials", False)
                ]

            # 7. Audit log
            await self.audit_logger.log_event(
                SecurityEventType.ACCESS_GRANTED,
                agent_id=self.capabilities.agent_id,
                session_id=self.current_session,
                details={
                    "operation": "retrieve",
                    "query_cost": cost.total_cost,
                    "result_count": len(memories),
                },
            )

            # 8. Reset failed query counter
            if self.anomaly_detector:
                self.anomaly_detector.reset_failed_queries(self.capabilities.agent_id)

            return memories

        except SecurityViolation as e:
            # Log security violation
            await self.audit_logger.log_event(
                SecurityEventType.ACCESS_DENIED,
                agent_id=self.capabilities.agent_id,
                session_id=self.current_session,
                details={"operation": "retrieve", "reason": str(e)},
                severity=4,
            )

            # Track failed queries
            if self.anomaly_detector:
                if not self.anomaly_detector.record_failed_query(self.capabilities.agent_id):
                    await self.audit_logger.log_event(
                        SecurityEventType.UNUSUAL_QUERY_PATTERN,
                        agent_id=self.capabilities.agent_id,
                        session_id=self.current_session,
                        details={"reason": "Too many failed queries"},
                        severity=5,
                    )

            raise

    async def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get memory by ID with security checks."""
        # Capability check for read access
        memory = await self.backend.get_memory_by_id(memory_id)

        if memory:
            # Check session access
            if not self.isolation.check_access(self.current_session, memory.session_id):
                raise SecurityViolation(
                    f"Cannot access memory from session {memory.session_id}"
                )

            # Filter credentials if not authorized
            if not self.capabilities.can_access_credentials:
                if memory.metadata.get("contains_credentials", False):
                    raise SecurityViolation("Not authorized to access credential-tagged memory")

        return memory

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory with security checks."""
        # Capability check
        self.enforcer.check_delete(memory_id)

        # Get memory to check session
        memory = await self.backend.get_memory_by_id(memory_id)
        if memory:
            if not self.isolation.check_access(self.current_session, memory.session_id):
                raise SecurityViolation(
                    f"Cannot delete memory from session {memory.session_id}"
                )

        success = await self.backend.delete_memory(memory_id)

        # Audit log
        await self.audit_logger.log_event(
            SecurityEventType.ACCESS_GRANTED,
            agent_id=self.capabilities.agent_id,
            session_id=self.current_session,
            details={"operation": "delete", "memory_id": memory_id},
        )

        return success

    async def cleanup_expired(self) -> int:
        """Cleanup expired memories."""
        # No special security checks - this is maintenance
        return await self.backend.cleanup_expired()

    async def get_session_info(self, session_id: str) -> SessionInfo | None:
        """Get session info with access check."""
        if not self.isolation.check_access(self.current_session, session_id):
            raise SecurityViolation(f"Cannot access session {session_id}")

        return await self.backend.get_session_info(session_id)

    async def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        """List sessions (filtered by access)."""
        all_sessions = await self.backend.list_sessions(limit)

        # Filter to only accessible sessions
        accessible = [
            s for s in all_sessions
            if self.isolation.check_access(self.current_session, s.session_id)
        ]

        return accessible

    async def get_stats(self) -> dict[str, any]:
        """Get backend stats."""
        return await self.backend.get_stats()

    async def close(self) -> None:
        """Close backend connection."""
        await self.backend.close()
```

## Integration Strategy

### Phase 1: Core Security Layer (Week 1)

1. Implement capability system (`capabilities.py`, `enforcer.py`)
2. Integrate with MemoryCoordinator
3. Add tests for access control

### Phase 2: Credential Protection (Week 1)

1. Implement credential scrubbing (`credentials.py`)
2. Integrate with storage pipeline
3. Add tests for scrubbing patterns

### Phase 3: Enhanced Isolation (Week 2)

1. Implement session lineage (`isolation.py`)
2. Add validation to all coordinator methods
3. Add tests for cross-session scenarios

### Phase 4: Query Security (Week 2)

1. Implement cost estimation (`query_validator.py`)
2. Add pre-execution validation
3. Add tests for complex queries

### Phase 5: Audit & Monitoring (Week 3)

1. Implement audit logging (`audit.py`)
2. Add anomaly detection (`anomaly.py`)
3. Create security dashboard (optional)

### Phase 6: Backend Wrapper (Week 3)

1. Implement SecureMemoryBackend (`backend.py`)
2. Integration testing
3. Performance benchmarking (<10% overhead)

## Testing Strategy

### Unit Tests

```python
# test_capabilities.py
def test_session_only_scope():
    caps = AgentCapabilities(
        agent_id="test",
        scope=ScopeLevel.SESSION_ONLY,
        allowed_memory_types=[MemoryType.EPISODIC],
    )

    assert caps.can_access_session("sess-1", "sess-1") is True
    assert caps.can_access_session("sess-1", "sess-2") is False

# test_credential_scrubbing.py
def test_scrub_github_token():
    scrubber = CredentialScrubber()
    content = "My token is ghp_1234567890abcdefghijklmnopqrstuv"

    scrubbed, detected = scrubber.scrub(content)

    assert "ghp_" not in scrubbed
    assert "github_token" in detected

# test_query_validator.py
def test_query_complexity_limit():
    validator = QueryValidator(max_complexity=100)
    query = MemoryQuery(
        content_search="test" * 100,  # Expensive search
        limit=1000,
    )

    with pytest.raises(SecurityViolation):
        validator.validate(query)
```

### Integration Tests

```python
# test_secure_backend.py
async def test_secure_backend_access_control():
    base_backend = SQLiteBackend(db_path=":memory:")

    caps = AgentCapabilities(
        agent_id="test-agent",
        scope=ScopeLevel.SESSION_ONLY,
        allowed_memory_types=[MemoryType.EPISODIC],
    )

    secure_backend = SecureMemoryBackend(
        backend=base_backend,
        capabilities=caps,
        current_session="sess-1",
    )

    await secure_backend.initialize()

    # Should allow same-session access
    memory = MemoryEntry(
        id="mem-1",
        session_id="sess-1",
        agent_id="test-agent",
        memory_type=MemoryType.EPISODIC,
        title="Test",
        content="Test content",
        metadata={},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    assert await secure_backend.store_memory(memory) is True

    # Should deny cross-session access
    memory.session_id = "sess-2"
    with pytest.raises(SecurityViolation):
        await secure_backend.store_memory(memory)
```

### Performance Tests

```python
# test_performance.py
async def test_security_overhead():
    """Verify security layer adds <10% overhead."""

    # Baseline: Unsecured backend
    base_backend = SQLiteBackend(db_path=":memory:")
    await base_backend.initialize()

    start = time.time()
    for i in range(1000):
        await base_backend.store_memory(create_test_memory())
    base_time = time.time() - start

    # Secured: With security layer
    secure_backend = SecureMemoryBackend(
        backend=base_backend,
        capabilities=DEFAULT_AGENT_CAPABILITIES,
        current_session="test",
    )

    start = time.time()
    for i in range(1000):
        await secure_backend.store_memory(create_test_memory())
    secure_time = time.time() - start

    # Assert <10% overhead
    overhead_pct = ((secure_time - base_time) / base_time) * 100
    assert overhead_pct < 10, f"Security overhead {overhead_pct:.1f}% exceeds 10%"
```

## Deployment Checklist

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance benchmarks meet <10% overhead
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Migration guide written
- [ ] Backward compatibility verified
- [ ] Audit log rotation configured
- [ ] Monitoring dashboard deployed (optional)
- [ ] Team training completed

## Future Enhancements

### Phase 7: Advanced Features (Future)

1. **Encryption at Rest**
   - Encrypt sensitive memories in database
   - Key management integration

2. **Differential Privacy**
   - Add noise to query results
   - Prevent inference attacks

3. **Security Policies DSL**
   - Define policies in YAML/JSON
   - Dynamic policy updates

4. **Advanced Anomaly Detection**
   - ML-based pattern recognition
   - Behavioral analysis

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- Credential Scrubbing Patterns: [AWS Secret Detection](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security_iam_id-based-policy-examples.html)

---

**Next Steps:**

1. Review this design with security expert
2. Create GitHub issue for implementation
3. Begin Phase 1 development (capability system)
