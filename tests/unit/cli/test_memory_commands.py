"""Regression tests for the supported top-level memory CLI surface."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
_CLI_PATH = _SRC_ROOT / "amplihack" / "cli.py"

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("amplihack._cli_entrypoint_test", _CLI_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestMemoryCommandParser:
    def test_memory_tree_accepts_sqlite_backend_flag(self):
        cli_module = _load_cli_module()
        parser = cli_module.create_parser()

        args = parser.parse_args(["memory", "tree", "--backend", "sqlite"])
        assert args.command == "memory"
        assert args.memory_command == "tree"
        assert args.backend == "sqlite"

    def test_memory_clean_subcommand_is_supported(self):
        cli_module = _load_cli_module()
        parser = cli_module.create_parser()

        args = parser.parse_args(["memory", "clean", "--pattern", "test_*"])
        assert args.command == "memory"
        assert args.memory_command == "clean"
        assert args.pattern == "test_*"
        assert args.backend == "sqlite"
        assert args.no_dry_run is False
        assert args.confirm is False


class TestMemoryImportRuntime:
    def test_memory_import_rejects_kuzu_merge_early(self, tmp_path, capsys):
        cli_module = _load_cli_module()
        kuzu_input = tmp_path / "kuzu_export"
        kuzu_input.mkdir()

        exit_code = cli_module.main(
            [
                "memory",
                "import",
                "--agent",
                "test-agent",
                "--input",
                str(kuzu_input),
                "--format",
                "kuzu",
                "--merge",
            ]
        )

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "--merge is not supported with --format kuzu" in captured.out
