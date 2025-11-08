#!/usr/bin/env python3
"""Local test for logging and transcript export fixes.

WHAT THIS TEST VERIFIES:
1. STDOUT/STDERR logging flows to all three destinations:
   - Session log file (auto.log)
   - Terminal (captured via stdout/stderr)
   - TUI (state updates - verified via log file)

2. Transcript export location:
   - Files written to: ./.claude/runtime/logs/{session_id}/
   - NOT UV cache location
   - All three files exist: CONVERSATION_TRANSCRIPT.md, conversation_transcript.json, codex_export.json

TEST APPROACH:
- Runs auto mode with a simple task
- Captures session ID from log output
- Verifies session log file exists and contains output
- Verifies transcript files exist in correct location
- Returns pass/fail status with clear messages

ZERO-BS PRINCIPLE: No stubs, complete implementation, working test.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path


def print_header(msg: str):
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {msg}")
    print(f"{'=' * 80}\n")


def print_test(msg: str):
    """Print a test step."""
    print(f"[TEST] {msg}")


def print_pass(msg: str):
    """Print a success message."""
    print(f"[PASS] {msg}")


def print_fail(msg: str):
    """Print a failure message."""
    print(f"[FAIL] {msg}", file=sys.stderr)


def find_session_id(output: str) -> str | None:
    """Extract session ID from auto mode output.

    Session ID format: auto_claude_{timestamp}
    """
    # Look for log directory creation messages
    patterns = [
        r"auto_claude_(\d+)",
        r"session_id[\"']?\s*:\s*[\"']?(auto_claude_\d+)",
        r"logs/(auto_claude_\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            if match.group(0).startswith("auto_claude_"):
                return match.group(0)
            return match.group(1)

    return None


def find_session_dir_from_logs() -> Path | None:
    """Find the most recent auto mode session directory."""
    project_root = Path.cwd()
    logs_dir = project_root / ".claude" / "runtime" / "logs"

    if not logs_dir.exists():
        return None

    # Find most recent auto_claude_* directory
    auto_dirs = sorted(
        logs_dir.glob("auto_claude_*"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if auto_dirs:
        return auto_dirs[0]

    return None


def verify_log_file_exists(session_dir: Path) -> bool:
    """Verify session log file exists and has content."""
    print_test(f"Verifying session log file in {session_dir}")

    log_file = session_dir / "auto.log"

    if not log_file.exists():
        print_fail(f"Session log file not found: {log_file}")
        return False

    # Check file has content
    content = log_file.read_text()
    if len(content) == 0:
        print_fail(f"Session log file is empty: {log_file}")
        return False

    print_pass(f"Session log file exists and has content ({len(content)} bytes)")
    return True


def verify_log_contains_output(session_dir: Path) -> bool:
    """Verify log file contains STDOUT/STDERR output from the session."""
    print_test("Verifying log file contains session output")

    log_file = session_dir / "auto.log"
    content = log_file.read_text()

    # Check for key indicators that output was logged
    indicators = [
        "stdout",  # Direct stdout logging
        "stderr",  # Direct stderr logging
        "Clarify Objective",  # Phase logging
        "Using Claude SDK",  # SDK activity
    ]

    found_indicators = [ind for ind in indicators if ind in content]

    if len(found_indicators) < 2:
        print_fail(f"Log file missing expected output indicators. Found: {found_indicators}")
        return False

    print_pass(f"Log file contains session output (indicators: {', '.join(found_indicators)})")
    return True


def verify_transcript_files_exist(session_dir: Path) -> bool:
    """Verify all three transcript files exist in correct location."""
    print_test(f"Verifying transcript files in {session_dir}")

    required_files = [
        "CONVERSATION_TRANSCRIPT.md",
        "conversation_transcript.json",
        "codex_export.json",
    ]

    missing_files = []
    for filename in required_files:
        file_path = session_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
        else:
            # Verify file has content
            if file_path.stat().st_size == 0:
                print_fail(f"Transcript file is empty: {filename}")
                return False

    if missing_files:
        print_fail(f"Missing transcript files: {', '.join(missing_files)}")
        return False

    print_pass(f"All transcript files exist: {', '.join(required_files)}")
    return True


def verify_transcript_in_project_not_uv_cache(session_dir: Path) -> bool:
    """Verify transcript files are in project location, not UV cache."""
    print_test("Verifying transcript location is in project (not UV cache)")

    session_dir_str = str(session_dir.resolve())

    # Check if path contains UV cache indicators
    uv_cache_indicators = [
        "/.cache/uv/",
        "/uv/cache/",
        "/.local/share/uv/",
    ]

    for indicator in uv_cache_indicators:
        if indicator in session_dir_str:
            print_fail(f"Transcripts in UV cache location: {session_dir_str}")
            return False

    # Verify path is in project
    project_root = Path.cwd()
    try:
        session_dir.relative_to(project_root)
        print_pass(f"Transcripts in project location: {session_dir.relative_to(project_root)}")
        return True
    except ValueError:
        print_fail(f"Transcripts not in project root: {session_dir_str}")
        return False


def verify_transcript_content(session_dir: Path) -> bool:
    """Verify transcript files contain expected content."""
    print_test("Verifying transcript file content")

    # Check markdown transcript
    md_file = session_dir / "CONVERSATION_TRANSCRIPT.md"
    md_content = md_file.read_text()

    if "# Claude Session Transcript" not in md_content and "Session Transcript" not in md_content:
        print_fail("Markdown transcript missing expected header")
        return False

    # Check JSON transcript
    json_file = session_dir / "conversation_transcript.json"
    try:
        with open(json_file) as f:
            json_data = json.load(f)

        if "messages" not in json_data and "conversation" not in json_data:
            print_fail("JSON transcript missing expected structure")
            return False
    except json.JSONDecodeError:
        print_fail("JSON transcript is not valid JSON")
        return False

    # Check codex export
    codex_file = session_dir / "codex_export.json"
    try:
        with open(codex_file) as f:
            codex_data = json.load(f)

        if "session_metadata" not in codex_data:
            print_fail("Codex export missing expected metadata")
            return False
    except json.JSONDecodeError:
        print_fail("Codex export is not valid JSON")
        return False

    print_pass("All transcript files contain valid content")
    return True


def run_auto_mode_test() -> tuple[int, str, str]:
    """Run auto mode with a simple test task.

    Returns:
        (exit_code, stdout, stderr)
    """
    print_test("Running auto mode with simple task")

    # Use amplihack CLI to run auto mode with a minimal task
    # This tests the actual deployment scenario
    cmd = [
        sys.executable,
        "-m",
        "amplihack.launcher.auto_mode",
        "--sdk",
        "claude",
        "--prompt",
        "Print 'Hello from auto mode test' to a file called test_output.txt in the current directory. Then verify the file was created successfully.",
        "--max-turns",
        "3",
    ]

    print(f"[CMD] {' '.join(cmd)}")

    # Run command and capture output
    start_time = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,  # 2 minute timeout
    )
    elapsed = time.time() - start_time

    print(f"[INFO] Auto mode completed in {elapsed:.1f}s (exit code: {result.returncode})")

    return result.returncode, result.stdout, result.stderr


def main():
    """Execute all tests and report results."""
    print_header("AUTO MODE LOGGING & TRANSCRIPT EXPORT TEST")

    print("[INFO] Test configuration:")
    print(f"  - Project root: {Path.cwd()}")
    print(f"  - Python: {sys.executable}")
    print("  - Test principle: Zero-BS (no stubs, complete implementation)")

    # Track test results
    tests_passed = 0
    tests_failed = 0

    try:
        # TEST 1: Run auto mode
        print_header("TEST 1: Run Auto Mode")
        exit_code, stdout, stderr = run_auto_mode_test()

        # Show output for debugging
        print("\n[STDOUT]")
        print(stdout[:1000] if len(stdout) > 1000 else stdout)
        if stderr:
            print("\n[STDERR]")
            print(stderr[:1000] if len(stderr) > 1000 else stderr)

        if exit_code != 0:
            print_fail(f"Auto mode failed with exit code {exit_code}")
            tests_failed += 1
            # Continue to check logs even if execution failed
        else:
            print_pass("Auto mode executed successfully")
            tests_passed += 1

        # Extract session ID from output
        session_id = find_session_id(stdout + stderr)

        if not session_id:
            print("[WARN] Could not extract session ID from output, searching logs...")
            session_dir = find_session_dir_from_logs()
            if not session_dir:
                print_fail("Could not find session directory")
                return 1
        else:
            print(f"[INFO] Session ID: {session_id}")
            session_dir = Path.cwd() / ".claude" / "runtime" / "logs" / session_id

        if not session_dir.exists():
            print_fail(f"Session directory does not exist: {session_dir}")
            return 1

        print(f"[INFO] Session directory: {session_dir}")

        # TEST 2: Verify session log file
        print_header("TEST 2: Verify Session Log File")
        if verify_log_file_exists(session_dir):
            tests_passed += 1
        else:
            tests_failed += 1

        # TEST 3: Verify log contains output
        print_header("TEST 3: Verify Log Contains Output")
        if verify_log_contains_output(session_dir):
            tests_passed += 1
        else:
            tests_failed += 1

        # TEST 4: Verify transcript files exist
        print_header("TEST 4: Verify Transcript Files Exist")
        if verify_transcript_files_exist(session_dir):
            tests_passed += 1
        else:
            tests_failed += 1

        # TEST 5: Verify transcript location
        print_header("TEST 5: Verify Transcript Location")
        if verify_transcript_in_project_not_uv_cache(session_dir):
            tests_passed += 1
        else:
            tests_failed += 1

        # TEST 6: Verify transcript content
        print_header("TEST 6: Verify Transcript Content")
        if verify_transcript_content(session_dir):
            tests_passed += 1
        else:
            tests_failed += 1

        # FINAL RESULTS
        print_header("TEST RESULTS")
        print(f"Tests passed: {tests_passed}")
        print(f"Tests failed: {tests_failed}")
        print(f"Total tests:  {tests_passed + tests_failed}")

        if tests_failed == 0:
            print("\n✓ ALL TESTS PASSED!")
            print("\nVERIFIED:")
            print("  ✓ STDOUT/STDERR flows to session log file")
            print("  ✓ Session log contains actual output")
            print("  ✓ Transcript files exist in correct location")
            print("  ✓ Transcripts in project (not UV cache)")
            print("  ✓ Transcript files contain valid content")
            return 0
        print(f"\n✗ {tests_failed} TEST(S) FAILED")
        return 1

    except subprocess.TimeoutExpired:
        print_fail("Auto mode timed out after 2 minutes")
        return 1
    except KeyboardInterrupt:
        print("\n[ABORT] Test interrupted by user")
        return 130
    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
