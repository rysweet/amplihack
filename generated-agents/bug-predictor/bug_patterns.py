"""
Bug Pattern Database

Defines common bug patterns and their characteristics for detection.
This module serves as a knowledge base for the bug predictor agent.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PatternDefinition:
    """Definition of a bug pattern."""

    name: str
    severity: str  # "critical", "high", "medium", "low"
    description: str
    keywords: list[str]
    ast_patterns: list[str]
    common_contexts: list[str]
    fix_template: str


# Common bug patterns in Python code
PATTERN_DATABASE = {
    "none_reference": PatternDefinition(
        name="none_reference",
        severity="high",
        description="Accessing attributes or methods on potentially None objects",
        keywords=["None", "is None", "== None", ".get(", "or None"],
        ast_patterns=["Compare", "Attribute", "Call"],
        common_contexts=[
            "result = function_that_returns_none()",
            "obj.method() without null check",
            "dict.get() without default value",
        ],
        fix_template="if obj is not None: obj.method()",
    ),
    "resource_leak": PatternDefinition(
        name="resource_leak",
        severity="high",
        description="Resources (files, connections) not properly closed",
        keywords=["open(", "connect(", "cursor(", "socket(", "close()"],
        ast_patterns=["Call", "With", "Assign"],
        common_contexts=[
            "f = open('file.txt') without close()",
            "conn = connect() without context manager",
            "Missing finally block for cleanup",
        ],
        fix_template="with open(...) as f: # use context manager",
    ),
    "sql_injection": PatternDefinition(
        name="sql_injection",
        severity="critical",
        description="SQL queries vulnerable to injection attacks",
        keywords=["execute(", "cursor.execute", "query", "+", 'f"', ".format("],
        ast_patterns=["Call", "BinOp", "JoinedStr"],
        common_contexts=[
            "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
            "query = f'DELETE FROM {table} WHERE {condition}'",
            "Using string concatenation in SQL",
        ],
        fix_template="cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))",
    ),
    "race_condition": PatternDefinition(
        name="race_condition",
        severity="high",
        description="Concurrent access to shared state without synchronization",
        keywords=["threading", "Thread", "Lock", "global", "shared_state"],
        ast_patterns=["Global", "Call", "Assign"],
        common_contexts=[
            "Multiple threads modifying global variable",
            "Shared dictionary without lock",
            "Check-then-act race condition",
        ],
        fix_template="with lock: # synchronized access",
    ),
    "memory_leak": PatternDefinition(
        name="memory_leak",
        severity="medium",
        description="Unbounded memory growth from unchecked accumulation",
        keywords=["append", "global", "cache", "[]", "{}"],
        ast_patterns=["Global", "List", "Dict", "Call"],
        common_contexts=[
            "Global cache that never clears",
            "Appending to list in loop without limit",
            "Circular references without cleanup",
        ],
        fix_template="Use weak references or bounded cache (LRU)",
    ),
    "off_by_one": PatternDefinition(
        name="off_by_one",
        severity="medium",
        description="Array/list indexing errors at boundaries",
        keywords=["range(", "len(", "[-1]", "[0]", "[i+1]", "[i-1]"],
        ast_patterns=["Subscript", "Call", "BinOp"],
        common_contexts=[
            "range(len(arr)) with arr[i+1]",
            "Loop from 1 to len(arr)",
            "Missing boundary check",
        ],
        fix_template="Check bounds: if i < len(arr) - 1: arr[i+1]",
    ),
    "type_mismatch": PatternDefinition(
        name="type_mismatch",
        severity="medium",
        description="Operations on incompatible types",
        keywords=["int(", "str(", "float(", "+", "*", "/"],
        ast_patterns=["Call", "BinOp", "Compare"],
        common_contexts=[
            "Adding string and int without conversion",
            "Comparing different types",
            "Missing type validation",
        ],
        fix_template="Explicit type check: isinstance(obj, expected_type)",
    ),
    "uncaught_exception": PatternDefinition(
        name="uncaught_exception",
        severity="high",
        description="Exceptions raised but not handled",
        keywords=["raise", "Exception", "Error", "try:", "except"],
        ast_patterns=["Raise", "Try", "ExceptHandler"],
        common_contexts=[
            "Raise exception in function without try/except",
            "Broad except clause (except:)",
            "Re-raising without context",
        ],
        fix_template="try: risky_op() except SpecificError as e: handle(e)",
    ),
    "infinite_loop": PatternDefinition(
        name="infinite_loop",
        severity="high",
        description="Loop with no exit condition or modification",
        keywords=["while True:", "while 1:", "for", "break"],
        ast_patterns=["While", "For", "Break"],
        common_contexts=[
            "while True without break",
            "Loop variable not modified",
            "Missing termination condition",
        ],
        fix_template="Add break condition or modify loop variable",
    ),
    "hardcoded_credentials": PatternDefinition(
        name="hardcoded_credentials",
        severity="critical",
        description="Credentials or secrets hardcoded in source",
        keywords=["password", "api_key", "secret", "token", "="],
        ast_patterns=["Assign", "Str", "Constant"],
        common_contexts=[
            "password = 'admin123'",
            "API_KEY = 'sk-...'",
            "Hardcoded connection strings",
        ],
        fix_template="Use environment variables: os.getenv('PASSWORD')",
    ),
}


def get_pattern(pattern_name: str) -> PatternDefinition:
    """Get pattern definition by name."""
    return PATTERN_DATABASE.get(pattern_name)


def get_all_patterns() -> dict[str, PatternDefinition]:
    """Get all pattern definitions."""
    return PATTERN_DATABASE.copy()


def get_patterns_by_severity(severity: str) -> dict[str, PatternDefinition]:
    """Get patterns filtered by severity."""
    return {
        name: pattern for name, pattern in PATTERN_DATABASE.items() if pattern.severity == severity
    }


def get_critical_patterns() -> dict[str, PatternDefinition]:
    """Get only critical severity patterns."""
    return get_patterns_by_severity("critical")


def pattern_to_dict(pattern: PatternDefinition) -> dict[str, Any]:
    """Convert pattern definition to dictionary."""
    return {
        "name": pattern.name,
        "severity": pattern.severity,
        "description": pattern.description,
        "keywords": pattern.keywords,
        "ast_patterns": pattern.ast_patterns,
        "common_contexts": pattern.common_contexts,
        "fix_template": pattern.fix_template,
    }
