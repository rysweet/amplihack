"""Claude CLI runner for AI-powered analysis."""

import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.parent.parent


def run_claude(prompt: str, timeout: int = 300) -> dict[str, Any]:
    """Run Claude CLI with prompt and return result.

    Args:
        prompt: Prompt to send to Claude
        timeout: Timeout in seconds

    Returns:
        Dictionary with exit_code, output, stderr
    """
    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "exit_code": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "output": "", "stderr": "Timeout"}
    except Exception as e:
        return {"exit_code": -1, "output": "", "stderr": str(e)}
