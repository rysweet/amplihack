#!/usr/bin/env python3
"""
Amplihack Builders Module - Microsoft Amplifier Style
Transcript and codex builders for session documentation and knowledge extraction.
"""

import sys

from .claude_transcript_builder import ClaudeTranscriptBuilder
from .codex_transcripts_builder import CodexTranscriptsBuilder

# Note: ExportOnCompactIntegration requires hook_processor which may not be available in all contexts
try:
    from .export_on_compact_integration import ExportOnCompactIntegration

    __all__ = ["ClaudeTranscriptBuilder", "CodexTranscriptsBuilder", "ExportOnCompactIntegration"]
except ImportError as e:
    print(f"WARNING: export_on_compact_integration not available - ExportOnCompactIntegration disabled", file=sys.stderr)
    __all__ = ["ClaudeTranscriptBuilder", "CodexTranscriptsBuilder"]
