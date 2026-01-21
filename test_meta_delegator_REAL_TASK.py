#!/usr/bin/env python3
"""
Test meta-delegator with REAL coding task
Goal: Get 100/100 score by having subprocess create actual code, tests, docs
"""
import sys
sys.path.insert(0, '/home/azureuser/src/amplihack/worktrees/feat/issue-2030-meta-delegator/src')
import os
from pathlib import Path

# Clean workspace
workspace = Path("/tmp/meta-real-coding-task")
if workspace.exists():
    import shutil
    shutil.rmtree(workspace)
workspace.mkdir(parents=True)

from amplihack.meta_delegation import run_meta_delegation

print("=" * 70)
print("META-DELEGATOR: REAL CODING TASK TEST")
print("=" * 70)
print()
print("Task: Have subprocess create a simple Python calculator module")
print("Success Criteria: Code + Tests + Documentation created")
print("Expected Score: 100/100 (all criteria met + bonuses)")
print("=" * 70)
print()

result = run_meta_delegation(
    goal="""Create a simple Python calculator module with these requirements:

1. File: calculator.py with add() and subtract() functions
2. File: test_calculator.py with at least 2 tests
3. File: README.md documenting how to use it

Each function should:
- Take two numbers
- Return the result
- Have a docstring

Keep it SIMPLE - just basic functionality, no error handling needed.
This is a learning exercise.""",

    success_criteria="""
- calculator.py file exists with add() and subtract() functions
- test_calculator.py exists with at least 2 test functions
- README.md exists with usage examples
- All files have actual content (not empty)
""",

    persona_type="guide",  # Guide will help subprocess learn
    platform="claude-code",
    timeout_minutes=10,  # Real tasks need more time
    working_directory=str(workspace),
    enable_scenarios=False,  # Keep it simple
    context="This is a learning exercise to create a basic calculator module. Focus on simplicity and completeness."
)

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Status: {result.status}")
print(f"Success Score: {result.success_score}/100")
print(f"Duration: {result.duration_seconds:.1f}s ({result.duration_seconds/60:.1f} minutes)")
print(f"Evidence Items Collected: {len(result.evidence)}")
print()

# Show what evidence was collected
if result.evidence:
    print("Evidence Collected:")
    for item in result.evidence:
        print(f"  - {item.type:20} {item.path}")
        if item.type in ['code_file', 'test_file', 'documentation']:
            print(f"    Preview: {item.excerpt[:80]}...")

# Check if files were actually created
print("\nFiles Created in Workspace:")
files_created = list(workspace.glob("*"))
for f in files_created:
    print(f"  ✅ {f.name} ({f.stat().st_size} bytes)")

if not files_created:
    print("  ⚠️  No files created")

# Show execution log excerpt
if result.execution_log:
    print(f"\nExecution Log ({len(result.execution_log)} chars total):")
    print("First 1000 chars:")
    print(result.execution_log[:1000])
    print("\n...")
    print("\nLast 1000 chars:")
    print(result.execution_log[-1000:])

print("\n" + "=" * 70)
print("ASSESSMENT")
print("=" * 70)

if result.status == "completed" and result.success_score >= 90:
    print("✅✅✅ PERFECT! Meta-delegator achieved 90+ score!")
    print("System works end-to-end for real coding tasks!")
elif result.status in ["completed", "PARTIAL"] and result.success_score >= 70:
    print("✅ SUCCESS! Meta-delegator works for real tasks!")
    print(f"Score {result.success_score}/100 indicates subprocess created most artifacts")
elif result.success_score > 0:
    print(f"⏸️  PARTIAL SUCCESS ({result.success_score}/100)")
    print("Subprocess ran but didn't complete all requirements")
else:
    print(f"❌ FAILED: {result.status}")
    if result.failure_reason:
        print(f"Reason: {result.failure_reason}")

print("=" * 70)
