"""Bloom filter for compact shard content summaries.

Used by the gossip protocol to efficiently compare shard contents
between agents. Each agent maintains a bloom filter of its fact IDs.
During gossip, agents exchange bloom filters and pull missing facts.

Philosophy:
- Compact representation (1KB for 1000 facts at 1% FPR)
- No false negatives — if bloom says "not present", it's truly absent
- Trade small false positive rate for massive space savings
- Simple bit-array implementation, no external dependencies

Public API:
    BloomFilter: Probabilistic set membership data structure
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence


class BloomFilter:
    """Space-efficient probabilistic set membership test.

    Supports add() and might_contain(). False positives possible,
    false negatives impossible.

    Args:
        expected_items: Expected number of items to store
        false_positive_rate: Target FPR (default 0.01 = 1%)
    """

    def __init__(
        self,
        expected_items: int = 1000,
        false_positive_rate: float = 0.01,
    ):
        self._expected = expected_items
        self._fpr = false_positive_rate

        # Optimal bit array size: m = -n*ln(p) / (ln2)^2
        if expected_items <= 0:
            expected_items = 1
        self._size = max(
            64,
            int(-expected_items * math.log(false_positive_rate) / (math.log(2) ** 2)),
        )
        # Optimal number of hash functions: k = (m/n) * ln2
        self._num_hashes = max(1, int((self._size / expected_items) * math.log(2)))
        # Bit array as bytearray
        self._bits = bytearray((self._size + 7) // 8)
        self._count = 0

    def _get_hashes(self, item: str) -> list[int]:
        """Generate k hash positions for an item using double hashing."""
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)
        return [(h1 + i * h2) % self._size for i in range(self._num_hashes)]

    def add(self, item: str) -> None:
        """Add an item to the bloom filter."""
        for pos in self._get_hashes(item):
            byte_idx = pos >> 3
            bit_idx = pos & 7
            self._bits[byte_idx] |= 1 << bit_idx
        self._count += 1

    def might_contain(self, item: str) -> bool:
        """Test if an item might be in the set.

        Returns True if possibly present, False if definitely absent.
        """
        for pos in self._get_hashes(item):
            byte_idx = pos >> 3
            bit_idx = pos & 7
            if not (self._bits[byte_idx] & (1 << bit_idx)):
                return False
        return True

    def add_all(self, items: Sequence[str]) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)

    def missing_from(self, items: Sequence[str]) -> list[str]:
        """Return items from the sequence that are NOT in this filter.

        These are items the peer has that we definitely don't.
        """
        return [item for item in items if not self.might_contain(item)]

    @property
    def count(self) -> int:
        """Approximate number of items added."""
        return self._count

    @property
    def size_bytes(self) -> int:
        """Size of the underlying bit array in bytes."""
        return len(self._bits)

    def to_bytes(self) -> bytes:
        """Serialize the bloom filter for network transmission."""
        return bytes(self._bits)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        expected_items: int = 1000,
        false_positive_rate: float = 0.01,
    ) -> BloomFilter:
        """Deserialize a bloom filter from bytes."""
        bf = cls(expected_items=expected_items, false_positive_rate=false_positive_rate)
        bf._bits = bytearray(data[: len(bf._bits)])
        return bf


__all__ = ["BloomFilter"]
