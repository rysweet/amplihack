"""Shared utilities for hive_mind package."""

import hashlib


def content_hash(text: str) -> str:
    """SHA-256 hash of normalized text for deduplication.

    Normalizes by stripping whitespace and lowercasing before hashing.
    Used by all hive_mind modules for consistent deduplication.
    """
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
