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

user_context = json.loads("{\"task_description\": \"Verify and resolve all merge-ready criteria for PR #3952 (fix(recipes): add idempotency guards to step-03-create-issue): check current branch state, CI/check status, review readiness, mergeability blockers. Apply any required code/test/doc fixes and validate with existing checks. Do not touch unrelated dirty files.\", \"repo_path\": \".\", \"issue_number\": 4173, \"workstream_state_file\": \"/tmp/amplihack-workstreams/state/ws-4173.json\", \"workstream_progress_file\": \"/tmp/amplihack-workstreams/state/ws-4173.progress.json\"}")
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
