#!/bin/bash
# safe_read.sh
#
# SEC-02: Path traversal prevention guard.
#
# Validates that a requested file path resolves to within an allowed boundary
# directory before reading it. This prevents directory traversal attacks of the
# form "../../../etc/passwd" or absolute paths that escape the atlas output tree.
#
# Outputs the file content to stdout if the path is safe.
# Exits with an error and no output if the path is unsafe.
#
# Usage:
#   bash scripts/safe_read.sh <file_path> [--boundary <dir>]
#   content=$(bash scripts/safe_read.sh docs/atlas/layer1-runtime/topology.mmd)
#
# Options:
#   --boundary <dir>   Allowed root directory (default: docs/atlas)
#                      Relative paths are resolved from the git repository root.
#
# Exit codes:
#   0 - Path is safe; file content written to stdout
#   1 - Path traversal detected or file not found / unreadable
#   2 - Usage error

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
FILE_PATH=""
BOUNDARY_DIR="docs/atlas"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --boundary)
            BOUNDARY_DIR="$2"
            shift 2
            ;;
        --help|-h)
            sed -n '3,30p' "$0" | sed 's/^# //'
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
        *)
            if [[ -z "$FILE_PATH" ]]; then
                FILE_PATH="$1"
            else
                echo "Error: Unexpected argument: $1" >&2
                exit 2
            fi
            shift
            ;;
    esac
done

if [[ -z "$FILE_PATH" ]]; then
    echo "Error: No file path provided." >&2
    echo "Usage: $0 <file_path> [--boundary <dir>]" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Resolve the boundary to an absolute canonical path
# ---------------------------------------------------------------------------
# Prefer realpath (GNU coreutils / macOS with coreutils)
# Fall back to Python, then to pwd-based approximation
resolve_canonical() {
    local path="$1"
    if command -v realpath &>/dev/null; then
        realpath -m "$path" 2>/dev/null || echo ""
    elif command -v python3 &>/dev/null; then
        python3 -c "import os; print(os.path.realpath('$path'))" 2>/dev/null || echo ""
    else
        # Best-effort: resolve from PWD without following symlinks
        if [[ "$path" == /* ]]; then
            echo "$path"
        else
            echo "$(pwd)/${path}"
        fi
    fi
}

# Resolve boundary: if relative, anchor to repository root
if [[ "$BOUNDARY_DIR" != /* ]]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    BOUNDARY_DIR="${REPO_ROOT}/${BOUNDARY_DIR}"
fi

CANONICAL_BOUNDARY=$(resolve_canonical "$BOUNDARY_DIR")

if [[ -z "$CANONICAL_BOUNDARY" ]]; then
    echo "Error: Could not resolve boundary directory: ${BOUNDARY_DIR}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Resolve the requested file path
# ---------------------------------------------------------------------------
# Anchor relative paths to the repository root (same convention as boundary)
if [[ "$FILE_PATH" != /* ]]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    FILE_PATH="${REPO_ROOT}/${FILE_PATH}"
fi

CANONICAL_FILE=$(resolve_canonical "$FILE_PATH")

if [[ -z "$CANONICAL_FILE" ]]; then
    echo "Error: Could not resolve file path: ${FILE_PATH}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# SEC-02: Boundary assertion
#
# The canonical file path must begin with the canonical boundary path
# followed by a path separator (to prevent prefix-matching attacks like
# /docs/atlas-evil matching boundary /docs/atlas).
# ---------------------------------------------------------------------------
BOUNDARY_PREFIX="${CANONICAL_BOUNDARY%/}/"   # Ensure trailing slash

if [[ "$CANONICAL_FILE" != "${BOUNDARY_PREFIX}"* && "$CANONICAL_FILE" != "${CANONICAL_BOUNDARY%/}" ]]; then
    echo "Error: Path traversal detected." >&2
    echo "  Requested: ${CANONICAL_FILE}" >&2
    echo "  Boundary:  ${CANONICAL_BOUNDARY}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Additional safety checks
# ---------------------------------------------------------------------------

# Reject symlinks — symlinks can point outside the boundary even if the
# symlink file itself is within it
if [[ -L "$CANONICAL_FILE" ]]; then
    echo "Error: Symlinks are not permitted. Path is a symlink: ${CANONICAL_FILE}" >&2
    exit 1
fi

# File must exist and be a regular file
if [[ ! -f "$CANONICAL_FILE" ]]; then
    echo "Error: File not found or is not a regular file: ${CANONICAL_FILE}" >&2
    exit 1
fi

# File must be readable
if [[ ! -r "$CANONICAL_FILE" ]]; then
    echo "Error: File is not readable: ${CANONICAL_FILE}" >&2
    exit 1
fi

# SEC-08: Reject files larger than 10 MB to prevent DoS
MAX_SIZE_BYTES=$(( 10 * 1024 * 1024 ))
FILE_SIZE=$(wc -c < "$CANONICAL_FILE" 2>/dev/null || echo "0")

if [[ "$FILE_SIZE" -gt "$MAX_SIZE_BYTES" ]]; then
    echo "Error: File exceeds 10 MB size limit (${FILE_SIZE} bytes): ${CANONICAL_FILE}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Safe to read — emit contents to stdout
# ---------------------------------------------------------------------------
cat "$CANONICAL_FILE"
