"""Encoding utilities - Batch 462"""

import base64
from typing import Union

class Encoder:
    """Encode and decode data in various formats."""

    @staticmethod
    def to_base64(data: Union[str, bytes]) -> str:
        """Encode data to base64 string."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b64encode(data).decode('utf-8')

    @staticmethod
    def from_base64(encoded: str) -> bytes:
        """Decode base64 string to bytes."""
        return base64.b64decode(encoded)

    @staticmethod
    def to_hex(data: Union[str, bytes]) -> str:
        """Encode data to hex string."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data.hex()

    @staticmethod
    def from_hex(hex_string: str) -> bytes:
        """Decode hex string to bytes."""
        return bytes.fromhex(hex_string)
