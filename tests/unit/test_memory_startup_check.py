"""Tests for memory_auto_install startup check.

Verifies that:
- No subprocess calls are made (PEP 668 compliance)
- Import check returns True when library is present
- Warning logged when library is absent
- amplihack-memory-lib remains a mandatory dependency in pyproject.toml
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch


class TestMemoryStartupCheck:
    """Verify ensure_memory_lib_installed() is a lazy import guard."""

    def test_returns_true_when_lib_available(self):
        """When amplihack_memory is importable, return True."""
        from importlib import reload

        import amplihack.memory_auto_install

        reload(amplihack.memory_auto_install)
        result = amplihack.memory_auto_install.ensure_memory_lib_installed()
        assert result is True

    def test_returns_false_when_lib_absent(self):
        """When amplihack_memory is not importable, return False with warning."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "amplihack_memory":
                raise ImportError("No module named 'amplihack_memory'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            from importlib import reload

            import amplihack.memory_auto_install

            reload(amplihack.memory_auto_install)
            result = amplihack.memory_auto_install.ensure_memory_lib_installed()
            assert result is False

    def test_logs_warning_with_repair_instructions_when_absent(self, caplog):
        """Warning message must include actionable repair commands."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "amplihack_memory":
                raise ImportError("No module named 'amplihack_memory'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            from importlib import reload

            import amplihack.memory_auto_install

            reload(amplihack.memory_auto_install)
            with caplog.at_level(logging.WARNING):
                amplihack.memory_auto_install.ensure_memory_lib_installed()

        assert "amplihack-memory-lib" in caplog.text
        assert "pip install" in caplog.text or "not importable" in caplog.text

    def test_result_is_cached(self):
        """Second call returns cached result without re-importing."""
        from importlib import reload

        import amplihack.memory_auto_install

        reload(amplihack.memory_auto_install)
        first = amplihack.memory_auto_install.ensure_memory_lib_installed()
        second = amplihack.memory_auto_install.ensure_memory_lib_installed()
        assert first == second

    def test_no_subprocess_import_in_module(self):
        """memory_auto_install.py must not import subprocess."""
        source = Path("src/amplihack/memory_auto_install.py").read_text()
        assert "import subprocess" not in source

    def test_no_subprocess_calls_in_module(self):
        """memory_auto_install.py must not call subprocess or os.system."""
        source = Path("src/amplihack/memory_auto_install.py").read_text()
        assert "subprocess.run" not in source
        assert "subprocess.Popen" not in source
        assert "os.system" not in source
        assert "sys.executable" not in source


class TestMemoryLibIsMandatoryDep:
    """Verify amplihack-memory-lib stays in [project.dependencies]."""

    def test_memory_lib_in_project_dependencies(self):
        """amplihack-memory-lib must be a mandatory dep, not optional."""
        import tomllib

        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        deps = data["project"]["dependencies"]
        memory_deps = [d for d in deps if "amplihack-memory-lib" in d]
        assert len(memory_deps) == 1, (
            f"amplihack-memory-lib must be in [project.dependencies], found: {memory_deps}"
        )

    def test_memory_lib_not_in_optional_dependencies(self):
        """amplihack-memory-lib must NOT be optional."""
        import tomllib

        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        optional = data.get("project", {}).get("optional-dependencies", {})
        for group_name, group_deps in optional.items():
            for dep in group_deps:
                assert "amplihack-memory-lib" not in dep, (
                    f"amplihack-memory-lib found in optional group '{group_name}' — "
                    "it must be a mandatory dependency"
                )
