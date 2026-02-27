"""
Tests for amplifier-bundle/tools/session_tree.py

Covers: depth enforcement, max-session limits,
concurrent access (via locking), env var propagation.
"""

import json
import os
import sys
import time
import threading
import unittest
from pathlib import Path

# Point at the amplifier-bundle tools directory
sys.path.insert(
    0,
    str(Path(__file__).parent.parent / "amplifier-bundle" / "tools"),
)
import session_tree as st


def _fresh_env(**overrides) -> dict:
    """Return a clean env dict for patching get_tree_context."""
    return {
        "AMPLIHACK_TREE_ID": overrides.get("tree_id", ""),
        "AMPLIHACK_SESSION_ID": overrides.get("session_id", ""),
        "AMPLIHACK_SESSION_DEPTH": str(overrides.get("depth", 0)),
        "AMPLIHACK_MAX_DEPTH": str(overrides.get("max_depth", 3)),
        "AMPLIHACK_MAX_SESSIONS": str(overrides.get("max_sessions", 10)),
    }


class TestDepthEnforcement(unittest.TestCase):
    """Max depth of 3 must be enforced."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self) -> str:
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_root_session_is_allowed(self):
        result = st.check_can_spawn(tree_id="", depth=0)
        self.assertTrue(result["allowed"], result["reason"])

    def test_depth_1_is_allowed(self):
        result = st.check_can_spawn(tree_id="", depth=1)
        self.assertTrue(result["allowed"])

    def test_depth_2_is_allowed(self):
        result = st.check_can_spawn(tree_id="", depth=2)
        self.assertTrue(result["allowed"])

    def test_depth_3_spawning_is_blocked(self):
        """At depth 3, spawning children (depth 4) is blocked."""
        result = st.check_can_spawn(tree_id="", depth=3)
        self.assertFalse(result["allowed"])
        self.assertIn("max_depth", result["reason"])

    def test_custom_max_depth_via_env(self):
        """AMPLIHACK_MAX_DEPTH overrides the default."""
        saved = os.environ.get("AMPLIHACK_MAX_DEPTH")
        os.environ["AMPLIHACK_MAX_DEPTH"] = "1"
        try:
            result = st.check_can_spawn(tree_id="", depth=1)
            self.assertFalse(result["allowed"])
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_DEPTH", None)
            else:
                os.environ["AMPLIHACK_MAX_DEPTH"] = saved

    def test_depth_zero_spawning_creates_child_at_depth_1(self):
        """child_depth = depth + 1 must be <= max_depth to be allowed."""
        result = st.check_can_spawn(tree_id="", depth=0)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["depth"], 0)


class TestMaxSessionsLimit(unittest.TestCase):
    """Active session count must be enforced."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self) -> str:
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_new_tree_is_always_allowed(self):
        result = st.check_can_spawn(tree_id="nonexistent-tree-xyz", depth=0)
        self.assertTrue(result["allowed"])

    def test_exceeding_max_sessions_blocks(self):
        tree = self._unique_tree()
        max_s = 3
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = str(max_s)
        try:
            # Register max_s active sessions
            for i in range(max_s):
                st.register_session(f"session-{i}", tree_id=tree, depth=0)
            # Now check — should be blocked
            result = st.check_can_spawn(tree_id=tree, depth=0)
            self.assertFalse(result["allowed"])
            self.assertIn("max_sessions", result["reason"].lower())
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
            else:
                os.environ["AMPLIHACK_MAX_SESSIONS"] = saved

    def test_completing_a_session_frees_capacity(self):
        tree = self._unique_tree()
        max_s = 2
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = str(max_s)
        try:
            st.register_session("s1", tree_id=tree, depth=0)
            st.register_session("s2", tree_id=tree, depth=0)
            # At capacity
            self.assertFalse(st.check_can_spawn(tree_id=tree, depth=0)["allowed"])
            # Complete one session
            st.complete_session("s1", tree_id=tree)
            # Now allowed
            self.assertTrue(st.check_can_spawn(tree_id=tree, depth=0)["allowed"])
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
            else:
                os.environ["AMPLIHACK_MAX_SESSIONS"] = saved


class TestSessionRegistration(unittest.TestCase):
    """register_session must track parent-child relationships."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self) -> str:
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_register_creates_state_file(self):
        tree = self._unique_tree()
        st.register_session("root", tree_id=tree, depth=0)
        state = st._load(tree)
        self.assertIn("root", state["sessions"])

    def test_register_records_depth(self):
        tree = self._unique_tree()
        st.register_session("s", tree_id=tree, depth=2)
        state = st._load(tree)
        self.assertEqual(state["sessions"]["s"]["depth"], 2)

    def test_register_links_child_to_parent(self):
        tree = self._unique_tree()
        st.register_session("parent", tree_id=tree, depth=0)
        st.register_session("child", tree_id=tree, parent_id="parent", depth=1)
        state = st._load(tree)
        self.assertIn("child", state["sessions"]["parent"]["children"])
        self.assertEqual(state["sessions"]["child"]["parent"], "parent")

    def test_complete_marks_status(self):
        tree = self._unique_tree()
        st.register_session("s", tree_id=tree, depth=0)
        st.complete_session("s", tree_id=tree)
        state = st._load(tree)
        self.assertEqual(state["sessions"]["s"]["status"], "completed")

    def test_complete_nonexistent_session_is_silent(self):
        """complete_session with unknown session_id must not raise."""
        tree = self._unique_tree()
        st.register_session("real", tree_id=tree, depth=0)
        st.complete_session("nonexistent", tree_id=tree)  # Must not raise
        state = st._load(tree)
        self.assertEqual(state["sessions"]["real"]["status"], "active")

    def test_register_raises_runtime_error_when_depth_exceeds_max(self):
        """register_session must raise RuntimeError when depth > max_depth."""
        tree = self._unique_tree()
        saved = os.environ.get("AMPLIHACK_MAX_DEPTH")
        os.environ["AMPLIHACK_MAX_DEPTH"] = "2"
        try:
            with self.assertRaises(RuntimeError) as ctx:
                st.register_session("deep", tree_id=tree, depth=3)
            self.assertIn("max_depth", str(ctx.exception))
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_DEPTH", None)
            else:
                os.environ["AMPLIHACK_MAX_DEPTH"] = saved

    def test_register_session_raises_on_capacity_overflow(self):
        """register_session raises RuntimeError when session count exceeds max_sessions."""
        tree = self._unique_tree()
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = "2"
        try:
            st.register_session("s1", tree_id=tree, depth=0)
            st.register_session("s2", tree_id=tree, depth=0)
            with self.assertRaises(RuntimeError) as ctx:
                st.register_session("s3", tree_id=tree, depth=0)
            self.assertIn("max_sessions", str(ctx.exception))
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
            else:
                os.environ["AMPLIHACK_MAX_SESSIONS"] = saved

    def test_register_allows_session_at_exactly_max_depth(self):
        """register_session uses depth > max_depth (strict); depth==max_depth is allowed."""
        tree = self._unique_tree()
        saved = os.environ.get("AMPLIHACK_MAX_DEPTH")
        os.environ["AMPLIHACK_MAX_DEPTH"] = "2"
        try:
            # depth=2 with max_depth=2: 2 > 2 is False -> should not raise
            result = st.register_session("leaf", tree_id=tree, depth=2)
            self.assertEqual(result["depth"], 2)
            state = st._load(tree)
            self.assertEqual(state["sessions"]["leaf"]["status"], "active")
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_DEPTH", None)
            else:
                os.environ["AMPLIHACK_MAX_DEPTH"] = saved


class TestGetStatus(unittest.TestCase):
    """get_status returns a useful tree summary."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self) -> str:
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_status_counts_correctly(self):
        tree = self._unique_tree()
        st.register_session("a", tree_id=tree, depth=0)
        st.register_session("b", tree_id=tree, depth=0)
        st.complete_session("a", tree_id=tree)

        status = st.get_status(tree)
        self.assertEqual(status["tree_id"], tree)
        self.assertIn("b", status["active"])
        self.assertIn("a", status["completed"])
        # queued key should not be present anymore
        self.assertNotIn("queued", status)


class TestPathTraversalRejection(unittest.TestCase):
    """Security: invalid tree_ids must be rejected."""

    def test_path_traversal_tree_id_rejected(self):
        with self.assertRaises((ValueError, Exception)):
            st.register_session("s", tree_id="../../etc/evil", depth=0)

    def test_empty_tree_id_rejected(self):
        with self.assertRaises((ValueError, Exception)):
            st._validate_tree_id("")


class TestConcurrentAccess(unittest.TestCase):
    """Concurrent register/complete operations must not corrupt state."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self) -> str:
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_concurrent_register_session_no_corruption(self):
        """10 threads registering simultaneously must not corrupt state."""
        tree = self._unique_tree()
        # Use large enough max_sessions to avoid blocking
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = "20"
        errors = []

        def register(sid):
            try:
                st.register_session(sid, tree_id=tree, depth=0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(f"s{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual([], errors, f"Unexpected errors: {errors}")
        state = st._load(tree)
        self.assertEqual(len(state["sessions"]), 10, "All 10 sessions must be registered")

        # Restore
        if saved is None:
            os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
        else:
            os.environ["AMPLIHACK_MAX_SESSIONS"] = saved

    def test_concurrent_register_respects_max_sessions(self):
        """When 5 threads compete for 3 slots, exactly 3 register and 2 raise."""
        tree = self._unique_tree()
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = "3"
        results = {"ok": [], "err": []}
        lock = threading.Lock()

        def register(sid):
            try:
                st.register_session(sid, tree_id=tree, depth=0)
                with lock:
                    results["ok"].append(sid)
            except RuntimeError:
                with lock:
                    results["err"].append(sid)

        threads = [threading.Thread(target=register, args=(f"s{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results["ok"]), 3, f"Exactly 3 should succeed, got: {results}")
        self.assertEqual(len(results["err"]), 2, f"Exactly 2 should fail, got: {results}")

        if saved is None:
            os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
        else:
            os.environ["AMPLIHACK_MAX_SESSIONS"] = saved


class TestTTLPruning(unittest.TestCase):
    """Verify _save() prunes stale sessions according to TTL rules."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self):
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_old_completed_session_pruned(self):
        tree = self._unique_tree()
        st.register_session("old", tree_id=tree, depth=0)
        st.complete_session("old", tree_id=tree)
        # Backdate completed_at to 25 hours ago
        state = st._load(tree)
        state["sessions"]["old"]["completed_at"] = time.time() - (25 * 3600)
        st._save(tree, state)  # This triggers pruning
        state_after = st._load(tree)
        self.assertNotIn("old", state_after["sessions"],
            "Completed session older than 24h must be pruned")

    def test_recent_completed_session_preserved(self):
        tree = self._unique_tree()
        st.register_session("recent", tree_id=tree, depth=0)
        st.complete_session("recent", tree_id=tree)
        # completed_at is now — should NOT be pruned
        state_after = st._load(tree)
        self.assertIn("recent", state_after["sessions"],
            "Recently completed session must not be pruned")

    def test_leaked_active_session_pruned_after_4h(self):
        tree = self._unique_tree()
        st.register_session("leaked", tree_id=tree, depth=0)
        # Backdate started_at to 5 hours ago
        state = st._load(tree)
        state["sessions"]["leaked"]["started_at"] = time.time() - (5 * 3600)
        st._save(tree, state)  # This triggers active pruning
        state_after = st._load(tree)
        self.assertNotIn("leaked", state_after["sessions"],
            "Active session older than 4h must be pruned as leaked")

    def test_fresh_active_session_preserved(self):
        tree = self._unique_tree()
        st.register_session("fresh", tree_id=tree, depth=0)
        # started_at is now — should NOT be pruned
        state_after = st._load(tree)
        self.assertIn("fresh", state_after["sessions"],
            "Fresh active session must not be pruned")

    def test_active_session_missing_started_at_is_pruned(self):
        """Active sessions with no started_at are treated as epoch 0 and always pruned."""
        tree = self._unique_tree()
        st.register_session("no-ts", tree_id=tree, depth=0)
        state = st._load(tree)
        del state["sessions"]["no-ts"]["started_at"]  # Remove the timestamp
        st._save(tree, state)
        # _save() triggers TTL pruning; session with no started_at should be pruned
        state_after = st._load(tree)
        self.assertNotIn("no-ts", state_after["sessions"],
            "Active session with missing started_at must be pruned")

    def test_completed_session_missing_completed_at_is_pruned(self):
        """Completed sessions with no completed_at default to 0 (epoch) — always pruned."""
        tree = self._unique_tree()
        st.register_session("no-ct", tree_id=tree, depth=0)
        st.complete_session("no-ct", tree_id=tree)
        state = st._load(tree)
        del state["sessions"]["no-ct"]["completed_at"]
        st._save(tree, state)  # triggers TTL; epoch default means always prunable
        state_after = st._load(tree)
        self.assertNotIn("no-ct", state_after["sessions"],
            "Completed session with missing completed_at must be pruned")


class TestCLISubcommands(unittest.TestCase):
    """Verify that the CLI paths called by the recipe actually work."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _run_cli(self, args, extra_env=None):
        import subprocess
        script = str(Path(__file__).parent.parent / "amplifier-bundle" / "tools" / "session_tree.py")
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, script] + args,
            capture_output=True, text=True, env=env,
            cwd=str(Path(__file__).parent.parent)
        )

    def test_register_outputs_tree_id_and_depth(self):
        """The recipe's setup-session step calls: session_tree.py register <session_id>"""
        import re as _re
        r = self._run_cli(["register", "test-sess-cli"])
        self.assertEqual(r.returncode, 0, f"register should exit 0: {r.stderr}")
        self.assertRegex(r.stdout.strip(), r'^TREE_ID=[A-Za-z0-9_-]+ DEPTH=\d+$',
            f"Output must be 'TREE_ID=... DEPTH=...' format, got: {r.stdout!r}")
        # Record tree for cleanup
        m = _re.search(r'TREE_ID=([A-Za-z0-9_-]+)', r.stdout)
        if m:
            self._trees_created.append(m.group(1))

    def test_check_outputs_allowed_for_new_tree(self):
        """The recipe's derive-recursion-guard step calls: session_tree.py check"""
        r = self._run_cli(
            ["check"],
            extra_env={
                "AMPLIHACK_TREE_ID": "",
                "AMPLIHACK_SESSION_DEPTH": "0",
                "AMPLIHACK_MAX_DEPTH": "3",
                "AMPLIHACK_MAX_SESSIONS": "10",
            }
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "ALLOWED")

    def test_complete_exits_zero(self):
        """The recipe's complete-session step calls: session_tree.py complete <id>"""
        import re as _re
        # Register first
        reg = self._run_cli(["register", "sess-for-complete"])
        m = _re.search(r'TREE_ID=([A-Za-z0-9_-]+)', reg.stdout)
        self.assertIsNotNone(m, f"register output malformed: {reg.stdout!r}")
        tree_id = m.group(1)
        self._trees_created.append(tree_id)
        # Complete
        r = self._run_cli(["complete", "sess-for-complete"],
                         extra_env={"AMPLIHACK_TREE_ID": tree_id})
        self.assertEqual(r.returncode, 0, f"complete should exit 0: {r.stderr}")

    def test_check_blocked_at_max_depth(self):
        """Session at max depth must return BLOCKED."""
        r = self._run_cli(
            ["check"],
            extra_env={"AMPLIHACK_TREE_ID": "", "AMPLIHACK_SESSION_DEPTH": "3", "AMPLIHACK_MAX_DEPTH": "3"}
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("BLOCKED", r.stdout.strip())

    def test_register_exits_rc1_on_capacity_overflow(self):
        """CLI register exits rc=1 when capacity is exceeded (recipe depends on this)."""
        import re as _re
        import uuid
        tree = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(tree)
        saved = os.environ.get("AMPLIHACK_MAX_SESSIONS")
        os.environ["AMPLIHACK_MAX_SESSIONS"] = "1"
        try:
            # Fill the single slot
            r1 = self._run_cli(
                ["register", "first-session"],
                extra_env={"AMPLIHACK_TREE_ID": tree, "AMPLIHACK_MAX_SESSIONS": "1"}
            )
            self.assertEqual(r1.returncode, 0, f"first register should succeed: {r1.stderr}")

            # Second register must fail with rc=1
            r2 = self._run_cli(
                ["register", "second-session"],
                extra_env={"AMPLIHACK_TREE_ID": tree, "AMPLIHACK_MAX_SESSIONS": "1"}
            )
            self.assertEqual(r2.returncode, 1,
                f"register should exit 1 on capacity overflow, got rc={r2.returncode}, stderr={r2.stderr}")
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_SESSIONS", None)
            else:
                os.environ["AMPLIHACK_MAX_SESSIONS"] = saved


class TestDuplicateSessionRegistration(unittest.TestCase):
    """Verify behavior when registering the same session_id twice."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self):
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_register_same_session_id_twice_overwrites(self):
        """Documenting current behavior: duplicate registration silently overwrites."""
        tree = self._unique_tree()
        st.register_session("dup", tree_id=tree, depth=0)
        st.complete_session("dup", tree_id=tree)
        # Re-register same id — overwrites the completed record
        st.register_session("dup", tree_id=tree, depth=1)
        state = st._load(tree)
        # Documents behavior: status reset to active, depth updated
        self.assertEqual(state["sessions"]["dup"]["status"], "active")
        self.assertEqual(state["sessions"]["dup"]["depth"], 1)


class TestTreeIdBoundary(unittest.TestCase):
    """Verify tree_id length boundary validation (MISS-7)."""

    def test_tree_id_exactly_64_chars_is_valid(self):
        """64-character tree_id is within the limit."""
        valid_id = "a" * 64
        result = st._validate_tree_id(valid_id)
        self.assertEqual(result, valid_id)

    def test_tree_id_65_chars_is_invalid(self):
        """65-character tree_id exceeds the limit."""
        with self.assertRaises(ValueError):
            st._validate_tree_id("a" * 65)


class TestCorruptedJsonRecovery(unittest.TestCase):
    """_load must return clean state on corrupted JSON, not raise."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self):
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_corrupted_json_returns_empty_state(self):
        """Write a corrupt JSON file; _load must recover gracefully."""
        tree = self._unique_tree()
        st._ensure_state_dir()
        state_file = st.STATE_DIR / f"{tree}.json"
        state_file.write_text("this is not valid json {{{{")
        result = st._load(tree)
        self.assertIn("sessions", result)
        self.assertEqual(result["sessions"], {})

    def test_truncated_json_returns_empty_state(self):
        """Truncated JSON should be treated as corrupt."""
        tree = self._unique_tree()
        st._ensure_state_dir()
        state_file = st.STATE_DIR / f"{tree}.json"
        state_file.write_text('{"sessions": {"abc": {"status": "active"')
        result = st._load(tree)
        self.assertIn("sessions", result)
        self.assertEqual(result["sessions"], {})

    def test_load_with_sessions_as_string_returns_empty_state(self):
        """When sessions is a string (wrong type), _load must return empty state."""
        tree = self._unique_tree()
        st._ensure_state_dir()
        (st.STATE_DIR / f"{tree}.json").write_text('{"sessions": "not_a_dict"}')
        result = st._load(tree)
        self.assertEqual(result, {"sessions": {}},
            "Schema-invalid state file must be treated as empty state")

    def test_load_with_sessions_as_list_returns_empty_state(self):
        """When sessions is a list (wrong type), _load must return empty state."""
        tree = self._unique_tree()
        st._ensure_state_dir()
        (st.STATE_DIR / f"{tree}.json").write_text('{"sessions": []}')
        result = st._load(tree)
        self.assertEqual(result, {"sessions": {}})


class TestGetStatusEdgeCases(unittest.TestCase):
    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                (st.STATE_DIR / f'{tree}{suffix}').unlink(missing_ok=True)

    def _unique_tree(self):
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_status_for_never_registered_tree_returns_empty(self):
        """get_status for a tree with no state file must return empty lists."""
        import uuid
        tree = "test-never-" + uuid.uuid4().hex[:8]
        result = st.get_status(tree)
        self.assertEqual(result["tree_id"], tree)
        self.assertEqual(result["active"], [])
        self.assertEqual(result["completed"], [])
        self.assertEqual(result["depths"], {})


class TestStaleLockCleanup(unittest.TestCase):
    """Stale lock file from a dead PID must be cleaned up by _locked()."""

    def setUp(self):
        self._trees_created = []

    def tearDown(self):
        for tree in self._trees_created:
            for suffix in ('.json', '.lock'):
                p = st.STATE_DIR / f'{tree}{suffix}'
                p.unlink(missing_ok=True)

    def _unique_tree(self):
        import uuid
        t = "test-" + uuid.uuid4().hex[:8]
        self._trees_created.append(t)
        return t

    def test_stale_lock_from_dead_pid_is_cleaned_up(self):
        """Write a lock file with a dead PID; _locked() must acquire successfully."""
        tree = self._unique_tree()
        st._ensure_state_dir()
        lock_file = st.STATE_DIR / f"{tree}.lock"
        # PID 1 is always init/systemd and will never be a session_tree process.
        # We need a truly dead PID. Use a high PID unlikely to exist, or find one.
        # The safest approach: use a PID we just know is dead.
        # We can fork a process, get its PID, wait for it to exit, then use that PID.
        import subprocess
        proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(0)"])
        dead_pid = proc.pid
        proc.wait()  # Ensure it's dead

        lock_file.write_text(str(dead_pid))

        # _locked() must clean up the stale lock and proceed
        acquired = False
        try:
            with st._locked(tree, timeout=5.0):
                acquired = True
        except TimeoutError:
            pass

        self.assertTrue(acquired, "Should have acquired lock after stale lock cleanup")
        self.assertFalse(lock_file.exists(), "Lock file should be removed after release")


if __name__ == "__main__":
    unittest.main()
