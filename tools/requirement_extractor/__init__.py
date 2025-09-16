"""
Requirements Extractor Tool

A modular tool for extracting functional requirements from codebases.
Designed to work with AI assistance for comprehensive requirement discovery.
"""

from .orchestrator import RequirementsOrchestrator, run_extraction
from .models import ExtractionConfig, OutputFormat

__all__ = ['RequirementsOrchestrator', 'run_extraction', 'ExtractionConfig', 'OutputFormat']