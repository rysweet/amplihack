#!/bin/bash
# render-atlas-svg.sh
#
# Renders Mermaid (.mmd) and Graphviz (.dot) source files to SVG.
# Implements a two-tier renderer with graceful degradation:
#
#   Primary:   mmdc (Mermaid CLI)  — for .mmd files
#   Primary:   dot  (Graphviz)     — for .dot files
#   Fallback:  Skip with warning   — when tools are absent (CI without renderer)
#
# External service dependencies:
#   - mmdc  (npm install -g @mermaid-js/mermaid-cli)
#   - dot   (apt install graphviz  /  brew install graphviz)
#
# Usage:
#   bash scripts/render-atlas-svg.sh [--atlas-dir <path>] [--dry-run] [--strict]
#
# Options:
#   --atlas-dir <path>   Path to docs/atlas/ (default: docs/atlas)
#   --dry-run            Print what would be rendered without writing files
#   --strict             Exit 1 if any renderer tool is missing (fail-fast for CI)
#   --file <path>        Render a single .mmd or .dot file (one-shot mode)
#
# Exit codes:
#   0 - All files rendered (or gracefully skipped when tools absent)
#   1 - A rendering error occurred for a file that was attempted
#   2 - Usage error

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RETRY_ATTEMPTS=3
RETRY_DELAY_BASE=2   # seconds; exponential: 2, 4, 8
MMDC_TIMEOUT=60      # seconds per diagram
DOT_TIMEOUT=30       # seconds per diagram

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
ATLAS_DIR="docs/atlas"
DRY_RUN=false
STRICT=false
SINGLE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --atlas-dir)
            ATLAS_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --strict)
            STRICT=true
            shift
            ;;
        --file)
            SINGLE_FILE="$2"
            shift 2
            ;;
        --help|-h)
            sed -n '3,30p' "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Renderer availability detection
# ---------------------------------------------------------------------------
MMDC_AVAILABLE=false
DOT_AVAILABLE=false

if command -v mmdc &>/dev/null; then
    MMDC_AVAILABLE=true
fi

if command -v dot &>/dev/null; then
    DOT_AVAILABLE=true
fi

if [[ "$STRICT" == true ]]; then
    if [[ "$MMDC_AVAILABLE" == false ]]; then
        echo "Error (strict): mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
        exit 1
    fi
    if [[ "$DOT_AVAILABLE" == false ]]; then
        echo "Error (strict): dot not found. Install with: apt install graphviz / brew install graphviz" >&2
        exit 1
    fi
fi

echo "Renderer status:"
echo "  mmdc (Mermaid CLI): $([ "$MMDC_AVAILABLE" == true ] && echo 'available' || echo 'not found — .mmd files will be skipped')"
echo "  dot  (Graphviz):    $([ "$DOT_AVAILABLE"  == true ] && echo 'available' || echo 'not found — .dot files will be skipped')"
echo ""

# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------
# Usage: retry_render <max_attempts> <delay_base> <command...>
# Returns the exit code of the final attempt.
retry_render() {
    local max_attempts="$1"
    local delay_base="$2"
    shift 2
    local cmd=("$@")
    local attempt=1
    local delay=$delay_base

    while [[ $attempt -le $max_attempts ]]; do
        if "${cmd[@]}"; then
            return 0
        fi
        local rc=$?
        if [[ $attempt -lt $max_attempts ]]; then
            echo "  Attempt ${attempt}/${max_attempts} failed (exit ${rc}). Retrying in ${delay}s..." >&2
            sleep "$delay"
            delay=$(( delay * 2 ))
        fi
        (( attempt++ ))
    done
    echo "  All ${max_attempts} attempts failed." >&2
    return 1
}

# ---------------------------------------------------------------------------
# Single-file render
# ---------------------------------------------------------------------------
render_mmd_file() {
    local src="$1"
    local dst="${src%.mmd}.svg"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would render: ${src} → ${dst}"
        return 0
    fi

    if [[ "$MMDC_AVAILABLE" == false ]]; then
        echo "  SKIP (mmdc absent): ${src}"
        return 0
    fi

    echo "  Rendering: ${src} → ${dst}"
    if retry_render "$RETRY_ATTEMPTS" "$RETRY_DELAY_BASE" \
        timeout "$MMDC_TIMEOUT" mmdc \
            --input  "$src"  \
            --output "$dst"  \
            --backgroundColor transparent \
            --quiet 2>/dev/null; then
        echo "  OK: ${dst}"
        return 0
    else
        echo "  ERROR: Failed to render ${src}" >&2
        return 1
    fi
}

render_dot_file() {
    local src="$1"
    local dst="${src%.dot}.svg"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would render: ${src} → ${dst}"
        return 0
    fi

    if [[ "$DOT_AVAILABLE" == false ]]; then
        echo "  SKIP (dot absent): ${src}"
        return 0
    fi

    echo "  Rendering: ${src} → ${dst}"
    if retry_render "$RETRY_ATTEMPTS" "$RETRY_DELAY_BASE" \
        timeout "$DOT_TIMEOUT" dot \
            -Tsvg \
            -o "$dst" \
            "$src"; then
        echo "  OK: ${dst}"
        return 0
    else
        echo "  ERROR: Failed to render ${src}" >&2
        return 1
    fi
}

# ---------------------------------------------------------------------------
# One-shot mode: render a single file
# ---------------------------------------------------------------------------
if [[ -n "$SINGLE_FILE" ]]; then
    if [[ ! -f "$SINGLE_FILE" ]]; then
        echo "Error: File not found: $SINGLE_FILE" >&2
        exit 2
    fi
    case "$SINGLE_FILE" in
        *.mmd) render_mmd_file "$SINGLE_FILE" ;;
        *.dot) render_dot_file "$SINGLE_FILE" ;;
        *)
            echo "Error: Unsupported file type (expected .mmd or .dot): $SINGLE_FILE" >&2
            exit 2
            ;;
    esac
    exit $?
fi

# ---------------------------------------------------------------------------
# Batch mode: render all .mmd and .dot files under ATLAS_DIR
# ---------------------------------------------------------------------------
if [[ ! -d "$ATLAS_DIR" ]]; then
    echo "Atlas directory not found: ${ATLAS_DIR}"
    echo "Nothing to render."
    exit 0
fi

echo "Scanning: ${ATLAS_DIR}"
echo ""

RENDERED=0
SKIPPED=0
ERRORS=0

# Render .mmd files
while IFS= read -r -d '' mmd_file; do
    if render_mmd_file "$mmd_file"; then
        (( RENDERED++ )) || true
    else
        (( ERRORS++ )) || true
    fi
done < <(find "$ATLAS_DIR" -name '*.mmd' -print0 2>/dev/null)

# Render .dot files
while IFS= read -r -d '' dot_file; do
    if render_dot_file "$dot_file"; then
        (( RENDERED++ )) || true
    else
        (( ERRORS++ )) || true
    fi
done < <(find "$ATLAS_DIR" -name '*.dot' -print0 2>/dev/null)

# Count skipped = files found but renderer absent
MMD_COUNT=$(find "$ATLAS_DIR" -name '*.mmd' 2>/dev/null | wc -l | tr -d ' ')
DOT_COUNT=$(find "$ATLAS_DIR" -name '*.dot' 2>/dev/null | wc -l | tr -d ' ')

if [[ "$MMDC_AVAILABLE" == false ]]; then
    SKIPPED=$(( SKIPPED + MMD_COUNT ))
fi
if [[ "$DOT_AVAILABLE" == false ]]; then
    SKIPPED=$(( SKIPPED + DOT_COUNT ))
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==================================="
echo "SVG Render Summary"
echo "==================================="
echo "  Rendered: ${RENDERED}"
echo "  Skipped:  ${SKIPPED} (renderer tool absent)"
echo "  Errors:   ${ERRORS}"
echo "==================================="

if [[ $ERRORS -gt 0 ]]; then
    echo "Some files failed to render. Check output above for details."
    exit 1
fi

exit 0
