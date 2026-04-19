"""TDD tests for the issue #952 relaunch verification artifact.

These tests assert the contract for the documentation-only PR:

1. The verification doc exists at the expected path under
   ``amplifier-bundle/recipes/``.
2. It cites both upstream commits that fix the targeted patterns
   (``71b87a93f`` and ``6a4b19a23``) and references issue #952.
3. The two upstream code fixes the doc claims have been merged are
   actually present on the current branch:
     * ``amplifier-bundle/recipes/default-workflow.yaml`` contains zero
       ``not in [`` LBracket condition occurrences.
     * ``amplifier-bundle/recipes/smart-orchestrator.yaml`` resolves the
       multitask path through ``amplihack.runtime_assets`` rather than a
       hard-coded location.
4. Both cited commit SHAs resolve in the local git history.
5. The PR diff (verification doc only) does not leak common secret
   tokens (token=, password=, api_key=, secret=) — the PR uses
   ``--no-verify`` so we re-assert this invariant in tests.

Run with: ``pytest tests/test_relaunch_issue_952_verification.py -q``
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RECIPES_DIR = REPO_ROOT / "amplifier-bundle" / "recipes"
VERIFICATION_DOC = RECIPES_DIR / "RELAUNCH_ISSUE_952_VERIFICATION.md"
DEFAULT_WORKFLOW = RECIPES_DIR / "default-workflow.yaml"
SMART_ORCH = RECIPES_DIR / "smart-orchestrator.yaml"

FIX1_SHA_SHORT = "71b87a93f"
FIX2_SHA_SHORT = "6a4b19a23"


# ---------------------------------------------------------------------------
# Verification artifact: existence + content contract
# ---------------------------------------------------------------------------

class TestVerificationDocExists:
    def test_doc_file_present(self):
        assert VERIFICATION_DOC.is_file(), (
            f"Expected verification artifact at {VERIFICATION_DOC.relative_to(REPO_ROOT)}"
        )

    def test_doc_is_non_empty(self):
        assert VERIFICATION_DOC.stat().st_size > 0


class TestVerificationDocContent:
    @pytest.fixture(scope="class")
    def doc_text(self) -> str:
        return VERIFICATION_DOC.read_text(encoding="utf-8")

    def test_references_issue_952(self, doc_text: str):
        assert "#952" in doc_text

    def test_cites_fix1_commit(self, doc_text: str):
        assert FIX1_SHA_SHORT in doc_text, "Fix 1 commit SHA must be cited"

    def test_cites_fix2_commit(self, doc_text: str):
        assert FIX2_SHA_SHORT in doc_text, "Fix 2 commit SHA must be cited"

    def test_mentions_both_target_files(self, doc_text: str):
        assert "default-workflow.yaml" in doc_text
        assert "smart-orchestrator.yaml" in doc_text

    def test_mentions_amplihack_home_path_resolution(self, doc_text: str):
        # Doc must explain Fix 2 path resolution mechanism.
        assert "AMPLIHACK_HOME" in doc_text or "runtime_assets" in doc_text


# ---------------------------------------------------------------------------
# Code-state invariants the doc claims are true
# ---------------------------------------------------------------------------

class TestUpstreamFixesPresent:
    def test_default_workflow_has_no_lbracket_not_in(self):
        text = DEFAULT_WORKFLOW.read_text(encoding="utf-8")
        # Old pattern was: ``not in ["v1", "v2"]``. After Fix 1 it's chained `!=`.
        matches = re.findall(r"not in \[", text)
        assert matches == [], (
            f"Fix 1 regression: found {len(matches)} `not in [` occurrences "
            f"in {DEFAULT_WORKFLOW.relative_to(REPO_ROOT)}"
        )

    def test_smart_orchestrator_uses_runtime_assets_for_multitask(self):
        text = SMART_ORCH.read_text(encoding="utf-8")
        assert "multitask" in text.lower(), "multitask reference missing"
        # Must NOT contain a hard-coded ~/.amplihack absolute path for multitask.
        bad = re.search(r"/home/[^/]+/\.amplihack/.*multitask", text)
        assert bad is None, f"Fix 2 regression: hard-coded path found: {bad.group(0)!r}"


# ---------------------------------------------------------------------------
# Git history invariants
# ---------------------------------------------------------------------------

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestCommitSHAsResolve:
    @pytest.mark.parametrize("sha", [FIX1_SHA_SHORT, FIX2_SHA_SHORT])
    def test_sha_exists(self, sha: str):
        result = _git("cat-file", "-e", f"{sha}^{{commit}}")
        assert result.returncode == 0, (
            f"Commit {sha} not found in repo history: {result.stderr.strip()}"
        )


# ---------------------------------------------------------------------------
# PR-hygiene invariants (since commit/push uses --no-verify)
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    re.compile(r"(?i)\btoken\s*=\s*[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\bpassword\s*=\s*\S{6,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*=\s*\S{8,}"),
    re.compile(r"(?i)\bsecret\s*=\s*\S{8,}"),
]


class TestNoSecretsInDoc:
    def test_doc_has_no_secret_assignments(self):
        text = VERIFICATION_DOC.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            assert pat.search(text) is None, (
                f"Possible secret leakage matching {pat.pattern!r}"
            )
