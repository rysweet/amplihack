"""Tests for the visualizer.py CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "visualizer.py"


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_cli_produces_per_language_files(tmp_path: Path):
    src = tmp_path / "src"
    out = tmp_path / "out"
    out.mkdir()
    _write(src / "a.py", "import os\n")
    _write(src / "b.ts", "import x from './y';\n")

    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(src), "--output", str(out), "--basename", "diagram"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    files = {p.name for p in out.iterdir()}
    assert "diagram-python.mmd" in files
    assert "diagram-typescript.mmd" in files
    for f in files:
        assert (out / f).read_text().strip() != ""


def test_cli_combined_flag_produces_combined_file(tmp_path: Path):
    src = tmp_path / "src"
    out = tmp_path / "out"
    out.mkdir()
    _write(src / "a.py", "import os\n")
    _write(src / "b.ts", "import x from './y';\n")

    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(src),
            "--output",
            str(out),
            "--basename",
            "diagram",
            "--combined",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert (out / "diagram-combined.mmd").exists()
    assert (out / "diagram-combined.mmd").read_text().strip() != ""


def test_cli_rejects_bad_basename(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    _write(src / "a.py", "x=1\n")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(src), "--basename", "../evil"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode != 0


def test_cli_rejects_nonexistent_path(tmp_path: Path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "nope")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode != 0
