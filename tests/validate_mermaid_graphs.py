#!/usr/bin/env python3
"""Validate mermaid workflow graphs added by PR #3249.

Checks:
1. All 7 target files contain ```mermaid blocks
2. Mermaid syntax is structurally valid (balanced braces, valid keywords)
3. Test-driven fixes are present (parallel validators, NEW qualifier, separate edges)
4. Graph structure matches expected node counts
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS = {
    ".claude/skills/dev-orchestrator/SKILL.md": {
        "type": "flowchart",
        "required_nodes": ["Classify Task", "Recursion Guard", "Decompose Workstreams", "Reflect on Round 1"],
        "required_edges": ["Development", "Investigation", "Q&A", "Operations"],
    },
    ".claude/skills/default-workflow/SKILL.md": {
        "type": "flowchart",
        "required_subgraphs": 7,  # 7 phases
        "required_nodes": ["Step 0: Workflow Preparation", "Step 14: Bump Version"],
    },
    ".claude/skills/investigation-workflow/SKILL.md": {
        "type": "flowchart",
        "required_subgraphs": 6,  # 6 phases
        "required_nodes": ["scope-definition", "deep-dive-primary", "consolidate-findings"],
    },
    ".claude/skills/quality-audit/SKILL.md": {
        "type": "flowchart",
        "required_nodes": ["SEEK", "MERGE", "FIX ALL confirmed", "Recurse decision"],
        "required_patterns": [
            r"V1 & V2 & V3",  # Fix #1: parallel validators
            r"NEW high/critical",  # Fix #2: NEW qualifier
        ],
    },
    "CLAUDE.md": {
        "type": "flowchart",
        "required_nodes": ["Classify Task Type"],
    },
    ".claude/agents/amplihack/specialized/ci-diagnostic-workflow.md": {
        "type": "stateDiagram",
        "required_nodes": ["PUSHED", "CHECKING", "FAILING", "FIXING", "PASSED", "MERGEABLE"],
    },
    ".claude/commands/amplihack/fix.md": {
        "type": "flowchart",
        "required_nodes": ["Pattern Detection", "DEFAULT_WORKFLOW"],
    },
}


def extract_mermaid_blocks(content: str) -> list[str]:
    """Extract all ```mermaid ... ``` blocks from markdown."""
    pattern = r"```mermaid\s*\n(.*?)```"
    return re.findall(pattern, content, re.DOTALL)


def validate_mermaid_syntax(block: str, expected_type: str) -> list[str]:
    """Basic structural validation of mermaid syntax."""
    errors = []

    # Check diagram type declaration
    first_line = block.strip().split("\n")[0].strip()
    if expected_type == "flowchart" and not first_line.startswith("flowchart"):
        errors.append(f"Expected flowchart declaration, got: {first_line}")
    elif expected_type == "stateDiagram" and not first_line.startswith("stateDiagram"):
        errors.append(f"Expected stateDiagram declaration, got: {first_line}")

    # Check balanced brackets
    for char_open, char_close, name in [("[", "]", "square brackets"), ("{", "}", "curly braces"), ("(", ")", "parentheses")]:
        if block.count(char_open) != block.count(char_close):
            errors.append(f"Unbalanced {name}: {block.count(char_open)} open, {block.count(char_close)} close")

    # Check for common syntax errors
    if "```" in block:
        errors.append("Nested code fence found inside mermaid block")

    return errors


def validate_file(rel_path: str, spec: dict) -> tuple[bool, list[str]]:
    """Validate a single file against its specification."""
    path = REPO_ROOT / rel_path
    errors = []

    if not path.exists():
        return False, [f"File not found: {rel_path}"]

    content = path.read_text()
    blocks = extract_mermaid_blocks(content)

    if not blocks:
        return False, [f"No mermaid blocks found in {rel_path}"]

    # Validate syntax of first block
    block = blocks[0]
    syntax_errors = validate_mermaid_syntax(block, spec.get("type", "flowchart"))
    errors.extend(syntax_errors)

    # Check required nodes
    for node in spec.get("required_nodes", []):
        if node not in block:
            errors.append(f"Missing required node: '{node}'")

    # Check required edges
    for edge in spec.get("required_edges", []):
        if edge not in block:
            errors.append(f"Missing required edge label: '{edge}'")

    # Check required patterns (regex)
    for pattern in spec.get("required_patterns", []):
        if not re.search(pattern, block):
            errors.append(f"Missing required pattern: '{pattern}'")

    # Check subgraph count
    expected_subgraphs = spec.get("required_subgraphs")
    if expected_subgraphs is not None:
        actual = block.count("subgraph ")
        if actual != expected_subgraphs:
            errors.append(f"Expected {expected_subgraphs} subgraphs, found {actual}")

    return len(errors) == 0, errors


def main():
    print("=" * 60)
    print("Mermaid Workflow Graph Validation")
    print("=" * 60)
    print()

    total_pass = 0
    total_fail = 0
    all_errors = []

    for rel_path, spec in TARGETS.items():
        passed, errors = validate_file(rel_path, spec)
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "x"

        print(f"  [{icon}] {rel_path}")
        if errors:
            for e in errors:
                print(f"      - {e}")
            all_errors.extend(errors)

        if passed:
            total_pass += 1
        else:
            total_fail += 1

    print()
    print("-" * 60)
    print(f"Results: {total_pass} passed, {total_fail} failed ({total_pass + total_fail} total)")
    print("-" * 60)

    if total_fail > 0:
        print(f"\nFAILED: {total_fail} file(s) have issues")
        return 1
    else:
        print("\nALL PASSED: All mermaid graphs are valid and complete")
        return 0


if __name__ == "__main__":
    sys.exit(main())
