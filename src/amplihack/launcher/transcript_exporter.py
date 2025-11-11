"""Session transcript export functionality."""

import importlib.util
import time
from pathlib import Path
from typing import Any, Callable, Optional


class TranscriptExporter:
    """Handles session transcript export using ClaudeTranscriptBuilder."""

    def __init__(
        self,
        log_dir: Path,
        log_func: Callable[[str, str], None],
        format_elapsed_func: Callable[[float], str],
    ):
        """Initialize transcript exporter.

        Args:
            log_dir: Directory for session logs
            log_func: Logging function(message, level)
            format_elapsed_func: Function to format elapsed time
        """
        self.log_dir = log_dir
        self.log = log_func
        self.format_elapsed = format_elapsed_func

    def _find_builder_paths(self) -> list[Path]:
        """Find possible paths for ClaudeTranscriptBuilder.

        Returns:
            List of valid paths to search for builder
        """
        search_paths = []

        # Path 1: UVX package location
        try:
            import amplihack

            # Security: Use strict=True to prevent symlink attacks
            pkg_path = Path(amplihack.__file__).parent.resolve(strict=True)
            builders_in_pkg = (pkg_path / ".claude" / "tools" / "amplihack" / "builders").resolve(
                strict=True
            )

            # Security: Validate path is within expected package
            if not str(builders_in_pkg).startswith(str(pkg_path)):
                self.log("Security: Builders path validation failed in UVX", "DEBUG")
                raise ValueError("Path traversal detected")

            if builders_in_pkg.exists():
                search_paths.append(builders_in_pkg)
        except (ValueError, OSError) as e:
            self.log(f"Path validation failed in UVX: {type(e).__name__}", "DEBUG")
        except Exception:
            pass

        # Path 2: Project root (local development)
        try:
            # Security: Resolve and validate project root
            current_file = Path(__file__).resolve(strict=True)
            project_root = current_file.parent.parent.parent.parent
            builders_in_root = (
                project_root / ".claude" / "tools" / "amplihack" / "builders"
            ).resolve(strict=True)

            # Security: Ensure builders path is under project root
            try:
                builders_in_root.relative_to(project_root)
            except ValueError:
                self.log("Security: Path traversal detected in project root", "DEBUG")
                raise ValueError("Path traversal detected")

            if builders_in_root.exists():
                search_paths.append(builders_in_root)
        except (ValueError, OSError) as e:
            self.log(f"Path validation failed in project root: {type(e).__name__}", "DEBUG")
        except Exception:
            pass

        return search_paths

    def _load_builder_class(self) -> Optional[Any]:
        """Load ClaudeTranscriptBuilder class.

        Returns:
            ClaudeTranscriptBuilder class or None if not found
        """
        search_paths = self._find_builder_paths()

        for builders_path in search_paths:
            try:
                builder_file = builders_path / "claude_transcript_builder.py"
                if builder_file.exists():
                    spec = importlib.util.spec_from_file_location(
                        "claude_transcript_builder", builder_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.log(f"Builders: Loaded from {builders_path}", "DEBUG")
                        return module.ClaudeTranscriptBuilder
            except Exception as e:
                self.log(f"Builders: Failed from {builders_path}: {e}", "DEBUG")
                continue

        return None

    def _validate_export_path(self, builder: Any) -> None:
        """Validate that builder exports to expected location.

        Args:
            builder: ClaudeTranscriptBuilder instance

        Raises:
            ValueError: If export path doesn't match expected location
        """
        expected_session_dir = self.log_dir
        actual_session_dir = builder.session_dir

        # Check if builder's session_dir matches our expected location
        if expected_session_dir.resolve() != actual_session_dir.resolve():
            error_msg = (
                f"Transcript export path mismatch detected!\n"
                f"  Expected: {expected_session_dir}\n"
                f"  Actual:   {actual_session_dir}\n"
                f"  This usually means project root detection failed.\n"
                f"  Refusing to export to wrong location to prevent silent data loss."
            )
            self.log(error_msg, "ERROR")
            raise ValueError(error_msg)

    def _verify_exported_files(self, session_dir: Path) -> None:
        """Verify that expected transcript files were created.

        Args:
            session_dir: Directory where files should be created

        Raises:
            FileNotFoundError: If expected files are missing
        """
        expected_files = [
            session_dir / "CONVERSATION_TRANSCRIPT.md",
            session_dir / "conversation_transcript.json",
            session_dir / "codex_export.json",
        ]
        missing_files = [f for f in expected_files if not f.exists()]

        if missing_files:
            error_msg = (
                f"Transcript export verification failed!\n"
                f"Expected files were not created at {session_dir}:\n"
                + "\n".join(f"  Missing: {f.name}" for f in missing_files)
            )
            self.log(error_msg, "ERROR")
            raise FileNotFoundError(error_msg)

    def export_session(
        self,
        messages: list,
        metadata: dict,
    ) -> None:
        """Export session transcript using ClaudeTranscriptBuilder.

        Creates comprehensive transcript files in multiple formats (markdown, JSON, codex)
        using the captured messages from the session.

        Args:
            messages: List of captured messages
            metadata: Session metadata (sdk, turns, duration, etc.)

        Raises:
            ValueError: If export path validation fails
            FileNotFoundError: If exported files verification fails
        """
        try:
            # Load builder class
            ClaudeTranscriptBuilder = self._load_builder_class()

            if ClaudeTranscriptBuilder is None:
                self.log("Transcript builder not found, skipping export", "INFO")
                return

            # Create builder instance
            builder = ClaudeTranscriptBuilder(session_id=self.log_dir.name)

            if not messages:
                self.log("No messages captured for export", "DEBUG")
                return

            # Validate export path BEFORE exporting
            self._validate_export_path(builder)

            # Log where transcripts will be exported
            actual_session_dir = builder.session_dir
            self.log(f"Exporting transcripts to: {actual_session_dir}", "DEBUG")

            # Generate transcript and export
            builder.build_session_transcript(messages, metadata)
            builder.export_for_codex(messages, metadata)

            # Verify files were actually written
            self._verify_exported_files(actual_session_dir)

            # Calculate total duration for log message
            total_duration = metadata.get("total_duration_seconds", 0)
            formatted_duration = self.format_elapsed(total_duration)

            self.log(f"✓ Session transcript exported ({len(messages)} messages, {formatted_duration})")

        except (ValueError, FileNotFoundError):
            # Path mismatch or file verification failures - re-raise to alert user
            raise
        except (ImportError, AttributeError) as e:
            # Builder loading issues - log but don't crash
            self.log(f"Transcript builder unavailable: {e}", "WARNING")
        except OSError as e:
            # File system errors - log but continue
            self.log(f"File system error during transcript export: {e}", "WARNING")
        except Exception as e:
            # Unexpected errors - log with full details
            self.log(f"Unexpected error during transcript export: {type(e).__name__}: {e}", "ERROR")
