#!/usr/bin/env python3
"""Workstream launcher - Rust recipe runner execution."""
import atexit
import os
import sys
import logging
from pathlib import Path

repo_root = Path(__file__).resolve().parent
src_path = repo_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

pid_file = os.environ.get("AMPLIHACK_WORKSTREAM_PID_FILE")
if pid_file:
    pid_path = Path(pid_file)
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    pid_path.chmod(0o600)

    def _cleanup_pid_file() -> None:
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass

    atexit.register(_cleanup_pid_file)

try:
    from amplihack.recipes import run_recipe_by_name
except ImportError:
    print("ERROR: amplihack package not importable. Falling back to classic mode.")
    sys.exit(2)

recipe_context = {"issues": ["#3978", "#3963"], "repo": "amplihack-pm"}
user_context = dict(recipe_context)
user_context["task_description"] = "Resume issues #3978 and #3963. Review current branch/PR state, complete remaining development, run validation, and close out or document next-action/blocker for each issue."
user_context["repo_path"] = "."

result = run_recipe_by_name(
    "default-workflow",
    user_context=user_context,
    progress=True,
)

print()
print("=" * 60)
print("RECIPE EXECUTION RESULTS")
print("=" * 60)
for sr in result.step_results:
    print(f"  [{sr.status.value:>9}] {sr.step_id}")
print(f"\nOverall: {'SUCCESS' if result.success else 'FAILED'}")
sys.exit(0 if result.success else 1)
