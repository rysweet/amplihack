"""Keep the packaged smart-orchestrator bundle in lockstep with repo source."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_RECIPE = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
PACKAGED_RECIPE = (
    REPO_ROOT / "src" / "amplihack" / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
)


def test_packaged_smart_orchestrator_matches_repo_source():
    assert PACKAGED_RECIPE.read_text(encoding="utf-8") == SOURCE_RECIPE.read_text(
        encoding="utf-8"
    ), "Packaged smart-orchestrator.yaml drifted from amplifier-bundle source"


def test_complete_session_step_is_nonfatal():
    content = SOURCE_RECIPE.read_text(encoding="utf-8")
    assert re.search(
        r'- id: "complete-session"\n\s+fatal: false\n\s+type: "bash"',
        content,
    ), "complete-session must stay non-fatal so wrapper teardown owns finalization"
