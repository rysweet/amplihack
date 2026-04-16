"""Tests for step-03b issue/PR reference extraction logic.

Validates the regex patterns and priority chain used by step-03b-extract-issue-number
in default-workflow.yaml to handle: issue URLs, PR URLs, #NNN references, ADO work
item URLs, and bare numeric IDs.

Covers fixes for: #4344, #4326, #4308, #4307, #4316, #4303
"""

from __future__ import annotations

import re
import subprocess
import textwrap

# ---------------------------------------------------------------------------
# Helpers — mirror the extraction patterns from step-03b
# ---------------------------------------------------------------------------

ISSUE_URL_RE = re.compile(r"(issues|_workitems/edit)/([0-9]+)")
PR_URL_RE = re.compile(r"pull/([0-9]+)")
HASH_REF_RE = re.compile(r"(?<![A-Za-z0-9_/-])#([0-9]+)\b")
BARE_NUMBER_RE = re.compile(r"^([0-9]+)$", re.MULTILINE)


def extract_issue_urls(text: str) -> list[str]:
    """Priority 1: Direct issue/ADO URLs."""
    return [m.group(2) for m in ISSUE_URL_RE.finditer(text)]


def extract_pr_urls(text: str) -> list[str]:
    """Priority 3: PR URLs."""
    return [m.group(1) for m in PR_URL_RE.finditer(text)]


def extract_hash_refs(text: str) -> list[str]:
    """Priority 2: #NNN hash references (deduplicated, order-preserved)."""
    seen: set[str] = set()
    result: list[str] = []
    for m in HASH_REF_RE.finditer(text):
        candidate = m.group(1)
        if candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def extract_bare_numbers(text: str) -> list[str]:
    """Priority 5: Bare numbers on their own line."""
    return [m.group(1) for m in BARE_NUMBER_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Priority 1: Issue URL extraction
# ---------------------------------------------------------------------------


class TestIssueURLExtraction:
    def test_github_issue_url(self):
        text = "https://github.com/owner/repo/issues/4567"
        assert extract_issue_urls(text) == ["4567"]

    def test_ado_work_item_url(self):
        text = "_workitems/edit/9876"
        assert extract_issue_urls(text) == ["9876"]

    def test_multiple_issue_urls(self):
        text = "issues/111 and issues/222"
        assert extract_issue_urls(text) == ["111", "222"]

    def test_no_match_for_pr_url(self):
        text = "https://github.com/owner/repo/pull/999"
        assert extract_issue_urls(text) == []

    def test_issue_url_in_noisy_output(self):
        text = textwrap.dedent("""\
            Creating issue...
            https://github.com/owner/repo/issues/4344
            Done.
        """)
        assert extract_issue_urls(text) == ["4344"]


# ---------------------------------------------------------------------------
# Priority 2: #NNN hash reference extraction
# ---------------------------------------------------------------------------


class TestHashRefExtraction:
    def test_single_hash_ref(self):
        assert extract_hash_refs("Fix #123") == ["123"]

    def test_multiple_hash_refs_deduplicated(self):
        assert extract_hash_refs("Closes #100, fixes #200, refs #100") == ["100", "200"]

    def test_hash_ref_not_in_url_path(self):
        # The negative lookbehind should prevent matching /123 inside URLs
        assert extract_hash_refs("issues/456") == []

    def test_hash_ref_at_start_of_line(self):
        assert extract_hash_refs("#789 is the target") == ["789"]

    def test_no_hash_refs(self):
        assert extract_hash_refs("No references here") == []

    def test_hash_ref_in_task_description(self):
        text = "Implement feature described in #4344, also see #4326"
        assert extract_hash_refs(text) == ["4344", "4326"]


# ---------------------------------------------------------------------------
# Priority 3: PR URL extraction
# ---------------------------------------------------------------------------


class TestPRURLExtraction:
    def test_github_pr_url(self):
        text = "https://github.com/owner/repo/pull/555"
        assert extract_pr_urls(text) == ["555"]

    def test_pr_url_not_confused_with_issue(self):
        text = "https://github.com/owner/repo/issues/111"
        assert extract_pr_urls(text) == []

    def test_mixed_issue_and_pr_urls(self):
        text = "issues/111 and pull/222"
        assert extract_issue_urls(text) == ["111"]
        assert extract_pr_urls(text) == ["222"]


# ---------------------------------------------------------------------------
# Priority 5: Bare numeric ID
# ---------------------------------------------------------------------------


class TestBareNumberExtraction:
    def test_bare_number_on_own_line(self):
        text = "4567\n"
        assert extract_bare_numbers(text) == ["4567"]

    def test_bare_number_among_text(self):
        text = "Created:\n4567\nDone"
        assert extract_bare_numbers(text) == ["4567"]

    def test_no_bare_number_inline(self):
        text = "Issue 4567 created"
        assert extract_bare_numbers(text) == []


# ---------------------------------------------------------------------------
# Integration: full priority chain (shell-level)
# ---------------------------------------------------------------------------

# These tests run the actual grep/python pipeline from a shell snippet to
# verify the extraction works end-to-end for each priority level.

SHELL_EXTRACT_SNIPPET = textwrap.dedent(r"""
    set -euo pipefail
    COMBINED_TEXT="$1"

    # Priority 1: issue/ADO URL
    EXTRACTED=$(printf '%s' "$COMBINED_TEXT" | grep -oE '(issues|_workitems/edit)/[0-9]+' | grep -oE '[0-9]+' | head -1 || true)

    # Priority 2: #NNN hash refs (just extract, no gh verification in test)
    if [ -z "$EXTRACTED" ]; then
      EXTRACTED=$(COMBINED_TEXT="$COMBINED_TEXT" python3 - <<'PY'
import os, re
text = os.environ.get("COMBINED_TEXT", "")
seen = set()
for m in re.finditer(r'(?<![A-Za-z0-9_/-])#([0-9]+)\b', text):
    c = m.group(1)
    if c not in seen:
        print(c)
        seen.add(c)
PY
    )
      EXTRACTED=$(printf '%s' "$EXTRACTED" | head -1)
    fi

    # Priority 3: PR URL
    if [ -z "$EXTRACTED" ]; then
      EXTRACTED=$(printf '%s' "$COMBINED_TEXT" | grep -oE 'pull/[0-9]+' | grep -oE '[0-9]+' | head -1 || true)
    fi

    # Priority 5: bare number
    if [ -z "$EXTRACTED" ]; then
      EXTRACTED=$(printf '%s' "$COMBINED_TEXT" | grep -oE '^[0-9]+$' | head -1 || true)
    fi

    printf '%s' "$EXTRACTED"
""")


def _run_shell_extract(text: str) -> str:
    """Run the shell extraction snippet and return the result."""
    result = subprocess.run(
        ["bash", "-c", SHELL_EXTRACT_SNIPPET, "--", text],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


class TestShellExtractionIntegration:
    def test_issue_url_priority(self):
        assert _run_shell_extract("https://github.com/o/r/issues/100") == "100"

    def test_ado_url_priority(self):
        assert _run_shell_extract("_workitems/edit/200") == "200"

    def test_hash_ref_fallback(self):
        assert _run_shell_extract("Fix for #300") == "300"

    def test_pr_url_fallback(self):
        assert _run_shell_extract("https://github.com/o/r/pull/400") == "400"

    def test_bare_number_fallback(self):
        assert _run_shell_extract("500") == "500"

    def test_issue_url_beats_hash_ref(self):
        text = "issues/100 and also #200"
        assert _run_shell_extract(text) == "100"

    def test_hash_ref_beats_pr_url(self):
        text = "#300 from pull/400"
        assert _run_shell_extract(text) == "300"

    def test_merged_pr_url_extracted(self):
        text = "Merged https://github.com/o/r/pull/600"
        assert _run_shell_extract(text) == "600"

    def test_complex_mixed_input(self):
        text = textwrap.dedent("""\
            Task: fix bug
            See https://github.com/owner/repo/pull/999
            Related to #777
        """)
        # #777 should win over pull/999 (Priority 2 > Priority 3)
        assert _run_shell_extract(text) == "777"

    def test_empty_input_returns_empty(self):
        assert _run_shell_extract("no numbers here") == ""
