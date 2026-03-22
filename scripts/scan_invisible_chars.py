#!/usr/bin/env python3
"""Scan git diff for invisible/malicious Unicode characters.

Supply-chain defense: detects zero-width chars, bidi overrides, tag characters,
and other invisible Unicode that can be used to hide malicious code in PRs.

Usage:
    # Scan a PR diff from stdin
    gh pr diff 123 | python3 scripts/scan_invisible_chars.py

    # Scan staged changes
    git diff --cached | python3 scripts/scan_invisible_chars.py

Exit codes:
    0 = clean
    1 = suspicious characters found
    2 = scan error
"""

from __future__ import annotations

import sys

DANGEROUS_CHARS: dict[int, str] = {
    # Zero-width characters
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    # Bidirectional overrides/embeddings
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    # Bidirectional isolates
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
    # Invisible operators
    0x2060: "WORD JOINER",
    0x2061: "FUNCTION APPLICATION",
    0x2062: "INVISIBLE TIMES",
    0x2063: "INVISIBLE SEPARATOR",
    0x2064: "INVISIBLE PLUS",
    # Other dangerous invisibles
    0xFEFF: "BYTE ORDER MARK",
    0x00AD: "SOFT HYPHEN",
    0x034F: "COMBINING GRAPHEME JOINER",
    0x061C: "ARABIC LETTER MARK",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0xFFF9: "INTERLINEAR ANNOTATION ANCHOR",
    0xFFFA: "INTERLINEAR ANNOTATION SEPARATOR",
    0xFFFB: "INTERLINEAR ANNOTATION TERMINATOR",
    # Language tag
    0xE0001: "LANGUAGE TAG",
}

# Ranges checked dynamically (too many individual entries)
DANGEROUS_RANGES: list[tuple[int, int, str]] = [
    (0xE0020, 0xE007F, "TAG CHARACTER"),
    (0xFE00, 0xFE0F, "VARIATION SELECTOR"),
    (0xE0100, 0xE01EF, "VARIATION SELECTOR SUPPLEMENT"),
]


def classify_char(cp: int) -> str | None:
    """Return a description if the codepoint is dangerous, else None."""
    name = DANGEROUS_CHARS.get(cp)
    if name:
        return name
    for lo, hi, category in DANGEROUS_RANGES:
        if lo <= cp <= hi:
            return f"{category} U+{cp:04X}"
    return None


def scan_diff(diff_text: str) -> list[dict]:
    """Parse a unified diff and scan added lines for invisible characters.

    Returns a list of findings, each with file, line, col, char, and name.
    """
    findings = []
    current_file = None
    line_in_new = 0

    for raw_line in diff_text.splitlines():
        # Track current file from diff headers
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue
        if raw_line.startswith("--- "):
            continue

        # Track line numbers from hunk headers
        if raw_line.startswith("@@"):
            # Parse @@ -old,count +new,count @@
            try:
                plus_part = raw_line.split("+")[1].split("@@")[0].strip()
                line_in_new = int(plus_part.split(",")[0]) - 1
            except (IndexError, ValueError):
                line_in_new = 0
            continue

        # Only scan added lines (not removed or context)
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_in_new += 1
            content = raw_line[1:]  # strip the leading '+'
            for col, ch in enumerate(content, 1):
                name = classify_char(ord(ch))
                if name:
                    findings.append(
                        {
                            "file": current_file or "<unknown>",
                            "line": line_in_new,
                            "col": col,
                            "char": f"U+{ord(ch):04X}",
                            "name": name,
                        }
                    )
        elif not raw_line.startswith("-"):
            line_in_new += 1

    return findings


def main() -> int:
    try:
        diff_text = sys.stdin.read()
    except Exception as e:
        print(f"ERROR: Failed to read input: {e}", file=sys.stderr)
        return 2

    if not diff_text.strip():
        print("No diff content to scan.")
        return 0

    findings = scan_diff(diff_text)

    if not findings:
        print("✅ No invisible/malicious Unicode characters found.")
        return 0

    print(f"🚨 Found {len(findings)} suspicious invisible character(s):\n")
    for f in findings:
        print(f"  {f['file']}:{f['line']}:{f['col']}  {f['char']} ({f['name']})")
    print(
        "\nThese characters are invisible and can be used to hide malicious code."
        "\nSee: https://trojansource.codes/"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
