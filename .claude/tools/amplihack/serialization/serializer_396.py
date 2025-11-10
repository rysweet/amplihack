"""Serialization utilities - Batch 396"""

import pickle
import json
from typing import Any
from pathlib import Path

class Serializer:
    """Serialize and deserialize objects."""

    @staticmethod
    def to_pickle(obj: Any, filepath: Path) -> None:
        """Serialize object to pickle file."""
        with open(filepath, 'wb') as f:
            pickle.dump(obj, f)

    @staticmethod
    def from_pickle(filepath: Path) -> Any:
        """Deserialize object from pickle file."""
        with open(filepath, 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def to_json_file(obj: Any, filepath: Path, indent: int = 2) -> None:
        """Serialize object to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(obj, f, indent=indent, default=str)

    @staticmethod
    def from_json_file(filepath: Path) -> Any:
        """Deserialize object from JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)
