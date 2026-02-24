"""Conftest for domain agent tests.

Ensures domain_agents package is importable by making the local
src/ directory take priority over the installed amplihack package.
"""

import sys
from pathlib import Path

# Calculate paths
_project_root = Path(__file__).resolve().parents[3]
_src = str(_project_root / "src")

# Insert src at the front of sys.path so local code takes priority
if _src not in sys.path:
    sys.path.insert(0, _src)

# Remove all cached amplihack modules so they reload from local src
_to_remove = [k for k in list(sys.modules.keys()) if k.startswith("amplihack")]
for k in _to_remove:
    del sys.modules[k]

# Force reimport of amplihack from local src
