"""Pytest configuration for xpia-defense tests."""

import sys
from pathlib import Path

# Add parent directory to path so we can import xpia_hook directly
sys.path.insert(0, str(Path(__file__).parent.parent))
