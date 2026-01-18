"""Pytest configuration and shared fixtures for az-devops-tools tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_config():
    """Mock configuration dictionary."""
    return {
        "org": "https://dev.azure.com/test-org",
        "project": "TestProject",
    }


@pytest.fixture
def mock_az_cli_success():
    """Mock successful az CLI command result."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.success = True
    mock_result.stdout = '{"value": []}'
    mock_result.stderr = ""
    mock_result.json_output = {"value": []}
    return mock_result


@pytest.fixture
def mock_az_cli_failure():
    """Mock failed az CLI command result."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.success = False
    mock_result.stdout = ""
    mock_result.stderr = "Error: Authentication failed"
    mock_result.json_output = None
    return mock_result


@pytest.fixture
def mock_work_item():
    """Mock work item data."""
    return {
        "id": 1234,
        "fields": {
            "System.Title": "Test Work Item",
            "System.WorkItemType": "User Story",
            "System.State": "New",
            "System.AssignedTo": "test@example.com",
            "System.Description": "<p>Test description</p>",
        },
        "url": "https://dev.azure.com/test-org/TestProject/_workitems/edit/1234",
    }


@pytest.fixture
def sample_markdown():
    """Sample markdown text for testing."""
    return """# Heading 1

## Heading 2

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2
- List item 3

1. Numbered item 1
2. Numbered item 2

```python
def hello():
    print("Hello, world!")
```

[Link text](https://example.com)
"""


@pytest.fixture
def sample_html():
    """Expected HTML output for sample_markdown."""
    return """<h1>Heading 1</h1>
<h2>Heading 2</h2>
<p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
<ul>
<li>List item 1</li>
<li>List item 2</li>
<li>List item 3</li>
</ul>
<ol>
<li>Numbered item 1</li>
<li>Numbered item 2</li>
</ol>
<pre><code class="language-python">def hello():
    print("Hello, world!")
</code></pre>
<p><a href="https://example.com">Link text</a></p>"""
