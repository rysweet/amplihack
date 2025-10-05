# Root conftest.py to set up Python path for imports
import sys
from pathlib import Path

# Add src directory to Python path for imports
root_dir = Path(__file__).parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))