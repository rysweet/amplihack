# How to Create Your Own {TOOL_TYPE}

This guide helps you create a tool similar to **{TOOL_NAME}** by following the proven patterns and architecture.

## Understanding the Pattern

### Core Concept

{TOOL_NAME} is a **{TOOL_CATEGORY}** that follows the **{CORE_PATTERN}** pattern. The key insight is:

> {KEY_INSIGHT_QUOTE}

### Architecture Overview

```
{ARCHITECTURE_DIAGRAM}
```

## Step-by-Step Creation Guide

### Step 1: Define Your Tool's Purpose

Answer these questions:

- **What problem does your tool solve?**
  {EXAMPLE_ANSWER}

- **Who is your target user?**
  {EXAMPLE_ANSWER}

- **What is the minimal viable solution?**
  {EXAMPLE_ANSWER}

### Step 2: Choose Your Tool Name

Follow amplihack naming conventions:

- **Format**: `{naming-pattern}`
- **Examples**: `{example-1}`, `{example-2}`, `{example-3}`
- **Your tool**: `{your-tool-name}`

### Step 3: Set Up Directory Structure

```bash
# Start in ai_working/ for experimentation
mkdir .claude/ai_working/{your-tool-name}
cd .claude/ai_working/{your-tool-name}

# Create basic files
touch README.md
touch prototype.py
touch notes.md
mkdir examples
```

### Step 4: Implement Core Functionality

#### Template Code Structure

```python
#!/usr/bin/env python3
"""
{Your Tool Name}

{One line description}
"""

import argparse
import sys
from pathlib import Path
from typing import {TYPE_ANNOTATIONS}

# Add project root to path for amplihack imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.amplihack.core import {CORE_IMPORTS}
from src.amplihack.agents import {AGENT_IMPORTS}

class {YourToolClass}:
    """Main tool implementation following {PATTERN_NAME} pattern."""

    def __init__(self, config: dict = None):
        """Initialize tool with configuration."""
        self.config = config or {}
        {INITIALIZATION_CODE}

    def {main_method}(self, {PARAMETERS}) -> {RETURN_TYPE}:
        """
        {METHOD_DESCRIPTION}

        Args:
            {PARAMETER_DOCS}

        Returns:
            {RETURN_DOCS}

        Example:
            >>> tool = {YourToolClass}()
            >>> result = tool.{main_method}({EXAMPLE_ARGS})
            >>> print(result)
        """
        {IMPLEMENTATION_TEMPLATE}

    def _validate_input(self, {INPUT_PARAMS}) -> bool:
        """Validate input parameters and security constraints."""
        {VALIDATION_LOGIC}

    def _format_output(self, {DATA_PARAMS}) -> {OUTPUT_TYPE}:
        """Format output according to user preferences."""
        {FORMATTING_LOGIC}

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='{TOOL_DESCRIPTION}')

    # Add arguments based on your tool's needs
    parser.add_argument('{ARG_NAME}', help='{ARG_HELP}')
    parser.add_argument('--{OPTION_NAME}', help='{OPTION_HELP}', default='{DEFAULT_VALUE}')

    args = parser.parse_args()

    # Create and run tool
    tool = {YourToolClass}()
    result = tool.{main_method}({MAPPED_ARGS})

    # Output results
    print(result)

if __name__ == '__main__':
    main()
```

### Step 5: Add Security Validation

Implement these security measures:

```python
import re
from pathlib import Path

def validate_tool_name(name: str) -> bool:
    """Validate tool name to prevent injection attacks."""
    if not re.match(r'^[a-z0-9-]+$', name):
        raise ValueError(f"Invalid tool name: {name}")
    return True

def validate_file_path(path: str, allowed_dirs: list = None) -> Path:
    """Validate file paths to prevent directory traversal."""
    clean_path = Path(path).resolve()

    # Prevent directory traversal
    if '..' in str(clean_path):
        raise ValueError(f"Directory traversal not allowed: {path}")

    # Restrict to allowed directories
    if allowed_dirs:
        if not any(str(clean_path).startswith(str(Path(d).resolve()))
                  for d in allowed_dirs):
            raise ValueError(f"Path not in allowed directories: {path}")

    return clean_path

def sanitize_user_input(content: str) -> str:
    """Sanitize user-generated content."""
    {SANITIZATION_LOGIC}
```

### Step 6: Write Tests

Create comprehensive test coverage:

```python
# tests/test_{your_tool}.py
import pytest
from pathlib import Path
import tempfile
import shutil

from ..{your_tool} import {YourToolClass}

class Test{YourToolClass}:
    """Test suite for {YourToolClass}."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tool = {YourToolClass}()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Unit Tests (60% of coverage)
    def test_{core_functionality}(self):
        """Test core functionality works correctly."""
        {TEST_IMPLEMENTATION}

    def test_input_validation(self):
        """Test input validation catches invalid inputs."""
        with pytest.raises(ValueError):
            self.tool.{main_method}({INVALID_INPUT})

    def test_security_validation(self):
        """Test security constraints are enforced."""
        {SECURITY_TESTS}

    # Integration Tests (30% of coverage)
    def test_agent_integration(self):
        """Test integration with amplihack agents."""
        {AGENT_INTEGRATION_TESTS}

    def test_workflow_integration(self):
        """Test integration with amplihack workflow."""
        {WORKFLOW_INTEGRATION_TESTS}

    # End-to-End Tests (10% of coverage)
    def test_full_workflow(self):
        """Test complete user workflow."""
        {E2E_TEST_IMPLEMENTATION}
```

### Step 7: Add Makefile Integration

```makefile
# Add to project Makefile
{your-tool-name}:
	@echo "Running {Your Tool Name}..."
	@python .claude/scenarios/{your-tool-name}/tool.py $(TARGET) $(OPTIONS)

.PHONY: {your-tool-name}
```

### Step 8: Graduate to Scenarios

When your tool meets graduation criteria:

```bash
# Move from ai_working to scenarios
mkdir .claude/scenarios/{your-tool-name}
cp -r .claude/ai_working/{your-tool-name}/* .claude/scenarios/{your-tool-name}/

# Rename and enhance files
mv prototype.py tool.py
# Complete documentation
# Add full test suite
# Update Makefile
```

## Customization Points

### Common Variations

**{VARIATION_1}**: {DESCRIPTION}

- Modify: {MODIFICATION_POINTS}
- Examples: {EXAMPLES}

**{VARIATION_2}**: {DESCRIPTION}

- Modify: {MODIFICATION_POINTS}
- Examples: {EXAMPLES}

### Configuration Options

```python
# Typical configuration structure
DEFAULT_CONFIG = {
    '{config_key}': '{default_value}',
    '{config_key}': {default_value},
    '{config_key}': ['{default_list}'],
}
```

### Extension Points

The tool can be extended by:

1. **{EXTENSION_POINT_1}**: {DESCRIPTION}
2. **{EXTENSION_POINT_2}**: {DESCRIPTION}
3. **{EXTENSION_POINT_3}**: {DESCRIPTION}

## Common Patterns

### Pattern 1: {PATTERN_NAME}

**When to use**: {USE_CASE}
**Implementation**: {IMPLEMENTATION_GUIDE}

### Pattern 2: {PATTERN_NAME}

**When to use**: {USE_CASE}
**Implementation**: {IMPLEMENTATION_GUIDE}

## Best Practices

### Code Quality

- Follow amplihack's ruthless simplicity philosophy
- No stubs or placeholder implementations
- Comprehensive error handling
- Clear, descriptive naming

### User Experience

- Immediate value on first use
- Sensible defaults
- Clear error messages
- Helpful examples

### Integration

- Respect user preferences
- Work with existing agents
- Follow workflow patterns
- Maintain security standards

## Troubleshooting Creation Process

### Common Issues

**Issue**: Tool doesn't integrate with agents
**Solution**: {SOLUTION_STEPS}

**Issue**: Makefile target not working
**Solution**: {SOLUTION_STEPS}

**Issue**: Tests not running correctly
**Solution**: {SOLUTION_STEPS}

## Next Steps

After creating your tool:

1. **Test Extensively**: Use with real scenarios
2. **Gather Feedback**: Get input from other users
3. **Iterate Rapidly**: Improve based on learning
4. **Document Learnings**: Update this template with insights
5. **Share Knowledge**: Help others create similar tools

## Resources

- **Original Tool**: `.claude/scenarios/{tool-name}/`
- **Template Files**: `.claude/scenarios/templates/`
- **Agent Documentation**: `.claude/agents/`
- **Philosophy Guide**: `.claude/context/PHILOSOPHY.md`

---

_Remember: Start simple, test early, iterate based on real usage. The best tools solve actual problems with minimal complexity._
