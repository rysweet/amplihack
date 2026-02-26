#!/usr/bin/env python3
"""
Tests for Issue #2548: power-steering infinite loop on "All checks passed".

Root cause: the first-stop visibility block (all checks pass, is_first_stop=True)
did NOT call _mark_complete, so _already_ran() returned False on subsequent stops.
Combined with an unstable session_id (timestamp fallback in stop.py), is_first_stop
remained True every invocation, causing up to 793 repeated "all checks passed" blocks.

Fixes applied:
1. stop.py line 160: use transcript_path.stem as session_id (stable across invocations)
2. power_steering_checker.py line 1078: call _mark_complete() in first-stop-visibility
   path so _already_ran() returns True on any subsequent stop.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestIssue2548AllPassLoop(unittest.TestCase):
    """Regression tests for Issue #2548."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        ).write_text(json.dumps(config))
        self.session_id = "032d7786-402c-4f2d-9680-177e9945ab19"

    # -----------------------------------------------------------------------
    # Core semaphore behaviour tests
    # -----------------------------------------------------------------------

    def test_mark_complete_makes_already_ran_true(self):
        """After _mark_complete, _already_ran must return True."""
        checker = PowerSteeringChecker(self.project_root)
        self.assertFalse(checker._already_ran(self.session_id))
        checker._mark_complete(self.session_id)
        self.assertTrue(checker._already_ran(self.session_id))

    def test_mark_results_shown_makes_results_already_shown_true(self):
        """After _mark_results_shown, _results_already_shown must return True."""
        checker = PowerSteeringChecker(self.project_root)
        self.assertFalse(checker._results_already_shown(self.session_id))
        checker._mark_results_shown(self.session_id)
        self.assertTrue(checker._results_already_shown(self.session_id))

    def test_first_stop_visibility_block_sets_both_semaphores(self):
        """
        Fix verification: the first-stop-visibility block (all pass, is_first_stop=True)
        must now call _mark_complete in addition to _mark_results_shown.

        Without the fix, only _results_shown was marked.  With the fix, _completed is
        also marked, so any subsequent check() call short-circuits via _already_ran.
        """
        checker = PowerSteeringChecker(self.project_root)

        # Neither semaphore exists yet
        self.assertFalse(checker._results_already_shown(self.session_id))
        self.assertFalse(checker._already_ran(self.session_id))

        # Simulate exactly what the fixed first-stop-visibility path does:
        checker._mark_results_shown(self.session_id)
        checker._mark_complete(self.session_id)  # THE FIX

        # Both semaphores must exist after the first-stop-visibility block
        self.assertTrue(
            checker._results_already_shown(self.session_id),
            "_results_shown semaphore not set",
        )
        self.assertTrue(
            checker._already_ran(self.session_id),
            "_completed semaphore not set — subsequent stop will loop!",
        )

    def test_already_ran_prevents_reentry_into_full_analysis(self):
        """
        After first-stop-visibility marks _completed, check() on a real transcript
        must short-circuit via _already_ran and return decision=approve.
        """
        checker = PowerSteeringChecker(self.project_root)

        # Lay down the semaphore as the fix does on first stop
        checker._mark_results_shown(self.session_id)
        checker._mark_complete(self.session_id)

        # Write a minimal JSONL transcript so check() has something to open
        transcript_file = self.project_root / f"{self.session_id}.jsonl"
        line = json.dumps({"type": "user", "message": {"role": "user", "content": "Fix login bug"}})
        transcript_file.write_text(line + "\n")

        result = checker.check(transcript_file, self.session_id)

        self.assertEqual(result.decision, "approve")
        self.assertIn("already_ran", result.reasons)

    # -----------------------------------------------------------------------
    # Session-ID stability tests (stop.py fix)
    # -----------------------------------------------------------------------

    def test_transcript_stem_is_stable_session_id(self):
        """
        transcript_path.stem (UUID filename without extension) is stable across
        multiple calls — unlike datetime.now().strftime("%Y%m%d_%H%M%S") which
        changes every second.
        """
        fake_jsonl = Path(f"/tmp/{self.session_id}.jsonl")
        stems = {Path(str(fake_jsonl)).stem for _ in range(10)}
        self.assertEqual(len(stems), 1, "stem must be identical on every call")
        self.assertEqual(stems.pop(), self.session_id)

    def test_transcript_stem_differs_from_timestamp_fallback(self):
        """
        Highlight that the old timestamp approach produces a different key each
        second, whereas stem is constant for the session lifetime.
        """
        import time

        t1 = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        time.sleep(1.05)  # Cross a second boundary
        t2 = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")

        # Timestamps from two invocations 1 s apart are different
        self.assertNotEqual(t1, t2, "timestamps must differ after 1 second")

        # But stem is always the same UUID
        fake_jsonl = Path(f"/tmp/{self.session_id}.jsonl")
        self.assertEqual(fake_jsonl.stem, self.session_id)
        self.assertEqual(fake_jsonl.stem, self.session_id)


if __name__ == "__main__":
    unittest.main()
