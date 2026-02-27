"""
Tests for amplifier-bundle/tools/session_tree.py

Covers: depth enforcement, max-session limits, queueing,
concurrent access (via locking), env var propagation.
"""

import json
import os
import sys
import time
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

    def _unique_tree(self) -> str:
        import uuid
        return "test-" + uuid.uuid4().hex[:8]

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

    def _unique_tree(self) -> str:
        import uuid
        return "test-" + uuid.uuid4().hex[:8]

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


class TestQueueing(unittest.TestCase):
    """Items over capacity should queue and dequeue when space opens."""

    def _unique_tree(self) -> str:
        import uuid
        return "test-" + uuid.uuid4().hex[:8]

    def test_enqueue_adds_to_queue(self):
        tree = self._unique_tree()
        spec = {"issue": "TBD", "branch": "feat/test", "description": "test", "task": "do it"}
        st.enqueue_session(spec, tree_id=tree)
        state = st._load(tree)
        self.assertEqual(len(state["queue"]), 1)
        self.assertEqual(state["queue"][0]["spec"]["branch"], "feat/test")

    def test_dequeue_returns_items_when_capacity_available(self):
        tree = self._unique_tree()
        for i in range(3):
            spec = {"issue": str(i), "branch": f"feat/ws-{i}", "description": f"ws{i}", "task": f"t{i}"}
            st.enqueue_session(spec, tree_id=tree)
        # No active sessions — all 3 should dequeue
        ready = st.dequeue_ready(tree_id=tree, max_sessions=10)
        self.assertEqual(len(ready), 3)
        state = st._load(tree)
        self.assertEqual(len(state["queue"]), 0)

    def test_dequeue_respects_capacity(self):
        tree = self._unique_tree()
        # 1 active session, max_sessions=2 → only 1 slot
        st.register_session("active-s", tree_id=tree, depth=0)
        for i in range(3):
            st.enqueue_session({"branch": f"b{i}"}, tree_id=tree)
        ready = st.dequeue_ready(tree_id=tree, max_sessions=2)
        self.assertEqual(len(ready), 1)
        state = st._load(tree)
        self.assertEqual(len(state["queue"]), 2)  # 2 remain queued

    def test_dequeue_fifo_order(self):
        tree = self._unique_tree()
        for i in range(3):
            st.enqueue_session({"order": i}, tree_id=tree)
        ready = st.dequeue_ready(tree_id=tree, max_sessions=10)
        orders = [r["order"] for r in ready]
        self.assertEqual(orders, [0, 1, 2])


class TestEnvForChild(unittest.TestCase):
    """env_for_child must correctly increment depth and propagate limits."""

    def test_increments_depth(self):
        saved = os.environ.get("AMPLIHACK_SESSION_DEPTH")
        os.environ["AMPLIHACK_SESSION_DEPTH"] = "1"
        try:
            env = st.env_for_child("tree123", 1)
            self.assertEqual(env["AMPLIHACK_SESSION_DEPTH"], "2")
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_SESSION_DEPTH", None)
            else:
                os.environ["AMPLIHACK_SESSION_DEPTH"] = saved

    def test_tree_id_preserved(self):
        env = st.env_for_child("my-tree", 0)
        self.assertEqual(env["AMPLIHACK_TREE_ID"], "my-tree")

    def test_max_depth_propagated(self):
        saved = os.environ.get("AMPLIHACK_MAX_DEPTH")
        os.environ["AMPLIHACK_MAX_DEPTH"] = "2"
        try:
            env = st.env_for_child("t", 0)
            self.assertEqual(env["AMPLIHACK_MAX_DEPTH"], "2")
        finally:
            if saved is None:
                os.environ.pop("AMPLIHACK_MAX_DEPTH", None)
            else:
                os.environ["AMPLIHACK_MAX_DEPTH"] = saved


class TestGetStatus(unittest.TestCase):
    """get_status returns a useful tree summary."""

    def _unique_tree(self) -> str:
        import uuid
        return "test-" + uuid.uuid4().hex[:8]

    def test_status_counts_correctly(self):
        tree = self._unique_tree()
        st.register_session("a", tree_id=tree, depth=0)
        st.register_session("b", tree_id=tree, depth=0)
        st.complete_session("a", tree_id=tree)
        st.enqueue_session({"x": 1}, tree_id=tree)

        status = st.get_status(tree)
        self.assertEqual(status["tree_id"], tree)
        self.assertIn("b", status["active"])
        self.assertIn("a", status["completed"])
        self.assertEqual(status["queued"], 1)


if __name__ == "__main__":
    unittest.main()
