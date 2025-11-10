"""Hashing utilities - Batch 471"""

import hashlib
from typing import Union

class Hasher:
    """Generate hashes for data."""

    @staticmethod
    def md5(data: Union[str, bytes]) -> str:
        """Generate MD5 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def sha256(data: Union[str, bytes]) -> str:
        """Generate SHA256 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha512(data: Union[str, bytes]) -> str:
        """Generate SHA512 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha512(data).hexdigest()

    @staticmethod
    def file_hash(filepath: str, algorithm: str = "sha256") -> str:
        """Generate hash of file contents."""
        hasher = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
