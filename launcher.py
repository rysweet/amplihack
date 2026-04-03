#!/usr/bin/env python3
"""Workstream launcher - Rust recipe runner execution."""
import sys
import json
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

try:
    from amplihack.recipes import run_recipe_by_name
except ImportError:
    print("ERROR: amplihack package not importable. Falling back to classic mode.")
    sys.exit(2)

user_context = json.loads("{\"task_description\": \"Based on audit findings, implement a safe disablement strategy: add guard checks or disabled flags to workflows/recipes/skills/agents that depend on Anthropic, update launch paths to reject or skip Anthropic-only paths, ensure affected components fail gracefully with a clear error message rather than silently. Update any related tests and documentation to reflect the disablement.\", \"repo_path\": \".\", \"issue_number\": 4215, \"workstream_state_file\": \"/tmp/amplihack-workstreams/state/ws-4215.json\", \"workstream_progress_file\": \"/tmp/amplihack-workstreams/state/ws-4215.progress.json\"}")
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
