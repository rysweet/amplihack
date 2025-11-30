"""
Data models for the Agent Bundle Generator.

Provides type-safe data structures for all stages of the bundle generation pipeline.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class ParsedPrompt:
    """Result of parsing a natural language prompt."""

    raw_prompt: str
    tokens: list[str]
    sentences: list[str]
    key_phrases: list[str]
    entities: dict[str, list[str]]  # entity_type -> values
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parsed prompt data."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        if not self.raw_prompt.strip():
            raise ValueError("Raw prompt cannot be empty")


@dataclass
class ExtractedIntent:
    """Extracted intent and requirements from a parsed prompt."""

    action: Literal["create", "modify", "combine", "specialize"]
    domain: str  # e.g., "security", "data-processing", "monitoring"
    agent_count: int
    agent_requirements: list["AgentRequirement"]
    complexity: Literal["simple", "standard", "advanced"]
    constraints: list[str]
    dependencies: list[str]
    confidence: float

    def __post_init__(self):
        """Validate extracted intent."""
        if self.agent_count < 1:
            raise ValueError("Must have at least one agent")
        if self.agent_count > 10:
            raise ValueError("Maximum 10 agents per bundle")
        if not self.agent_requirements:
            raise ValueError("Must have at least one agent requirement")


@dataclass
class AgentRequirement:
    """Requirements for a single agent."""

    name: str
    role: str
    purpose: str
    capabilities: list[str]
    constraints: list[str] = field(default_factory=list)
    suggested_type: Literal["core", "specialized", "workflow"] = "specialized"
    dependencies: list[str] = field(default_factory=list)
    priority: int = 0  # 0 = highest priority

    def __post_init__(self):
        """Validate agent requirement."""
        if not self.name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Agent name must be alphanumeric with hyphens/underscores: {self.name}"
            )
        if not self.capabilities:
            raise ValueError(f"Agent {self.name} must have at least one capability")


@dataclass
class GeneratedAgent:
    """A generated agent with content and metadata."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    type: Literal["core", "specialized", "workflow"] = "specialized"
    role: str = ""
    description: str = ""
    content: str = ""  # Markdown content
    model: str = "inherit"
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)  # Test file contents
    documentation: str = ""  # Additional docs
    created_at: datetime = field(default_factory=datetime.utcnow)
    generation_time_seconds: float = 0.0

    def __post_init__(self):
        """Validate generated agent."""
        if self.content and len(self.content) < 100:
            raise ValueError(f"Agent {self.name} content must be at least 100 characters")
        if not self.role:
            raise ValueError(f"Agent {self.name} must have a role")

    @property
    def file_size_kb(self) -> float:
        """Estimated file size in KB."""
        return len(self.content.encode("utf-8")) / 1024


@dataclass
class AgentBundle:
    """A complete bundle of agents ready for packaging."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    agents: list[GeneratedAgent] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: Literal["pending", "processing", "ready", "failed"] = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate bundle."""
        if not self.name:
            raise ValueError("Bundle must have a name")
        if not self.agents:
            raise ValueError("Bundle must contain at least one agent")
        if len(self.name) < 3 or len(self.name) > 50:
            raise ValueError("Bundle name must be 3-50 characters")

    @property
    def agent_count(self) -> int:
        """Number of agents in bundle."""
        return len(self.agents)

    @property
    def total_size_kb(self) -> float:
        """Total estimated size in KB."""
        return sum(agent.file_size_kb for agent in self.agents)


@dataclass
class PackagedBundle:
    """A packaged bundle ready for distribution."""

    bundle: AgentBundle
    package_path: Path
    format: Literal["tar.gz", "zip", "directory", "uvx"]
    checksum: str = ""
    size_bytes: int = 0
    uvx_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate packaged bundle."""
        if not self.package_path:
            raise ValueError("Package must have a path")
        if self.format == "uvx" and not self.uvx_metadata:
            self.uvx_metadata = {
                "version": "1.0.0",
                "python_requirement": ">=3.11",
                "entry_point": f"amplihack.bundle_generator.{self.bundle.name}",
            }


@dataclass
class DistributionResult:
    """Result of distributing a bundle."""

    success: bool
    platform: Literal["github", "pypi", "local"]
    url: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    release_tag: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    distribution_time_seconds: float = 0.0

    @property
    def has_errors(self) -> bool:
        """Check if distribution had errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if distribution had warnings."""
        return len(self.warnings) > 0


@dataclass
class TestResult:
    """Result of testing an agent or bundle."""

    test_type: Literal["agent", "bundle", "integration"]
    target_name: str
    passed: bool
    test_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    failures: list[dict[str, Any]] = field(default_factory=list)
    coverage_percent: float | None = None

    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.test_count == 0:
            return 0.0
        return self.passed_count / self.test_count


@dataclass
class GenerationMetrics:
    """Metrics for bundle generation performance."""

    total_time_seconds: float = 0.0
    parsing_time: float = 0.0
    extraction_time: float = 0.0
    generation_time: float = 0.0
    validation_time: float = 0.0
    packaging_time: float = 0.0
    agent_count: int = 0
    total_size_kb: float = 0.0
    memory_peak_mb: float = 0.0

    @property
    def average_agent_time(self) -> float:
        """Average time per agent."""
        if self.agent_count == 0:
            return 0.0
        return self.generation_time / self.agent_count
