"""Pytest configuration for mcp-manager tests."""

import sys
from pathlib import Path

# Add parent directory to path so we can import mcp_manager modules
test_dir = Path(__file__).parent
package_dir = test_dir.parent
sys.path.insert(0, str(package_dir))
