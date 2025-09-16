"""
Data models for requirements extraction
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats"""
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"


@dataclass
class CodeFile:
    """Represents a single code file"""
    path: str
    relative_path: str
    language: str
    size: int
    lines: int


@dataclass
class CodeModule:
    """Groups related code files into a logical module"""
    name: str
    description: str
    files: List[CodeFile]
    primary_language: str
    total_lines: int = 0

    def __post_init__(self):
        if not self.total_lines:
            self.total_lines = sum(f.lines for f in self.files)


@dataclass
class Requirement:
    """A single functional requirement"""
    id: str
    title: str
    description: str
    category: str  # e.g., "Authentication", "Data Processing", "API"
    priority: str  # "high", "medium", "low"
    source_modules: List[str]  # Which modules this came from
    evidence: List[str]  # Code snippets or patterns that support this
    confidence: float  # 0.0 to 1.0


@dataclass
class ModuleRequirements:
    """Requirements extracted from a specific module"""
    module_name: str
    requirements: List[Requirement]
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    extraction_status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None


@dataclass
class ProcessingState:
    """Tracks the state of the extraction process for resume capability"""
    project_path: str
    total_modules: int
    processed_modules: List[str] = field(default_factory=list)
    failed_modules: List[str] = field(default_factory=list)
    current_module: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    requirements_file: Optional[str] = None

    @property
    def progress_percentage(self) -> float:
        if self.total_modules == 0:
            return 0.0
        return (len(self.processed_modules) / self.total_modules) * 100

    @property
    def is_complete(self) -> bool:
        return len(self.processed_modules) + len(self.failed_modules) >= self.total_modules


@dataclass
class GapAnalysis:
    """Results of comparing extracted requirements against existing docs"""
    documented_requirements: List[Requirement]
    extracted_requirements: List[Requirement]
    missing_in_docs: List[Requirement]
    missing_in_code: List[Requirement]
    inconsistencies: List[Dict[str, Any]]


@dataclass
class ExtractionConfig:
    """Configuration for the extraction process"""
    project_path: str
    output_path: str = "requirements.md"
    output_format: OutputFormat = OutputFormat.MARKDOWN
    include_evidence: bool = True
    min_confidence: float = 0.5
    max_files_per_module: int = 50
    timeout_seconds: int = 120  # Claude SDK timeout
    retry_failed: bool = True
    state_file: str = ".requirements_extraction_state.json"
    existing_requirements_path: Optional[str] = None