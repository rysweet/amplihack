"""Pytest configuration for API Client tests.

This conftest adds the parent directory to sys.path so that
the api_client module can be imported during testing.
"""

import sys
from pathlib import Path

# Add parent directory (api-client/) to path for imports
api_client_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_client_dir))
