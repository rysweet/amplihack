"""Data models for amplihack profile system.

This module defines pydantic models for profile configuration, validation,
and metadata management.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ComponentSpec(BaseModel):
    """Specification for filtering a component type.

    Attributes:
        include: List of component names to explicitly include
        exclude: List of component names to explicitly exclude
        include_all: If True, include all components (overrides include/exclude)
    """

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    include_all: bool = False

    @field_validator("include", "exclude")
    @classmethod
    def validate_patterns(cls, v: list[str]) -> list[str]:
        """Ensure patterns are valid strings."""
        if not all(isinstance(pattern, str) for pattern in v):
            raise ValueError("All patterns must be strings")
        return v


class SkillSpec(ComponentSpec):
    """Extended spec for skills with category support.

    Attributes:
        include_categories: List of skill categories to include
        exclude_categories: List of skill categories to exclude

    Inherits all ComponentSpec attributes.
    """

    include_categories: list[str] = Field(default_factory=list)
    exclude_categories: list[str] = Field(default_factory=list)

    @field_validator("include_categories", "exclude_categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """Ensure categories are valid strings."""
        if not all(isinstance(category, str) for category in v):
            raise ValueError("All categories must be strings")
        return v


class ComponentsConfig(BaseModel):
    """All component specifications.

    Attributes:
        commands: Command filtering specification
        context: Context file filtering specification
        agents: Agent filtering specification
        skills: Skill filtering specification with category support
    """

    commands: ComponentSpec = Field(default_factory=ComponentSpec)
    context: ComponentSpec = Field(default_factory=ComponentSpec)
    agents: ComponentSpec = Field(default_factory=ComponentSpec)
    skills: SkillSpec = Field(default_factory=SkillSpec)


class MetadataConfig(BaseModel):
    """Profile metadata.

    Attributes:
        author: Profile author name
        version: Profile version string
        tags: List of tags for categorization
        created: Creation timestamp
        updated: Last update timestamp
    """

    author: str
    version: str
    tags: list[str] = Field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Ensure tags are valid strings."""
        if not all(isinstance(tag, str) for tag in v):
            raise ValueError("All tags must be strings")
        return v


class PerformanceConfig(BaseModel):
    """Performance tuning options.

    Attributes:
        lazy_load_skills: If True, load skills on-demand rather than at startup
        cache_ttl: Cache time-to-live in seconds
    """

    lazy_load_skills: bool = True
    cache_ttl: int = 3600

    @field_validator("cache_ttl")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Ensure cache_ttl is positive."""
        if v < 0:
            raise ValueError("cache_ttl must be non-negative")
        return v


class ProfileConfig(BaseModel):
    """Complete profile configuration.

    Attributes:
        version: Profile schema version
        name: Profile name
        description: Human-readable profile description
        components: Component specifications
        metadata: Profile metadata
        performance: Performance tuning options
    """

    version: str
    name: str
    description: str
    components: ComponentsConfig
    metadata: MetadataConfig
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @field_validator("version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        """Ensure version is valid format and supported.

        Security: Validates version before model construction to prevent
        processing of unsupported profile versions.
        """
        if not v or not isinstance(v, str):
            raise ValueError("version must be a non-empty string")

        # Validate version compatibility before construction
        SUPPORTED_VERSIONS = ["1.0"]
        if v not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported profile version: {v}. "
                f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
            )

        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is valid."""
        if not v or not isinstance(v, str):
            raise ValueError("name must be a non-empty string")
        return v
