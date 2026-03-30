"""Copilot hook strategy compatibility layer."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import HookStrategy


class CopilotStrategy(HookStrategy):
    CONTEXT_DIR = Path("runtime") / "copilot"
    DYNAMIC_CONTEXT_FILE = CONTEXT_DIR / "dynamic_context.md"
    AGENTS_FILE = Path(".github") / "agents" / "AGENTS.md"

    def _write_with_retry(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _update_agents_file(self) -> None:
        include_line = f"@include {self.DYNAMIC_CONTEXT_FILE.as_posix()}"
        self.AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if self.AGENTS_FILE.exists():
            content = self.AGENTS_FILE.read_text(encoding="utf-8")
            if include_line in content:
                return
            updated = content.rstrip() + "\n\n" + include_line + "\n"
        else:
            updated = (
                "# GitHub Copilot Agents Context\n\n"
                "This file is managed by the compatibility hook strategy.\n\n"
                f"{include_line}\n"
            )
        self.AGENTS_FILE.write_text(updated, encoding="utf-8")

    def inject_context(self, context: str) -> dict[str, object]:
        self.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        self.AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._write_with_retry(self.DYNAMIC_CONTEXT_FILE, context)
        self._update_agents_file()
        return {}

    def power_steer(self, prompt: str, session_id: str | None = None) -> bool:
        if shutil.which("gh") is None:
            return False
        cmd = ["gh", "copilot"]
        if session_id:
            cmd.extend(["--continue", session_id])
        cmd.extend(["-p", prompt])
        try:
            subprocess.Popen(cmd)
        except OSError:
            return False
        return True
