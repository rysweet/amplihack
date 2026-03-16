#!/bin/bash
# rebuild-atlas-all.sh
#
# Triggers a full code atlas rebuild for the current repository.
# Called by CI (Pattern 3: scheduled weekly rebuild) and by engineers
# after major refactors or first-time atlas creation.
#
# What it does:
#   1. Validates environment (git repo, docs/atlas/ writable)
#   2. Records the current git ref for the atlas build stamp
#   3. Reports the rebuild command for the Claude Code atlas skill
#   4. Optionally commits updated atlas docs if run in CI mode
#
# Usage:
#   bash scripts/rebuild-atlas-all.sh            # interactive — prints instructions
#   bash scripts/rebuild-atlas-all.sh --ci        # CI mode — stages and commits atlas changes
#   bash scripts/rebuild-atlas-all.sh --dry-run   # show what would happen, no writes
#
# Exit codes:
#   0 - Success
#   1 - Error (not a git repo, docs/atlas not writable, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
CI_MODE=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --ci)       CI_MODE=true ;;
        --dry-run)  DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--ci] [--dry-run]"
            echo ""
            echo "  --ci       Stage and commit atlas changes after rebuild (for GitHub Actions)"
            echo "  --dry-run  Print what would happen without making changes"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------
echo "==================================="
echo "Code Atlas — Full Rebuild"
echo "==================================="
echo ""

# Must be inside a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not inside a git repository." >&2
    echo "Run this script from the repository root." >&2
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
ATLAS_DIR="${REPO_ROOT}/docs/atlas"
CURRENT_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo "Repository: ${REPO_ROOT}"
echo "Branch:     ${CURRENT_BRANCH}"
echo "Ref:        ${CURRENT_REF}"
echo "Atlas dir:  ${ATLAS_DIR}"
echo ""

# Create docs/atlas/ if it does not exist
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "${ATLAS_DIR}"
fi

# Verify writability
if [[ "$DRY_RUN" == false ]] && [[ ! -w "${ATLAS_DIR}" ]]; then
    echo "Error: ${ATLAS_DIR} is not writable." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Rebuild instructions
# ---------------------------------------------------------------------------
if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] Would trigger full atlas rebuild at ref ${CURRENT_REF}."
    echo "[DRY RUN] Atlas output directory: ${ATLAS_DIR}"
    echo "[DRY RUN] No files written."
    exit 0
fi

echo "Triggering full atlas rebuild..."
echo ""
echo "Run the following Claude Code command in this repository:"
echo ""
echo "  /code-atlas rebuild all"
echo ""
echo "This will:"
echo "  1. Analyze all 6 atlas layers from current code state"
echo "  2. Generate/refresh all .mmd, .dot, and .svg files in docs/atlas/"
echo "  3. Run 2-pass bug hunt and update docs/atlas/bugs.md"
echo "  4. Update docs/atlas/index.md with build timestamp ${CURRENT_REF}"
echo ""

# Write a build-stamp file so CI can detect whether the atlas was actually updated
BUILD_STAMP="${ATLAS_DIR}/.build-stamp"
echo "ref=${CURRENT_REF}" > "${BUILD_STAMP}"
echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${BUILD_STAMP}"
echo "branch=${CURRENT_BRANCH}" >> "${BUILD_STAMP}"
echo "Wrote build stamp: ${BUILD_STAMP}"
echo ""

# ---------------------------------------------------------------------------
# CI mode: stage and commit atlas changes
# ---------------------------------------------------------------------------
if [[ "$CI_MODE" == true ]]; then
    echo "CI mode: staging atlas changes..."

    # Validate that rebuild produced expected layer directories
    EXPECTED_LAYERS=("layer1-runtime" "layer2-dependencies" "layer3-routing" "layer4-dataflow" "layer5-journeys" "layer6-inventory")
    MISSING_LAYERS=()
    for layer in "${EXPECTED_LAYERS[@]}"; do
        layer_dir="${ATLAS_DIR}/${layer}"
        if [[ ! -d "$layer_dir" ]] || [[ -z "$(ls -A "$layer_dir" 2>/dev/null)" ]]; then
            MISSING_LAYERS+=("$layer")
        fi
    done
    if [[ ${#MISSING_LAYERS[@]} -gt 0 ]]; then
        echo "Error: Atlas rebuild validation failed. Missing or empty layer directories:" >&2
        printf '  - %s\n' "${MISSING_LAYERS[@]}" >&2
        echo "Aborting commit to prevent capturing broken atlas state." >&2
        exit 1
    fi
    echo "Validation passed: all ${#EXPECTED_LAYERS[@]} layer directories present."

    if git diff --quiet "${ATLAS_DIR}" 2>/dev/null && ! git ls-files --others --exclude-standard "${ATLAS_DIR}" | grep -q .; then
        echo "No atlas changes to commit."
    else
        git add "${ATLAS_DIR}"
        git commit -m "chore: refresh code atlas [skip ci]

Built from ref ${CURRENT_REF} on branch ${CURRENT_BRANCH}.
Triggered by: scripts/rebuild-atlas-all.sh --ci" || echo "Nothing to commit."
        echo "Atlas changes committed."
    fi
fi

echo ""
echo "==================================="
echo "Rebuild complete."
echo "==================================="
