"""Comparison utilities - Batch 424"""

from typing import Any, List, Dict
from difflib import SequenceMatcher

class Comparator:
    """Compare and diff data structures."""

    @staticmethod
    def similarity(str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, str1, str2).ratio()

    @staticmethod
    def diff_lists(list1: List[Any], list2: List[Any]) -> Dict[str, List[Any]]:
        """Find differences between two lists."""
        set1 = set(list1)
        set2 = set(list2)
        return {{
            "only_in_first": list(set1 - set2),
            "only_in_second": list(set2 - set1),
            "common": list(set1 & set2)
        }}

    @staticmethod
    def diff_dicts(dict1: Dict, dict2: Dict) -> Dict[str, Dict]:
        """Find differences between two dictionaries."""
        all_keys = set(dict1.keys()) | set(dict2.keys())
        result = {{
            "only_in_first": {{}},
            "only_in_second": {{}},
            "different_values": {{}},
            "same": {{}}
        }}

        for key in all_keys:
            if key not in dict2:
                result["only_in_first"][key] = dict1[key]
            elif key not in dict1:
                result["only_in_second"][key] = dict2[key]
            elif dict1[key] != dict2[key]:
                result["different_values"][key] = {{"first": dict1[key], "second": dict2[key]}}
            else:
                result["same"][key] = dict1[key]

        return result
