"""Tests for CRDT implementations (GSet, ORSet, LWWRegister).

Testing pyramid:
- 60% Unit tests (add, remove, contains, get/set, serialization)
- 30% Integration tests (merge properties, concurrent add/remove)
- 10% Thread-safety stress tests

Merge properties verified for every type:
- Commutative:  a.merge(b) == b.merge(a)
- Associative:  (a.merge(b)).merge(c) == a.merge(b.merge(c))
- Idempotent:   a.merge(a) == a
"""

from __future__ import annotations

import threading

from amplihack.agents.goal_seeking.hive_mind.crdt import (
    GSet,
    LWWRegister,
    ORSet,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clone_gset(gs: GSet) -> GSet:
    return GSet.from_dict(gs.to_dict())


def _clone_orset(orset: ORSet) -> ORSet:
    return ORSet.from_dict(orset.to_dict())


def _clone_lww(reg: LWWRegister) -> LWWRegister:
    return LWWRegister.from_dict(reg.to_dict())


# ===========================================================================
# GSet tests
# ===========================================================================


class TestGSetUnit:
    """Unit tests for GSet basics."""

    def test_add_and_contains(self) -> None:
        gs = GSet()
        assert not gs.contains("a")
        gs.add("a")
        assert gs.contains("a")

    def test_add_duplicate(self) -> None:
        gs = GSet()
        gs.add("a")
        gs.add("a")
        assert gs.items == frozenset({"a"})

    def test_items_returns_frozenset(self) -> None:
        gs = GSet()
        gs.add("x")
        gs.add("y")
        assert gs.items == frozenset({"x", "y"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        gs = GSet()
        gs.add("a")
        gs.add("b")
        restored = GSet.from_dict(gs.to_dict())
        assert restored.items == gs.items

    def test_to_dict_format(self) -> None:
        gs = GSet()
        gs.add("b")
        gs.add("a")
        d = gs.to_dict()
        assert d["type"] == "GSet"
        assert d["items"] == ["a", "b"]  # sorted


class TestGSetMerge:
    """Merge semantics and CRDT properties for GSet."""

    def test_merge_union(self) -> None:
        a = GSet()
        a.add("x")
        b = GSet()
        b.add("y")
        a.merge(b)
        assert a.items == frozenset({"x", "y"})

    def test_merge_commutative(self) -> None:
        a = GSet()
        a.add("1")
        a.add("2")
        b = GSet()
        b.add("2")
        b.add("3")

        a1 = _clone_gset(a)
        b1 = _clone_gset(b)
        a1.merge(b1)

        a2 = _clone_gset(a)
        b2 = _clone_gset(b)
        b2.merge(a2)

        assert a1.items == b2.items

    def test_merge_associative(self) -> None:
        a = GSet()
        a.add("a")
        b = GSet()
        b.add("b")
        c = GSet()
        c.add("c")

        # (a merge b) merge c
        ab = _clone_gset(a)
        ab.merge(_clone_gset(b))
        ab.merge(_clone_gset(c))

        # a merge (b merge c)
        bc = _clone_gset(b)
        bc.merge(_clone_gset(c))
        a2 = _clone_gset(a)
        a2.merge(bc)

        assert ab.items == a2.items

    def test_merge_idempotent(self) -> None:
        gs = GSet()
        gs.add("x")
        gs.add("y")
        before = gs.items
        gs.merge(_clone_gset(gs))
        assert gs.items == before


class TestGSetThreadSafety:
    def test_concurrent_adds(self) -> None:
        gs = GSet()
        errors: list[Exception] = []

        def add_items(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    gs.add(str(i))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add_items, args=(i * 100,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(gs.items) == 400


# ===========================================================================
# ORSet tests
# ===========================================================================


class TestORSetUnit:
    """Unit tests for ORSet basics."""

    def test_add_and_contains(self) -> None:
        s = ORSet()
        assert not s.contains("a")
        s.add("a")
        assert s.contains("a")

    def test_remove_makes_absent(self) -> None:
        s = ORSet()
        s.add("a")
        s.remove("a")
        assert not s.contains("a")

    def test_add_after_remove_restores(self) -> None:
        s = ORSet()
        s.add("a")
        s.remove("a")
        s.add("a")
        assert s.contains("a")

    def test_remove_nonexistent_is_noop(self) -> None:
        s = ORSet()
        s.remove("ghost")
        assert not s.contains("ghost")

    def test_items(self) -> None:
        s = ORSet()
        s.add("x")
        s.add("y")
        s.remove("x")
        assert s.items == frozenset({"y"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        s = ORSet()
        s.add("a")
        s.add("b")
        s.remove("a")
        restored = ORSet.from_dict(s.to_dict())
        assert restored.items == s.items

    def test_add_returns_unique_tag(self) -> None:
        s = ORSet()
        t1 = s.add("a")
        t2 = s.add("a")
        assert t1 != t2


class TestORSetConcurrentAddRemove:
    """ORSet resolves concurrent add/remove correctly."""

    def test_concurrent_add_wins_over_remove(self) -> None:
        """If A adds and B removes concurrently, the add wins (add-wins semantics)."""
        a = ORSet()
        a.add("x")

        # B observes x, then removes it
        b = _clone_orset(a)
        b.remove("x")

        # A concurrently adds x again (new tag)
        a.add("x")

        # Merge: A's new tag is NOT in B's tombstones, so x is present
        a.merge(b)
        assert a.contains("x")


class TestORSetMerge:
    """Merge properties for ORSet."""

    def test_merge_commutative(self) -> None:
        a = ORSet()
        a.add("1")
        a.add("2")
        b = ORSet()
        b.add("2")
        b.add("3")

        a1 = _clone_orset(a)
        b1 = _clone_orset(b)
        a1.merge(b1)

        a2 = _clone_orset(a)
        b2 = _clone_orset(b)
        b2.merge(a2)

        assert a1.items == b2.items

    def test_merge_associative(self) -> None:
        a = ORSet()
        a.add("a")
        b = ORSet()
        b.add("b")
        c = ORSet()
        c.add("c")

        ab = _clone_orset(a)
        ab.merge(_clone_orset(b))
        ab.merge(_clone_orset(c))

        bc = _clone_orset(b)
        bc.merge(_clone_orset(c))
        a2 = _clone_orset(a)
        a2.merge(bc)

        assert ab.items == a2.items

    def test_merge_idempotent(self) -> None:
        s = ORSet()
        s.add("x")
        s.add("y")
        s.remove("x")
        before = s.items
        s.merge(_clone_orset(s))
        assert s.items == before

    def test_merge_with_removes(self) -> None:
        a = ORSet()
        a.add("x")
        a.add("y")

        b = _clone_orset(a)
        b.remove("x")

        a.merge(b)
        assert not a.contains("x")
        assert a.contains("y")


class TestORSetThreadSafety:
    def test_concurrent_add_remove(self) -> None:
        s = ORSet()
        errors: list[Exception] = []

        def adder() -> None:
            try:
                for i in range(50):
                    s.add(f"item-{i}")
            except Exception as exc:
                errors.append(exc)

        def remover() -> None:
            try:
                for i in range(50):
                    s.remove(f"item-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=adder) for _ in range(2)]
        threads += [threading.Thread(target=remover) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ===========================================================================
# LWWRegister tests
# ===========================================================================


class TestLWWRegisterUnit:
    """Unit tests for LWWRegister basics."""

    def test_set_and_get(self) -> None:
        r = LWWRegister()
        assert r.get() is None
        r.set("hello", 1.0)
        assert r.get() == "hello"

    def test_later_timestamp_wins(self) -> None:
        r = LWWRegister()
        r.set("old", 1.0)
        r.set("new", 2.0)
        assert r.get() == "new"

    def test_earlier_timestamp_ignored(self) -> None:
        r = LWWRegister()
        r.set("new", 2.0)
        r.set("old", 1.0)
        assert r.get() == "new"

    def test_tie_broken_by_value(self) -> None:
        r = LWWRegister()
        r.set("aaa", 1.0)
        r.set("zzz", 1.0)
        assert r.get() == "zzz"

    def test_to_dict_from_dict_roundtrip(self) -> None:
        r = LWWRegister()
        r.set("val", 42.0)
        restored = LWWRegister.from_dict(r.to_dict())
        assert restored.get() == "val"

    def test_to_dict_empty(self) -> None:
        r = LWWRegister()
        d = r.to_dict()
        assert d["type"] == "LWWRegister"
        assert d["value"] is None
        assert d["timestamp"] is None

    def test_from_dict_empty(self) -> None:
        r = LWWRegister.from_dict({"type": "LWWRegister", "value": None, "timestamp": None})
        assert r.get() is None


class TestLWWRegisterMerge:
    """Merge properties for LWWRegister."""

    def test_merge_keeps_latest(self) -> None:
        a = LWWRegister()
        a.set("a-val", 1.0)
        b = LWWRegister()
        b.set("b-val", 2.0)
        a.merge(b)
        assert a.get() == "b-val"

    def test_merge_commutative(self) -> None:
        a = LWWRegister()
        a.set("a", 1.0)
        b = LWWRegister()
        b.set("b", 2.0)

        a1 = _clone_lww(a)
        b1 = _clone_lww(b)
        a1.merge(b1)

        a2 = _clone_lww(a)
        b2 = _clone_lww(b)
        b2.merge(a2)

        assert a1.get() == b2.get()

    def test_merge_associative(self) -> None:
        a = LWWRegister()
        a.set("a", 1.0)
        b = LWWRegister()
        b.set("b", 2.0)
        c = LWWRegister()
        c.set("c", 3.0)

        ab = _clone_lww(a)
        ab.merge(_clone_lww(b))
        ab.merge(_clone_lww(c))

        bc = _clone_lww(b)
        bc.merge(_clone_lww(c))
        a2 = _clone_lww(a)
        a2.merge(bc)

        assert ab.get() == a2.get()

    def test_merge_idempotent(self) -> None:
        r = LWWRegister()
        r.set("val", 5.0)
        before = r.get()
        r.merge(_clone_lww(r))
        assert r.get() == before

    def test_merge_with_empty(self) -> None:
        a = LWWRegister()
        a.set("val", 1.0)
        b = LWWRegister()
        a.merge(b)
        assert a.get() == "val"

    def test_merge_empty_with_value(self) -> None:
        a = LWWRegister()
        b = LWWRegister()
        b.set("val", 1.0)
        a.merge(b)
        assert a.get() == "val"

    def test_merge_tie_deterministic(self) -> None:
        a = LWWRegister()
        a.set("aaa", 1.0)
        b = LWWRegister()
        b.set("zzz", 1.0)

        a1 = _clone_lww(a)
        a1.merge(_clone_lww(b))
        b1 = _clone_lww(b)
        b1.merge(_clone_lww(a))

        assert a1.get() == b1.get() == "zzz"


class TestLWWRegisterThreadSafety:
    def test_concurrent_sets(self) -> None:
        r = LWWRegister()
        errors: list[Exception] = []

        def setter(offset: float) -> None:
            try:
                for i in range(100):
                    r.set(f"v-{offset}-{i}", offset + i)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=setter, args=(i * 1000.0,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert r.get() is not None
