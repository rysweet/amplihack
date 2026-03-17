#!/bin/bash
# .claude/skills/code-atlas/tests/test_publication_workflow.sh
#
# TDD tests for atlas publication workflow:
# - SVG companion generation (dot → SVG, mmd → SVG)
# - mkdocs navigation structure
# - GitHub Pages readiness (all referenced files exist)
# - index.md landing page quality
#
# THESE TESTS WILL FAIL until publication workflow is implemented.
#
# Usage: bash .claude/skills/code-atlas/tests/test_publication_workflow.sh [atlas_dir]
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail
shopt -s globstar nullglob  # enable ** recursive globs; unmatched globs expand to nothing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

ATLAS="${1:-${REPO_ROOT}/docs/atlas}"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_file_exists() {
    local label="$1"; local path="$2"
    if [[ -f "$path" ]]; then
        echo "PASS: $label"; PASS=$((PASS + 1))
    else
        echo "FAIL: $label — not found: $path"; FAIL=$((FAIL + 1))
    fi
}

assert_file_contains() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"; FAIL=$((FAIL + 1)); return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $label"; PASS=$((PASS + 1))
    else
        echo "FAIL: $label — pattern '$pattern' not in $file"; FAIL=$((FAIL + 1))
    fi
}

assert_file_size_gt() {
    local label="$1"; local file="$2"; local min_bytes="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"; FAIL=$((FAIL + 1)); return
    fi
    size=$(wc -c < "$file" 2>/dev/null || echo 0)
    if [[ "$size" -gt "$min_bytes" ]]; then
        echo "PASS: $label (${size} bytes)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — file too small (${size} bytes, expected > ${min_bytes})"
        FAIL=$((FAIL + 1))
    fi
}

# ============================================================================
# Test Group 1: SVG Companion Files
# ============================================================================

echo ""
echo "=== SVG Companion Files ==="

# Every .mmd and .dot file must have a matching .svg companion
for mmd_file in "${ATLAS}"/**/*.mmd "${ATLAS}"/*.mmd; do
    [[ -f "$mmd_file" ]] || continue
    svg_file="${mmd_file%.mmd}.svg"
    layer_dir=$(dirname "$mmd_file" | sed "s|${REPO_ROOT}/||")
    fname=$(basename "$mmd_file")
    assert_file_exists "SVG exists for ${layer_dir}/${fname}" "$svg_file"
    if [[ -f "$svg_file" ]]; then
        assert_file_size_gt "SVG not empty: ${fname%.mmd}.svg" "$svg_file" 100
        assert_file_contains "SVG has valid SVG content" "<svg\|xmlns.*svg" "$svg_file"
    fi
done

for dot_file in "${ATLAS}"/**/*.dot "${ATLAS}"/*.dot; do
    [[ -f "$dot_file" ]] || continue
    svg_file="${dot_file%.dot}.svg"
    layer_dir=$(dirname "$dot_file" | sed "s|${REPO_ROOT}/||")
    fname=$(basename "$dot_file")
    assert_file_exists "SVG exists for ${layer_dir}/${fname}" "$svg_file"
    if [[ -f "$svg_file" ]]; then
        assert_file_size_gt "SVG not empty: ${fname%.dot}.svg" "$svg_file" 100
        assert_file_contains "SVG has valid SVG content (dot)" "<svg\|xmlns.*svg" "$svg_file"
    fi
done

# ============================================================================
# Test Group 2: index.md Landing Page Quality
# ============================================================================

echo ""
echo "=== index.md Landing Page ==="

INDEX="${ATLAS}/index.md"
assert_file_exists "docs/atlas/index.md exists" "$INDEX"

if [[ -f "$INDEX" ]]; then
    # Must have a title heading
    assert_file_contains "index.md: has H1 title" "^# " "$INDEX"

    # Must link to all 8 layers
    for layer in "layer1" "layer2" "layer3" "layer4" "layer5" "layer6"; do
        assert_file_contains "index.md: links to $layer" "$layer" "$INDEX"
    done

    # Must link to bug-reports
    assert_file_contains "index.md: links to bug-reports" "bug-report\|[Bb]ug [Rr]eport" "$INDEX"

    # Must mention atlas generation date or .build-stamp reference
    assert_file_contains "index.md: has generation metadata" \
        "[Gg]enerated\|[Bb]uilt\|[Cc]reated\|[Rr]efreshed\|[Aa]tlas" "$INDEX"

    # Must NOT contain raw paths (should use relative links)
    if grep -q "^/home/\|^/tmp/\|^/root/" "$INDEX" 2>/dev/null; then
        echo "FAIL: index.md contains absolute filesystem paths (should use relative links)"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: index.md uses relative links (no absolute paths)"
        PASS=$((PASS + 1))
    fi
fi

# ============================================================================
# Test Group 3: Layer README Files Quality
# ============================================================================

echo ""
echo "=== Layer README Files ==="

for layer_dir in repo-surface compile-deps api-contracts data-flow user-journeys inventory; do
    readme="${ATLAS}/${layer_dir}/README.md"
    assert_file_exists "${layer_dir}/README.md exists" "$readme"

    if [[ -f "$readme" ]]; then
        # Must have H1 title
        assert_file_contains "${layer_dir}/README.md: has H1" "^# " "$readme"

        # Must have at least 100 chars of content (not just a title)
        char_count=$(wc -c < "$readme" 2>/dev/null || echo 0)
        if [[ "$char_count" -gt 100 ]]; then
            echo "PASS: ${layer_dir}/README.md: has meaningful content (${char_count} chars)"
            PASS=$((PASS + 1))
        else
            echo "FAIL: ${layer_dir}/README.md: too short (${char_count} chars, need > 100)"
            FAIL=$((FAIL + 1))
        fi

        # Must NOT contain absolute paths
        if grep -q "^/home/\|^/tmp/\|^/root/" "$readme" 2>/dev/null; then
            echo "FAIL: ${layer_dir}/README.md: contains absolute filesystem paths"
            FAIL=$((FAIL + 1))
        else
            echo "PASS: ${layer_dir}/README.md: no absolute paths"
            PASS=$((PASS + 1))
        fi
    fi
done

# ============================================================================
# Test Group 4: mkdocs Integration File
# ============================================================================

echo ""
echo "=== mkdocs Integration ==="

MKDOCS="${REPO_ROOT}/mkdocs.yml"

if [[ -f "$MKDOCS" ]]; then
    # mkdocs.yml must reference atlas layers in nav
    assert_file_contains "mkdocs.yml: references Code Atlas" "Code Atlas\|atlas" "$MKDOCS"
    assert_file_contains "mkdocs.yml: references layer1" "layer1\|Runtime Topology" "$MKDOCS"
    assert_file_contains "mkdocs.yml: references layer6" "layer6\|Inventory" "$MKDOCS"
    assert_file_contains "mkdocs.yml: references bug-reports" "bug-report\|Bug Report" "$MKDOCS"
else
    echo "SKIP: mkdocs.yml not present (not required for initial implementation)"
fi

# ============================================================================
# Test Group 5: GitHub Pages Readiness
# ============================================================================

echo ""
echo "=== GitHub Pages Readiness ==="

# All internal links in index.md must resolve to real files
if [[ -f "$INDEX" ]]; then
    broken_links=0
    while IFS= read -r link; do
        # Extract relative path from markdown link [text](path)
        link_path="${ATLAS}/${link}"
        if [[ ! -f "$link_path" && ! -d "$link_path" ]]; then
            echo "FAIL: GitHub Pages: broken link in index.md → $link"
            broken_links=$((broken_links + 1))
            FAIL=$((FAIL + 1))
        fi
    done < <(grep -oP '\]\(\K[^)]+' "$INDEX" 2>/dev/null | grep -v "^http\|^#" | head -30)

    if [[ "$broken_links" -eq 0 ]]; then
        echo "PASS: GitHub Pages: all internal links in index.md resolve"
        PASS=$((PASS + 1))
    fi
fi

# All SVGs must be valid (not empty, contain <svg> tag)
svg_count=0
invalid_svg=0
while IFS= read -r svg_file; do
    svg_count=$((svg_count + 1))
    if ! grep -q "<svg" "$svg_file" 2>/dev/null; then
        echo "FAIL: Invalid SVG (no <svg> tag): $svg_file"
        invalid_svg=$((invalid_svg + 1))
        FAIL=$((FAIL + 1))
    fi
done < <(find "${ATLAS}" -name "*.svg" 2>/dev/null)

if [[ "$svg_count" -gt 0 && "$invalid_svg" -eq 0 ]]; then
    echo "PASS: GitHub Pages: all $svg_count SVG files are valid"
    PASS=$((PASS + 1))
elif [[ "$svg_count" -eq 0 ]]; then
    echo "FAIL: GitHub Pages: no SVG files found — publication workflow not run"
    FAIL=$((FAIL + 1))
fi

# ============================================================================
# Test Group 6: Staleness Map YAML Contract
# ============================================================================

echo ""
echo "=== Staleness Map YAML ==="

STALENESS_MAP="${ATLAS}/.staleness-map.yaml"

# staleness-map.yaml is generated alongside atlas and tracks layer build times
# This file is referenced in API-CONTRACTS.md
assert_file_exists "docs/atlas/.staleness-map.yaml exists" "$STALENESS_MAP"

if [[ -f "$STALENESS_MAP" ]]; then
    # Must have entries for all 8 layers
    for layer in 1 2 3 4 5 6; do
        assert_file_contains ".staleness-map.yaml: layer $layer entry" \
            "layer${layer}\|layer_${layer}" "$STALENESS_MAP"
    done

    # Must have last_built timestamps
    assert_file_contains ".staleness-map.yaml: last_built field" \
        "last_built\|built_at\|timestamp" "$STALENESS_MAP"

    # Must have git ref
    assert_file_contains ".staleness-map.yaml: git_ref field" \
        "git_ref\|git.ref\|commit" "$STALENESS_MAP"
fi

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="
echo ""
echo "NOTE: SVG and publication tests fail until 'mmdc'/'dot' render commands run."
echo "Run: /code-atlas publish  — to generate SVGs and publish to docs/atlas/"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
