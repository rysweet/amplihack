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

user_context = json.loads("{\"task_description\": \"Investigate and fix the Copilot flag issues #4166, #4167, #4144 and duplicate cluster #4136-#4139. Confirm shared root cause, land the actual fix, validate with existing tests, and handle duplicate issue consolidation.\", \"repo_path\": \".\", \"issue_number\": 4174, \"workstream_state_file\": \"/tmp/amplihack-workstreams/state/ws-4174.json\", \"workstream_progress_file\": \"/tmp/amplihack-workstreams/state/ws-4174.progress.json\"}")
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
