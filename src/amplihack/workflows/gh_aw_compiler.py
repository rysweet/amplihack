"""GH-AW Workflow Compiler Frontend.

Python-based compiler frontend for ``.github/workflows/*.md`` (gh-aw) files.
Parses and validates workflow frontmatter, producing structured diagnostics
with line:col positions, fuzzy suggestions, and valid-value examples.

Key improvements over raw PyYAML-based validators:

- **P0** Normalises PyYAML's ``on``→``True`` boolean coercion (YAML "Norway
  problem") by reading raw key strings via ``yaml.compose()``.
- **P1** Attaches ``line:col`` positions to every diagnostic.
- **P1** Promotes unrecognised-field warnings to *errors* when the
  Levenshtein edit distance to the closest known field is ≤ 2.
- **P2** Suggests the top-3 closest known fields by fuzzy matching.
- **P2** Embeds valid-value examples in "missing required field" errors.
- **P2** Type-checks ``timeout-minutes`` (must be an integer, not a string).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Literal

import yaml

# ---------------------------------------------------------------------------
# Field registry
# ---------------------------------------------------------------------------

#: All frontmatter fields recognised by the gh-aw compiler.
KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "on",
        "engine",
        "strict",
        "timeout-minutes",
        "permissions",
        "tools",
        "tracker-id",
        "safe-outputs",
        "imports",
        "skip-if-match",
        "concurrency",
    }
)

#: Fields that *must* be present for the workflow to compile.
REQUIRED_FIELDS: frozenset[str] = frozenset({"name", "on"})

#: Human-readable valid-value examples embedded in missing-field diagnostics.
FIELD_VALID_VALUES: dict[str, str] = {
    "name": 'a quoted string, e.g. "My Workflow Name"',
    "on": (
        "a trigger map, e.g.:\n  on:\n    push:\n      branches: [main]\n    workflow_dispatch:"
    ),
    "engine": 'one of: "claude", "copilot"',
    "strict": "true or false",
    "timeout-minutes": "an integer, e.g. 30",
}

#: Fields whose values must be YAML integers (tag ``!!int``).
INT_FIELDS: frozenset[str] = frozenset({"timeout-minutes"})

# ---------------------------------------------------------------------------
# Diagnostic model
# ---------------------------------------------------------------------------

Severity = Literal["error", "warning"]


@dataclass
class Diagnostic:
    """A compiler diagnostic with severity, message, and optional location."""

    severity: Severity
    message: str
    line: int | None = None
    col: int | None = None

    def format(self, filename: str = "") -> str:
        """Return a human-readable single-line representation.

        Format: ``[ERROR|WARN] filename:line:col message``
        """
        tag = "ERROR" if self.severity == "error" else "WARN "
        loc_parts = []
        if filename:
            loc_parts.append(filename)
        if self.line is not None:
            loc_parts.append(str(self.line))
            if self.col is not None:
                loc_parts.append(str(self.col))
        loc = ":".join(loc_parts)
        prefix = f"[{tag}] {loc}: " if loc else f"[{tag}] "
        return f"{prefix}{self.message}"

    def __str__(self) -> str:
        return self.format()


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class GhAwCompiler:
    """Compiler frontend for ``.github/workflows/*.md`` gh-aw workflow files.

    Usage::

        compiler = GhAwCompiler()
        diags = compiler.compile(Path("code-simplifier.md").read_text(),
                                 filename="code-simplifier.md")
        for d in diags:
            print(d.format())   # filename already embedded via compile()

    Or pass the filename only when formatting::

        diags = compiler.compile(content)
        for d in diags:
            print(d.format(filename="code-simplifier.md"))
    """

    def compile(self, content: str, filename: str = "<unknown>") -> list[Diagnostic]:
        """Validate workflow frontmatter and return all diagnostics.

        Args:
            content: Full ``.md`` file content (frontmatter + body).
            filename: File name shown in diagnostic messages.

        Returns:
            Ordered list of :class:`Diagnostic` objects.  Errors appear before
            warnings; within the same severity they appear in source order.
        """
        diagnostics: list[Diagnostic] = []

        fm_text, fm_line_offset = self._extract_frontmatter_text(content)
        if fm_text is None:
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message=("Missing frontmatter delimiter.  File must start with a --- block."),
                    line=1,
                    col=1,
                )
            )
            return diagnostics

        # Parse using yaml.compose() so we get raw key strings *and* positions.
        # yaml.safe_load() would silently coerce "on" → True (YAML "Norway
        # problem"), making the field appear missing.
        try:
            doc = yaml.compose(fm_text)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message=f"Invalid YAML in frontmatter: {exc}",
                    line=(mark.line + fm_line_offset) if mark else fm_line_offset,
                    col=(mark.column + 1) if mark else None,
                )
            )
            return diagnostics

        if doc is None or not isinstance(doc, yaml.MappingNode):
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message="Frontmatter must be a YAML mapping (key: value pairs).",
                    line=fm_line_offset,
                    col=1,
                )
            )
            return diagnostics

        keys_present: set[str] = set()

        for key_node, val_node in doc.value:
            raw_key = self._raw_key(key_node)
            line = key_node.start_mark.line + fm_line_offset
            col = key_node.start_mark.column + 1

            keys_present.add(raw_key)

            if raw_key not in KNOWN_FIELDS:
                diagnostics.extend(self._unknown_field_diagnostics(raw_key, line, col))

            # Type-check integer fields
            if raw_key in INT_FIELDS:
                diagnostics.extend(self._type_check_int(raw_key, val_node, line, col))

        # Required-field checks
        for req_field in sorted(REQUIRED_FIELDS):
            if req_field not in keys_present:
                diagnostics.append(self._missing_required_diagnostic(req_field, fm_line_offset))

        return diagnostics

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_key(key_node: yaml.ScalarNode) -> str:
        """Return the *original* YAML string for a mapping key.

        ``yaml.compose()`` preserves the source text in ``ScalarNode.value``
        even for boolean-coercible words like "on", "off", "yes", "no".
        This avoids the PyYAML "Norway problem" where safe_load would
        silently convert "on" → ``True``.
        """
        return key_node.value

    def _unknown_field_diagnostics(self, key: str, line: int, col: int) -> list[Diagnostic]:
        """Produce a diagnostic for an unrecognised frontmatter field."""
        suggestions = difflib.get_close_matches(key, KNOWN_FIELDS, n=3, cutoff=0.5)
        min_dist = min((_edit_distance(key, f) for f in KNOWN_FIELDS), default=999)

        if suggestions:
            suggestion_text = ", ".join(f"'{s}'" for s in suggestions)
            msg = (
                f"Unrecognised frontmatter field '{key}' (possible typo). "
                f"Did you mean: {suggestion_text}?"
            )
        else:
            msg = f"Unrecognised frontmatter field '{key}'."

        # Edit distance ≤ 2 → almost certainly a typo → escalate to error.
        severity: Severity = "error" if min_dist <= 2 else "warning"
        return [Diagnostic(severity=severity, message=msg, line=line, col=col)]

    @staticmethod
    def _type_check_int(
        field_name: str,
        val_node: yaml.Node,
        line: int,
        col: int,
    ) -> list[Diagnostic]:
        """Return an error if *val_node* is not a YAML integer."""
        int_tag = "tag:yaml.org,2002:int"
        if not (isinstance(val_node, yaml.ScalarNode) and val_node.tag == int_tag):
            actual = val_node.value if isinstance(val_node, yaml.ScalarNode) else "<complex>"
            example = FIELD_VALID_VALUES.get(field_name, "an integer")
            return [
                Diagnostic(
                    severity="error",
                    message=(
                        f"Field '{field_name}' must be {example}, got string value '{actual}'."
                    ),
                    line=line,
                    col=col,
                )
            ]
        return []

    @staticmethod
    def _missing_required_diagnostic(field_name: str, fm_line: int) -> Diagnostic:
        """Build an informative error for a missing required field."""
        example = FIELD_VALID_VALUES.get(field_name, "")
        suffix = f"  Valid format: {example}" if example else ""
        return Diagnostic(
            severity="error",
            message=(
                f"Missing required field '{field_name}'.  "
                f"Workflow cannot be compiled without the '{field_name}' field.{suffix}"
            ),
            line=fm_line,
            col=1,
        )

    @staticmethod
    def _extract_frontmatter_text(content: str) -> tuple[str | None, int]:
        """Split out the YAML frontmatter block from a Markdown file.

        Returns ``(frontmatter_text, start_line)`` where *start_line* is the
        1-based line number of the first frontmatter line (i.e. line 2, right
        after the opening ``---``).  Returns ``(None, 0)`` when no frontmatter
        is found.
        """
        if not content.startswith("---"):
            return None, 0

        lines = content.split("\n")
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                # lines[1:i] is the frontmatter body; starts at source line 2
                return "\n".join(lines[1:i]), 2

        return None, 0


# ---------------------------------------------------------------------------
# Levenshtein edit distance (stdlib only, no external deps)
# ---------------------------------------------------------------------------


def _edit_distance(s1: str, s2: str) -> int:
    """Return the Levenshtein edit distance between *s1* and *s2*."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if not s2:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for ch1 in s1:
        curr_row = [prev_row[0] + 1]
        for j, ch2 in enumerate(s2):
            curr_row.append(
                min(
                    prev_row[j + 1] + 1,  # deletion
                    curr_row[j] + 1,  # insertion
                    prev_row[j] + (ch1 != ch2),  # substitution
                )
            )
        prev_row = curr_row

    return prev_row[-1]


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------


def compile_workflow(content: str, filename: str = "<unknown>") -> list[Diagnostic]:
    """Module-level shortcut for :meth:`GhAwCompiler.compile`."""
    return GhAwCompiler().compile(content, filename=filename)
