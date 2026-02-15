"""
Library of optimization patterns and techniques.

This module contains reusable optimization patterns that the agent
learns to apply effectively over time.
"""

from dataclasses import dataclass


@dataclass
class OptimizationPattern:
    """Represents a reusable optimization pattern."""

    pattern_id: str
    name: str
    category: str
    description: str
    before_code: str
    after_code: str
    estimated_speedup_min: float
    estimated_speedup_max: float
    when_to_apply: str
    caveats: list[str]


# Library of optimization patterns
OPTIMIZATION_PATTERNS: dict[str, OptimizationPattern] = {
    "list_comprehension": OptimizationPattern(
        pattern_id="list_comprehension",
        name="List Comprehension",
        category="comprehension",
        description="Replace explicit for-loop with list comprehension",
        before_code="""
result = []
for x in items:
    result.append(f(x))
""",
        after_code="""
result = [f(x) for x in items]
""",
        estimated_speedup_min=1.5,
        estimated_speedup_max=2.0,
        when_to_apply="When building a list by iterating and appending",
        caveats=[
            "Don't use for side effects",
            "Keep comprehensions simple and readable",
        ],
    ),
    "generator_expression": OptimizationPattern(
        pattern_id="generator_expression",
        name="Generator Expression",
        category="comprehension",
        description="Use generator expression for memory efficiency",
        before_code="""
result = [f(x) for x in large_iterable]
for item in result:
    process(item)
""",
        after_code="""
result = (f(x) for x in large_iterable)
for item in result:
    process(item)
""",
        estimated_speedup_min=1.0,
        estimated_speedup_max=1.2,
        when_to_apply="When processing large iterables once",
        caveats=[
            "Can't iterate twice",
            "No indexing support",
        ],
    ),
    "set_membership": OptimizationPattern(
        pattern_id="set_membership",
        name="Set Membership Test",
        category="algorithm",
        description="Use set instead of list for membership tests",
        before_code="""
if x in [1, 2, 3, 4, 5]:
    do_something()
""",
        after_code="""
if x in {1, 2, 3, 4, 5}:
    do_something()
""",
        estimated_speedup_min=5.0,
        estimated_speedup_max=100.0,
        when_to_apply="When checking membership in collections (3+ items)",
        caveats=[
            "Sets use more memory",
            "Items must be hashable",
            "Order is not preserved",
        ],
    ),
    "dict_get": OptimizationPattern(
        pattern_id="dict_get",
        name="Dictionary .get() Method",
        category="algorithm",
        description="Use dict.get() instead of key check + access",
        before_code="""
if key in my_dict:
    value = my_dict[key]
else:
    value = default
""",
        after_code="""
value = my_dict.get(key, default)
""",
        estimated_speedup_min=1.2,
        estimated_speedup_max=1.5,
        when_to_apply="When accessing dict with default fallback",
        caveats=[
            "Only for simple default values",
            "Use setdefault() if modifying dict",
        ],
    ),
    "join_strings": OptimizationPattern(
        pattern_id="join_strings",
        name="String Join",
        category="string",
        description="Use str.join() instead of concatenation in loops",
        before_code="""
result = ""
for s in strings:
    result += s
""",
        after_code="""
result = "".join(strings)
""",
        estimated_speedup_min=10.0,
        estimated_speedup_max=100.0,
        when_to_apply="When concatenating multiple strings in a loop",
        caveats=[
            "All items must be strings",
            "Consider f-strings for templates",
        ],
    ),
    "enumerate_instead_of_range_len": OptimizationPattern(
        pattern_id="enumerate_instead_of_range_len",
        name="Enumerate Instead of range(len())",
        category="loop",
        description="Use enumerate() for cleaner and faster iteration",
        before_code="""
for i in range(len(items)):
    print(i, items[i])
""",
        after_code="""
for i, item in enumerate(items):
    print(i, item)
""",
        estimated_speedup_min=1.3,
        estimated_speedup_max=1.5,
        when_to_apply="When needing both index and value in loops",
        caveats=[
            "Use start parameter if not starting at 0",
        ],
    ),
    "any_instead_of_loop": OptimizationPattern(
        pattern_id="any_instead_of_loop",
        name="any() Instead of Loop",
        category="loop",
        description="Use any() for existence checks",
        before_code="""
found = False
for x in items:
    if condition(x):
        found = True
        break
""",
        after_code="""
found = any(condition(x) for x in items)
""",
        estimated_speedup_min=2.0,
        estimated_speedup_max=3.0,
        when_to_apply="When checking if any item meets a condition",
        caveats=[
            "Use all() for universal checks",
            "Short-circuits on first True",
        ],
    ),
    "all_instead_of_loop": OptimizationPattern(
        pattern_id="all_instead_of_loop",
        name="all() Instead of Loop",
        category="loop",
        description="Use all() for universal checks",
        before_code="""
valid = True
for x in items:
    if not condition(x):
        valid = False
        break
""",
        after_code="""
valid = all(condition(x) for x in items)
""",
        estimated_speedup_min=2.0,
        estimated_speedup_max=3.0,
        when_to_apply="When checking if all items meet a condition",
        caveats=[
            "Short-circuits on first False",
            "Returns True for empty iterables",
        ],
    ),
    "lru_cache": OptimizationPattern(
        pattern_id="lru_cache",
        name="LRU Cache Decorator",
        category="caching",
        description="Cache function results with @lru_cache",
        before_code="""
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
        after_code="""
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
        estimated_speedup_min=100.0,
        estimated_speedup_max=10000.0,
        when_to_apply="When function is called repeatedly with same arguments",
        caveats=[
            "Arguments must be hashable",
            "Memory usage increases",
            "Not suitable for functions with side effects",
        ],
    ),
    "defaultdict": OptimizationPattern(
        pattern_id="defaultdict",
        name="defaultdict",
        category="algorithm",
        description="Use defaultdict to avoid key checks",
        before_code="""
counts = {}
for item in items:
    if item not in counts:
        counts[item] = 0
    counts[item] += 1
""",
        after_code="""
from collections import defaultdict

counts = defaultdict(int)
for item in items:
    counts[item] += 1
""",
        estimated_speedup_min=1.5,
        estimated_speedup_max=2.0,
        when_to_apply="When accumulating values in dict",
        caveats=[
            "Consider Counter for counting",
            "Creates entries on access",
        ],
    ),
    "counter": OptimizationPattern(
        pattern_id="counter",
        name="collections.Counter",
        category="algorithm",
        description="Use Counter for counting operations",
        before_code="""
counts = {}
for item in items:
    counts[item] = counts.get(item, 0) + 1
""",
        after_code="""
from collections import Counter

counts = Counter(items)
""",
        estimated_speedup_min=2.0,
        estimated_speedup_max=5.0,
        when_to_apply="When counting occurrences",
        caveats=[
            "Counter is a dict subclass",
            "Has useful methods like most_common()",
        ],
    ),
    "operator_itemgetter": OptimizationPattern(
        pattern_id="operator_itemgetter",
        name="operator.itemgetter",
        category="algorithm",
        description="Use itemgetter for faster sorting/grouping",
        before_code="""
sorted_items = sorted(items, key=lambda x: x[1])
""",
        after_code="""
from operator import itemgetter

sorted_items = sorted(items, key=itemgetter(1))
""",
        estimated_speedup_min=1.5,
        estimated_speedup_max=2.0,
        when_to_apply="When sorting/grouping by item/attribute access",
        caveats=[
            "Use attrgetter for attributes",
            "Slightly faster than lambda",
        ],
    ),
    "local_variable": OptimizationPattern(
        pattern_id="local_variable",
        name="Local Variable Caching",
        category="loop",
        description="Cache frequently accessed attributes in local variables",
        before_code="""
for item in items:
    process(self.config.value, item)
""",
        after_code="""
config_value = self.config.value
for item in items:
    process(config_value, item)
""",
        estimated_speedup_min=1.1,
        estimated_speedup_max=1.3,
        when_to_apply="When accessing same attribute repeatedly in loop",
        caveats=[
            "Local lookups are faster than attribute lookups",
            "Only worth it for tight loops",
        ],
    ),
    "slots": OptimizationPattern(
        pattern_id="slots",
        name="__slots__",
        category="memory",
        description="Use __slots__ to reduce memory in classes",
        before_code="""
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
""",
        after_code="""
class Point:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y
""",
        estimated_speedup_min=1.0,
        estimated_speedup_max=1.2,
        when_to_apply="When creating many instances of simple classes",
        caveats=[
            "Reduces memory by ~40%",
            "No __dict__ attribute",
            "Can't add new attributes dynamically",
        ],
    ),
}


def get_pattern(pattern_id: str) -> OptimizationPattern:
    """Get optimization pattern by ID."""
    return OPTIMIZATION_PATTERNS.get(pattern_id)


def get_patterns_by_category(category: str) -> list[OptimizationPattern]:
    """Get all patterns in a category."""
    return [pattern for pattern in OPTIMIZATION_PATTERNS.values() if pattern.category == category]


def get_all_categories() -> list[str]:
    """Get all optimization categories."""
    return sorted(set(p.category for p in OPTIMIZATION_PATTERNS.values()))


def format_pattern_info(pattern: OptimizationPattern) -> str:
    """Format pattern information for display."""
    lines = [
        f"=== {pattern.name} ===",
        f"Category: {pattern.category}",
        f"Description: {pattern.description}",
        "",
        f"Speedup Range: {pattern.estimated_speedup_min:.1f}x - {pattern.estimated_speedup_max:.1f}x",
        "",
        "When to Apply:",
        f"  {pattern.when_to_apply}",
        "",
        "Before:",
        pattern.before_code.strip(),
        "",
        "After:",
        pattern.after_code.strip(),
        "",
        "Caveats:",
    ]

    for caveat in pattern.caveats:
        lines.append(f"  - {caveat}")

    return "\n".join(lines)
