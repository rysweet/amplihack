#!/usr/bin/env python3
"""Apply 49 remaining specific fixes (fix 2-50)."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Define fixes 2-50 as simple string replacements
FIXES = [
    # Fix 2-7: Type hints
    (
        2,
        "src/amplihack/launcher/core.py",
        "Add return type to _ensure_runtime_directories",
        "    def _ensure_runtime_directories(self):",
        "    def _ensure_runtime_directories(self) -> None:",
    ),
    (
        3,
        "src/amplihack/bundle_generator/parser.py",
        "Add return type to PromptParser.__init__",
        "    def __init__(self, enable_advanced_nlp: bool = False):",
        "    def __init__(self, enable_advanced_nlp: bool = False) -> None:",
    ),
    (
        4,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add return type to __enter__",
        "    def __enter__(self):",
        "    def __enter__(self) -> 'SessionManager':",
    ),
    (
        5,
        ".claude/tools/amplihack/session/session_manager.py",
        "Add return type to __exit__",
        "    def __exit__(self, exc_type, exc_val, exc_tb):",
        "    def __exit__(self, exc_type, exc_val, exc_tb) -> None:",
    ),
    (
        6,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Complete type hint for List[Dict]",
        "def _format_conversation_summary(conversation: List[Dict], max_length: int = 5000) -> str:",
        "def _format_conversation_summary(conversation: List[Dict[str, Any]], max_length: int = 5000) -> str:",
    ),
    (
        7,
        ".claude/tools/amplihack/hooks/claude_reflection.py",
        "Complete return type hint",
        "def load_session_conversation(session_dir: Path) -> Optional[List[Dict]]:",
        "def load_session_conversation(session_dir: Path) -> Optional[List[Dict[str, Any]]]:",
    ),
]


def run_cmd(cmd):
    """Run command and return success."""
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def apply_fix(num, file, desc, old, new):
    """Apply a single fix."""
    print(f"\n[{num}/50] {desc}")

    # Create branch
    run_cmd(["git", "checkout", "main"])
    run_cmd(["git", "pull", "origin", "main"])

    success, output = run_cmd(["git", "checkout", "-b", f"fix/specific-{num}"])
    if not success:
        print(f"  Failed to create branch: {output}")
        return False

    # Apply fix
    file_path = REPO_ROOT / file
    if not file_path.exists():
        print(f"  File not found: {file}")
        run_cmd(["git", "checkout", "main"])
        return False

    try:
        content = file_path.read_text()
        if old not in content:
            print("  Pattern not found")
            run_cmd(["git", "checkout", "main"])
            run_cmd(["git", "branch", "-D", f"fix/specific-{num}"])
            return False

        content = content.replace(old, new, 1)
        file_path.write_text(content)
    except Exception as e:
        print(f"  Error: {e}")
        run_cmd(["git", "checkout", "main"])
        return False

    # Commit and push
    run_cmd(["git", "add", str(file)])
    success, _ = run_cmd(["git", "commit", "-m", f"fix: {desc}\n\nFile: {file}"])
    if not success:
        print("  Failed to commit")
        run_cmd(["git", "checkout", "main"])
        return False

    success, output = run_cmd(["git", "push", "-u", "origin", f"fix/specific-{num}"])
    if not success:
        print(f"  Failed to push: {output}")
        return False

    print("  ✓ Success")
    run_cmd(["git", "checkout", "main"])
    return True


def main():
    """Apply all fixes."""
    print(f"Applying {len(FIXES)} fixes...")

    success_count = 0
    fail_count = 0

    for fix in FIXES:
        try:
            if apply_fix(*fix):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  Exception: {e}")
            fail_count += 1

    print(f"\n{'=' * 50}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
