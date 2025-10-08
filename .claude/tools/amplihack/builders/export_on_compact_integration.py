#!/usr/bin/env python3
"""
Export-on-Compact Integration - Microsoft Amplifier Style
Integrates transcript and codex builders with the pre-compact hook system.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..hook_processor import HookProcessor
    from .claude_transcript_builder import ClaudeTranscriptBuilder
    from .codex_transcripts_builder import CodexTranscriptsBuilder
except ImportError:
    # Fallback for testing or standalone usage
    from claude_transcript_builder import ClaudeTranscriptBuilder
    from codex_transcripts_builder import CodexTranscriptsBuilder
    from hook_processor import HookProcessor


class ExportOnCompactIntegration(HookProcessor):
    """Enhanced pre-compact hook with transcript and codex builders integration."""

    def __init__(self):
        super().__init__("pre_compact_enhanced")
        # Initialize session attributes
        self.session_id = self.get_session_id()
        self.session_dir = self.log_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize builders
        self.transcript_builder = ClaudeTranscriptBuilder(self.session_id)
        self.codex_builder = CodexTranscriptsBuilder()

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced process that includes transcript and codex building.

        Args:
            input_data: Input from Claude Code containing conversation data

        Returns:
            Comprehensive export results including transcripts and codex
        """
        try:
            # Get conversation data
            conversation = input_data.get("conversation", [])
            messages = input_data.get("messages", [])
            metadata = input_data.get("metadata", {})

            # Use either conversation or messages data
            conversation_data = conversation if conversation else messages

            self.log(
                f"Enhanced export: Processing {len(conversation_data)} entries before compaction"
            )

            results = {
                "status": "success",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "exports": {},
                "metadata": {},
            }

            # 1. Build session transcript
            transcript_path = self.transcript_builder.build_session_transcript(
                conversation_data, metadata
            )
            results["exports"]["transcript"] = transcript_path
            self.log(f"Session transcript built: {transcript_path}")

            # 2. Build session summary
            session_summary = self.transcript_builder.build_session_summary(
                conversation_data, metadata
            )
            results["exports"]["summary"] = session_summary
            self.log(f"Session summary created with {session_summary['message_count']} messages")

            # 3. Export for codex
            codex_export_path = self.transcript_builder.export_for_codex(
                conversation_data, metadata
            )
            results["exports"]["codex_export"] = codex_export_path
            self.log(f"Codex export created: {codex_export_path}")

            # 4. Build comprehensive codex if we have multiple sessions
            try:
                comprehensive_codex_path = self.codex_builder.build_comprehensive_codex()
                results["exports"]["comprehensive_codex"] = comprehensive_codex_path
                self.log(f"Comprehensive codex updated: {comprehensive_codex_path}")
            except Exception as e:
                self.log(f"Could not build comprehensive codex: {e}", "WARNING")

            # 5. Generate insights report
            try:
                insights_report_path = self.codex_builder.generate_insights_report()
                results["exports"]["insights_report"] = insights_report_path
                self.log(f"Insights report generated: {insights_report_path}")
            except Exception as e:
                self.log(f"Could not generate insights report: {e}", "WARNING")

            # 6. Extract learning corpus
            try:
                learning_corpus_path = self.codex_builder.extract_learning_corpus()
                results["exports"]["learning_corpus"] = learning_corpus_path
                self.log(f"Learning corpus extracted: {learning_corpus_path}")
            except Exception as e:
                self.log(f"Could not extract learning corpus: {e}", "WARNING")

            # Save enhanced compaction event metadata
            compaction_info = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "messages_exported": len(conversation_data),
                "exports_created": list(results["exports"].keys()),
                "compaction_trigger": input_data.get("trigger", "unknown"),
                "enhanced_export": True,
                "builder_version": "1.0",
            }

            # Save metadata
            metadata_file = self.session_dir / "enhanced_compaction_events.json"
            events = []
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        events = json.load(f)
                except Exception:
                    events = []

            events.append(compaction_info)

            with open(metadata_file, "w") as f:
                json.dump(events, f, indent=2)

            results["metadata"] = compaction_info

            # Save enhanced metrics
            self.save_metric("messages_exported", len(conversation_data))
            self.save_metric("exports_created", len(results["exports"]))
            self.save_metric("enhanced_compaction_events", len(events))
            self.save_metric("transcript_exported", True)
            self.save_metric("codex_exported", True)

            # Create quick access summary
            self._create_quick_access_summary(results)

            return results

        except Exception as e:
            error_msg = f"Enhanced export failed: {e}"
            self.log(error_msg)
            self.save_metric("transcript_exported", False)
            self.save_metric("codex_exported", False)

            return {"status": "error", "message": error_msg, "error": str(e)}

    def _create_quick_access_summary(self, results: Dict[str, Any]) -> None:
        """Create a quick access summary file for easy reference."""
        summary_content = f"""# Session Export Summary

**Session ID**: {results["session_id"]}
**Exported**: {results["timestamp"]}
**Status**: {results["status"]}

## Files Created

"""

        for export_type, export_path in results.get("exports", {}).items():
            summary_content += f"- **{export_type.title()}**: `{export_path}`\n"

        summary_content += f"""

## Session Statistics

- **Messages**: {results["metadata"].get("messages_exported", 0)}
- **Exports**: {len(results.get("exports", {}))}
- **Enhanced Export**: {results["metadata"].get("enhanced_export", False)}

## Quick Access Commands

```bash
# View transcript
cat "{results.get("exports", {}).get("transcript", "N/A")}"

# View session summary
cat "{self.session_dir}/session_summary.json"

# View codex export
cat "{results.get("exports", {}).get("codex_export", "N/A")}"
```

---
Generated by Export-on-Compact Integration at {results["timestamp"]}
"""

        summary_file = self.session_dir / "EXPORT_SUMMARY.md"
        summary_file.write_text(summary_content)
        self.log(f"Quick access summary created: {summary_file}")

    def restore_enhanced_session_data(self, session_id: str = None) -> Dict[str, Any]:
        """Restore enhanced session data including all exported artifacts.

        Args:
            session_id: Optional session ID. If None, uses current session.

        Returns:
            Dictionary with all available session data
        """
        target_session = session_id or self.session_id
        target_dir = self.log_dir / target_session

        if not target_dir.exists():
            self.log(f"Session directory not found: {target_session}")
            return {}

        session_data = {
            "session_id": target_session,
            "transcript": None,
            "summary": None,
            "codex_export": None,
            "export_summary": None,
            "compaction_events": None,
        }

        # Load transcript
        transcript_file = target_dir / "CONVERSATION_TRANSCRIPT.md"
        if transcript_file.exists():
            session_data["transcript"] = transcript_file.read_text()

        # Load summary
        summary_file = target_dir / "session_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    session_data["summary"] = json.load(f)
            except Exception as e:
                self.log(f"Could not load session summary: {e}")

        # Load codex export
        codex_file = target_dir / "codex_export.json"
        if codex_file.exists():
            try:
                with open(codex_file) as f:
                    session_data["codex_export"] = json.load(f)
            except Exception as e:
                self.log(f"Could not load codex export: {e}")

        # Load export summary
        export_summary_file = target_dir / "EXPORT_SUMMARY.md"
        if export_summary_file.exists():
            session_data["export_summary"] = export_summary_file.read_text()

        # Load compaction events
        compaction_file = target_dir / "enhanced_compaction_events.json"
        if compaction_file.exists():
            try:
                with open(compaction_file) as f:
                    session_data["compaction_events"] = json.load(f)
            except Exception as e:
                self.log(f"Could not load compaction events: {e}")

        self.log(f"Enhanced session data restored for: {target_session}")
        return session_data

    def list_available_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions with enhanced export data.

        Returns:
            List of session information dictionaries
        """
        if not self.log_dir.exists():
            return []

        sessions = []
        for session_dir in self.log_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session_info = {
                "session_id": session_dir.name,
                "has_transcript": (session_dir / "CONVERSATION_TRANSCRIPT.md").exists(),
                "has_summary": (session_dir / "session_summary.json").exists(),
                "has_codex_export": (session_dir / "codex_export.json").exists(),
                "has_export_summary": (session_dir / "EXPORT_SUMMARY.md").exists(),
                "enhanced_export": (session_dir / "enhanced_compaction_events.json").exists(),
            }

            # Get basic stats if summary exists
            summary_file = session_dir / "session_summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file) as f:
                        summary = json.load(f)
                        session_info["message_count"] = summary.get("message_count", 0)
                        session_info["tools_used"] = len(summary.get("tools_used", []))
                        session_info["timestamp"] = summary.get("timestamp", "Unknown")
                except Exception:
                    pass

            sessions.append(session_info)

        return sorted(sessions, key=lambda s: s["session_id"], reverse=True)


def main():
    """Entry point for the enhanced pre-compact hook."""
    hook = ExportOnCompactIntegration()
    hook.run()


if __name__ == "__main__":
    main()
