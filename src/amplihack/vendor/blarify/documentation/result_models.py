"""
Result models for the documentation layer.

This module provides Pydantic models for representing the results of documentation
and workflow creation processes, replacing the complex LangGraph state management.
"""

from typing import Any

# Import concrete Node types for type annotations
from amplihack.vendor.blarify.graph.node.documentation_node import DocumentationNode
from amplihack.vendor.blarify.repositories.graph_db_manager.dtos.node_with_content_dto import NodeWithContentDto
from pydantic import BaseModel, ConfigDict, Field


class DocumentationResult(BaseModel):
    """Result of documentation creation process."""

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Allow Node objects

    # Core results
    information_nodes: list[dict[str, Any]] = Field(default_factory=list)
    """List of generated DocumentationNode objects (as dictionaries)"""

    # New fields for proper Node object handling
    documentation_nodes: list[DocumentationNode] = Field(default_factory=list)
    """List of actual DocumentationNode objects"""

    source_nodes: list[NodeWithContentDto] = Field(default_factory=list)
    """List of source code DTOs"""

    # Analysis metadata
    analyzed_nodes: list[dict[str, Any]] = Field(default_factory=list)
    """Analyzed code components"""

    # Processing statistics
    total_nodes_processed: int = 0
    """Total number of nodes processed"""

    processing_time_seconds: float = 0.0
    """Total processing time in seconds"""

    # Error handling
    error: str | None = None
    """Error message if processing failed"""

    warnings: list[str] = Field(default_factory=list)
    """Non-fatal warnings during processing"""


class WorkflowResult(BaseModel):
    """Result of workflow discovery and analysis."""

    # Core workflow data
    entry_point_id: str
    """ID of the entry point node"""

    entry_point_name: str
    """Name of the entry point"""

    entry_point_path: str
    """File path of the entry point"""

    end_point_id: str | None = None
    """ID of the final node in the workflow"""

    end_point_name: str | None = None
    """Name of the final node"""

    end_point_path: str | None = None
    """File path of the final node"""

    # Workflow structure
    workflow_nodes: list[dict[str, Any]] = Field(default_factory=list)
    """Nodes participating in the workflow"""

    workflow_edges: list[dict[str, Any]] = Field(default_factory=list)
    """Edges representing the workflow execution flow"""

    documentation_node_ids: list[str] = Field(default_factory=list)
    """IDs of associated documentation nodes"""

    # Workflow metadata
    workflow_type: str = "execution_trace"
    """Type of workflow discovered"""

    total_execution_steps: int = 0
    """Number of execution steps in the workflow"""

    path_length: int = 0
    """Length of the execution path"""

    discovered_by: str = "code_workflow_discovery"
    """Method used to discover the workflow"""

    # Analysis results
    complexity_score: int | None = None
    """Workflow complexity score (if calculated)"""

    has_cycles: bool = False
    """Whether the workflow contains cycles"""

    # Error handling
    error: str | None = None
    """Error message if discovery failed"""


class WorkflowDiscoveryResult(BaseModel):
    """Result of complete workflow discovery process."""

    # Discovery results
    discovered_workflows: list[WorkflowResult] = Field(default_factory=list)
    """All discovered workflows"""

    entry_points: list[dict[str, Any]] = Field(default_factory=list)
    """Entry points used for discovery"""

    # Statistics
    total_entry_points: int = 0
    """Total number of entry points analyzed"""

    total_workflows: int = 0
    """Total number of workflows discovered"""

    discovery_time_seconds: float = 0.0
    """Time taken for discovery in seconds"""

    # Error handling
    error: str | None = None
    """Error message if discovery failed"""

    warnings: list[str] = Field(default_factory=list)
    """Non-fatal warnings during discovery"""


class FrameworkDetectionResult(BaseModel):
    """Result of framework detection analysis."""

    # Framework information
    primary_framework: str | None = None
    """Primary framework detected (e.g., Django, React, etc.)"""

    framework_version: str | None = None
    """Version of the framework if detected"""

    technology_stack: list[str] = Field(default_factory=list)
    """List of technologies detected in the codebase"""

    main_folders: list[str] = Field(default_factory=list)
    """Main architectural folders identified"""

    config_files: list[str] = Field(default_factory=list)
    """Configuration files found"""

    # Analysis metadata
    confidence_score: float = 0.0
    """Confidence in the framework detection (0.0-1.0)"""

    analysis_method: str = "llm_analysis"
    """Method used for detection"""

    # Raw analysis
    raw_analysis: str = ""
    """Raw LLM analysis output"""

    # Error handling
    error: str | None = None
    """Error message if detection failed"""
