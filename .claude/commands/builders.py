#!/usr/bin/env python3
"""
/builders command - Transcript and Codex Builders Management
Implements Microsoft Amplifier-style session documentation and knowledge extraction.
"""

import sys
from pathlib import Path

# Clean import setup - use robust path detection (must be done before other imports)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
try:
    from amplihack.utils.paths import FrameworkPathResolver

    project_root = FrameworkPathResolver.find_framework_root()
    if project_root is None:
        raise RuntimeError(
            "Could not find project root. Ensure .claude directory exists or set AMPLIHACK_ROOT environment variable."
        )
except ImportError:
    # Fallback for local development - try relative path
    project_root = Path(__file__).resolve().parents[2]
    if not (project_root / ".claude").exists():
        raise RuntimeError(
            "Could not find project root with .claude directory. Please ensure you are running from the correct location."
        )

sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))

import json

from builders import CodexTranscriptsBuilder

# Try to import ExportOnCompactIntegration, but it's optional
try:
    from builders import ExportOnCompactIntegration
except ImportError:
    ExportOnCompactIntegration = None


def show_help():
    """Display help information for the builders command."""
    help_text = """
🔧 Transcript and Codex Builders - Microsoft Amplifier Style

USAGE:
    /builders <subcommand> [options]

SUBCOMMANDS:
    build-transcript <session_id>         Build transcript for specific session
    build-codex [session_ids...]          Build comprehensive codex
    extract-corpus [session_ids...]       Extract learning corpus
    generate-insights [session_ids...]    Generate insights report
    list-sessions                         List available sessions
    restore-session <session_id>          Restore session data
    export-summary <session_id>           Show export summary
    focus-codex <area> [session_ids...]   Build focused codex (tools/errors/patterns/decisions/workflows)

EXAMPLES:
    /builders build-transcript 20241002_092454
    /builders build-codex
    /builders extract-corpus 20241002_092454 20241001_153022
    /builders focus-codex tools
    /builders list-sessions
    /builders restore-session latest

OPTIONS:
    --output-dir <path>    Specify output directory for exports
    --format <json|md>     Output format (default: json)
    --verbose              Show detailed progress information

INTEGRATION:
    This tool integrates with the pre-compact hook system to automatically
    export session data before context compaction. Enhanced exports include
    transcripts, summaries, codex data, and learning corpus extraction.
"""
    print(help_text)


def list_available_sessions() -> list[dict[str, str]]:
    """List available sessions with enhanced export information."""
    if ExportOnCompactIntegration:
        integration = ExportOnCompactIntegration()
        sessions = integration.list_available_sessions()
    else:
        # Fallback to basic session listing
        logs_dir = project_root / ".claude" / "runtime" / "logs"
        sessions = []
        if logs_dir.exists():
            for session_dir in logs_dir.iterdir():
                if session_dir.is_dir():
                    sessions.append(
                        {
                            "session_id": session_dir.name,
                            "has_transcript": (session_dir / "CONVERSATION_TRANSCRIPT.md").exists(),
                            "has_summary": (session_dir / "session_summary.json").exists(),
                            "enhanced_export": False,
                        }
                    )

    print(f"📋 Available Sessions with Export Data ({len(sessions)} sessions)")
    print("━" * 80)

    for i, session in enumerate(sessions[:15], 1):  # Show latest 15
        session_id = session["session_id"]
        enhanced = "✨" if session.get("enhanced_export", False) else "📄"

        exports = []
        if session.get("has_transcript"):
            exports.append("transcript")
        if session.get("has_summary"):
            exports.append("summary")
        if session.get("has_codex_export"):
            exports.append("codex")

        export_str = ", ".join(exports) if exports else "none"

        print(f"{i:2d}. {enhanced} {session_id}")
        print(
            f"    📊 {session.get('message_count', 0)} messages | {session.get('tools_used', 0)} tools"
        )
        print(f"    📁 Exports: {export_str}")
        print(f"    🕒 {session.get('timestamp', 'Unknown time')}")
        print()

    return sessions


def build_session_transcript(session_id: str, verbose: bool = False) -> str:
    """Build transcript for a specific session."""
    if session_id == "latest":
        if ExportOnCompactIntegration:
            integration = ExportOnCompactIntegration()
            sessions = integration.list_available_sessions()
            if not sessions:
                print("❌ No sessions found")
                return ""
            session_id = sessions[0]["session_id"]
        else:
            # Simple fallback - get latest session directory
            logs_dir = project_root / ".claude" / "runtime" / "logs"
            if logs_dir.exists():
                session_dirs = [d for d in logs_dir.iterdir() if d.is_dir()]
                if session_dirs:
                    session_id = sorted(session_dirs)[-1].name
                else:
                    print("❌ No sessions found")
                    return ""

    print(f"🔄 Building transcript for session: {session_id}")

    # Check if transcript already exists
    transcript_path = f".claude/runtime/logs/{session_id}/CONVERSATION_TRANSCRIPT.md"
    if Path(transcript_path).exists():
        print(f"✅ Transcript already exists for session: {session_id}")
        print(f"📄 Location: {transcript_path}")
        return transcript_path

    print("⚠️  No existing transcript found. Use /transcripts command to create one.")
    return ""


def build_comprehensive_codex(
    session_ids: list[str] | None = None, output_dir: str | None = None, verbose: bool = False
) -> str:
    """Build comprehensive codex from sessions."""
    print("🔄 Building comprehensive codex from session transcripts...")

    codex_builder = CodexTranscriptsBuilder(output_dir)

    try:
        codex_path = codex_builder.build_comprehensive_codex(session_ids)
        print("✅ Comprehensive codex built successfully!")
        print(f"📄 Location: {codex_path}")

        if verbose:
            # Show some statistics
            with open(codex_path) as f:
                codex_data = json.load(f)
                metadata = codex_data.get("metadata", {})
                print(f"📊 Sessions processed: {metadata.get('sessions_processed', 0)}")
                print(f"📊 Total sessions available: {metadata.get('total_sessions_available', 0)}")

        return codex_path
    except Exception as e:
        print(f"❌ Failed to build comprehensive codex: {e}")
        return ""


def extract_learning_corpus(
    session_ids: list[str] | None = None, output_dir: str | None = None, verbose: bool = False
) -> str:
    """Extract learning corpus from sessions."""
    print("🔄 Extracting learning corpus from session transcripts...")

    codex_builder = CodexTranscriptsBuilder(output_dir)

    try:
        corpus_path = codex_builder.extract_learning_corpus(session_ids)
        print("✅ Learning corpus extracted successfully!")
        print(f"📄 Location: {corpus_path}")

        if verbose:
            with open(corpus_path) as f:
                corpus_data = json.load(f)
                metadata = corpus_data.get("metadata", {})
                print(f"📊 Sessions processed: {metadata.get('sessions_count', 0)}")

        return corpus_path
    except Exception as e:
        print(f"❌ Failed to extract learning corpus: {e}")
        return ""


def generate_insights_report(
    session_ids: list[str] | None = None, output_dir: str | None = None, verbose: bool = False
) -> str:
    """Generate insights report from sessions."""
    print("🔄 Generating insights report from session data...")

    codex_builder = CodexTranscriptsBuilder(output_dir)

    try:
        report_path = codex_builder.generate_insights_report(session_ids)
        print("✅ Insights report generated successfully!")
        print(f"📄 Location: {report_path}")

        # Also show markdown version
        md_path = report_path.replace(".json", ".md")
        if Path(md_path).exists():
            print(f"📄 Markdown version: {md_path}")

        return report_path
    except Exception as e:
        print(f"❌ Failed to generate insights report: {e}")
        return ""


def build_focused_codex(
    focus_area: str,
    session_ids: list[str] | None = None,
    output_dir: str | None = None,
    verbose: bool = False,
) -> str:
    """Build focused codex for specific area."""
    valid_areas = ["tools", "errors", "patterns", "decisions", "workflows"]

    if focus_area not in valid_areas:
        print(f"❌ Invalid focus area: {focus_area}")
        print(f"Valid areas: {', '.join(valid_areas)}")
        return ""

    print(f"🔄 Building {focus_area}-focused codex...")

    codex_builder = CodexTranscriptsBuilder(output_dir)

    try:
        codex_path = codex_builder.build_focused_codex(focus_area, session_ids)
        print(f"✅ {focus_area.title()}-focused codex built successfully!")
        print(f"📄 Location: {codex_path}")

        return codex_path
    except Exception as e:
        print(f"❌ Failed to build {focus_area}-focused codex: {e}")
        return ""


def restore_session_data(session_id: str, verbose: bool = False) -> dict[str, str]:
    """Restore and display session data."""
    if session_id == "latest":
        integration = ExportOnCompactIntegration()
        sessions = integration.list_available_sessions()
        if not sessions:
            print("❌ No sessions found")
            return {}
        session_id = sessions[0]["session_id"]

    print(f"🔄 Restoring session data: {session_id}")

    integration = ExportOnCompactIntegration()
    session_data = integration.restore_enhanced_session_data(session_id)

    if not session_data:
        print(f"❌ Session not found: {session_id}")
        return {}

    print(f"✅ Session data restored for: {session_id}")
    print("━" * 60)

    # Show what's available
    available_data = []
    if session_data.get("transcript"):
        available_data.append("📄 Conversation transcript")
    if session_data.get("summary"):
        available_data.append("📊 Session summary")
    if session_data.get("codex_export"):
        available_data.append("🔧 Codex export")
    if session_data.get("export_summary"):
        available_data.append("📋 Export summary")
    if session_data.get("compaction_events"):
        available_data.append("🔄 Compaction events")

    for item in available_data:
        print(f"  {item}")

    if verbose and session_data.get("summary"):
        summary = session_data["summary"]
        print("\n📊 Summary Statistics:")
        print(f"  Messages: {summary.get('message_count', 0)}")
        print(f"  Tools used: {len(summary.get('tools_used', []))}")
        print(f"  Total words: {summary.get('total_words', 0)}")

    return session_data


def show_export_summary(session_id: str) -> None:
    """Show export summary for a session."""
    if session_id == "latest":
        integration = ExportOnCompactIntegration()
        sessions = integration.list_available_sessions()
        if not sessions:
            print("❌ No sessions found")
            return
        session_id = sessions[0]["session_id"]

    logs_dir = project_root / ".claude" / "runtime" / "logs"
    summary_file = logs_dir / session_id / "EXPORT_SUMMARY.md"

    if not summary_file.exists():
        print(f"❌ No export summary found for session: {session_id}")
        return

    print(f"📋 Export Summary for Session: {session_id}")
    print("━" * 80)
    print(summary_file.read_text())


def main():
    """Main entry point for /builders command."""
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if not args or args[0] in ["help", "-h", "--help"]:
        show_help()
        return

    subcommand = args[0]
    remaining_args = args[1:]

    # Parse common options
    verbose = "--verbose" in remaining_args
    if verbose:
        remaining_args.remove("--verbose")

    output_dir = None
    if "--output-dir" in remaining_args:
        idx = remaining_args.index("--output-dir")
        if idx + 1 < len(remaining_args):
            output_dir = remaining_args[idx + 1]
            remaining_args.pop(idx)  # Remove --output-dir
            remaining_args.pop(idx)  # Remove the path

    # Route to appropriate function
    if subcommand == "build-transcript":
        if not remaining_args:
            print("❌ Session ID required")
            return
        build_session_transcript(remaining_args[0], verbose)

    elif subcommand == "build-codex":
        session_ids = remaining_args if remaining_args else None
        build_comprehensive_codex(session_ids, output_dir, verbose)

    elif subcommand == "extract-corpus":
        session_ids = remaining_args if remaining_args else None
        extract_learning_corpus(session_ids, output_dir, verbose)

    elif subcommand == "generate-insights":
        session_ids = remaining_args if remaining_args else None
        generate_insights_report(session_ids, output_dir, verbose)

    elif subcommand == "list-sessions":
        list_available_sessions()

    elif subcommand == "restore-session":
        if not remaining_args:
            print("❌ Session ID required")
            return
        restore_session_data(remaining_args[0], verbose)

    elif subcommand == "export-summary":
        if not remaining_args:
            print("❌ Session ID required")
            return
        show_export_summary(remaining_args[0])

    elif subcommand == "focus-codex":
        if not remaining_args:
            print("❌ Focus area required")
            return
        focus_area = remaining_args[0]
        session_ids = remaining_args[1:] if len(remaining_args) > 1 else None
        build_focused_codex(focus_area, session_ids, output_dir, verbose)

    else:
        print(f"❌ Unknown subcommand: {subcommand}")
        print("Use '/builders help' for usage information")


if __name__ == "__main__":
    main()
