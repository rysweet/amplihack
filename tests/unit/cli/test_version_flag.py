"""Tests for the --version flag on the amplihack CLI (issue #3081).

TDD: These tests FAIL until parser.add_argument('--version', ...) is added
to create_parser() in src/amplihack/cli.py.

The --version flag must:
- Be accepted by the top-level parser (not as a subcommand)
- Exit with code 0
- Print 'amplihack <version>' to stdout (argparse action='version' uses stdout)
- Be distinct from the 'version' subcommand (both must coexist)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Resolve the amploxy repo root so we can run it as a module
_AMPLOXY_ROOT = Path(__file__).resolve().parents[4]  # tests/unit/cli -> amploxy root


class TestVersionFlagParser:
    """Unit tests for argparse --version flag setup."""

    def test_version_flag_causes_system_exit(self):
        """--version must trigger SystemExit (standard argparse action='version' behaviour)."""
        from amplihack.cli import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])

        # argparse action='version' exits with code 0
        assert exc_info.value.code == 0

    def test_version_flag_outputs_amplihack_prefix(self, capsys):
        """--version output must start with 'amplihack '."""
        from amplihack.cli import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

        captured = capsys.readouterr()
        # argparse writes version to stdout
        combined = captured.out + captured.err
        assert combined.strip().startswith("amplihack "), (
            f"Expected output starting with 'amplihack ', got: {combined!r}"
        )

    def test_version_flag_includes_version_number(self, capsys):
        """--version output must include a non-empty version string."""
        from amplihack import __version__
        from amplihack.cli import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert __version__ in combined, (
            f"Expected __version__ {__version__!r} in output, got: {combined!r}"
        )

    def test_version_flag_coexists_with_version_subcommand(self):
        """--version flag and 'version' subcommand must both be parseable."""
        from amplihack.cli import create_parser

        parser = create_parser()

        # Subcommand 'version' should parse without raising
        args = parser.parse_args(["version"])
        assert args.command == "version"

        # --version flag should trigger SystemExit (not an error)
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestVersionFlagSubprocess:
    """Integration tests: run the CLI as a subprocess and check exit code / output."""

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        """Run 'python -m amplihack.cli <args>' from the amploxy repo root."""
        return subprocess.run(
            [sys.executable, "-m", "amplihack.cli", *args],
            capture_output=True,
            text=True,
            cwd=str(_AMPLOXY_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(_AMPLOXY_ROOT / "src")},
        )

    def test_version_flag_exits_zero(self):
        """'amplihack --version' must exit with code 0."""
        result = self._run_cli("--version")
        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    def test_version_flag_prints_version_to_output(self):
        """'amplihack --version' must print 'amplihack <version>' to stdout or stderr."""
        result = self._run_cli("--version")
        combined = result.stdout + result.stderr
        assert "amplihack" in combined.lower(), f"Expected 'amplihack' in output, got: {combined!r}"
