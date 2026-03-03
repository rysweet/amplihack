"""Exclude outside-in test scenarios from pytest collection.

These are gadugi-agentic-test YAML scenarios, not pytest tests.
They are executed by the gadugi-agentic-test framework, not by pytest.

Run them with: gadugi-agentic-test run <scenario.yaml>
"""

collect_ignore_glob = ["*.yaml"]
