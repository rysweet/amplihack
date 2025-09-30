#!/bin/bash
# C# Format Check - Verify code formatting compliance
# Validates that C# files follow formatting standards without making changes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CACHE_DIR="${ROOT_DIR}/.cache/cs-validator"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Check if dotnet is available
if ! command -v dotnet &> /dev/null; then
    echo "✗ dotnet CLI not found. Please install .NET SDK."
    exit 4
fi

# Check if dotnet format is available
if ! dotnet format --version &> /dev/null; then
    echo "⚠ dotnet format not available. Installing..."
    if ! dotnet tool install -g dotnet-format 2>&1 | tee "$CACHE_DIR/format-install.txt"; then
        echo "✗ Failed to install dotnet-format"
        echo "  Please install manually: dotnet tool install -g dotnet-format"
        exit 4
    fi
fi

# Get list of modified files
if [ $# -eq 0 ]; then
    echo "Usage: format-check.sh <file1.cs> [file2.cs ...]"
    exit 2
fi

echo "Verifying code formatting..."

# Build list of files to check
FILES_TO_CHECK=()
for file in "$@"; do
    # Skip if file doesn't exist
    [ ! -f "$file" ] && continue
    FILES_TO_CHECK+=("$file")
done

if [ ${#FILES_TO_CHECK[@]} -eq 0 ]; then
    echo "✗ No valid C# files to check"
    exit 2
fi

# Find solution or project files to format
# We need to format at the project/solution level
declare -a FORMAT_TARGETS=()
declare -a FOUND_TARGETS=()

# First, try to find a solution file in the root
if compgen -G "$ROOT_DIR/*.sln" > /dev/null; then
    solution_file=$(ls "$ROOT_DIR"/*.sln 2>/dev/null | head -1)
    if [ -n "$solution_file" ]; then
        FOUND_TARGETS+=("$solution_file")
    fi
fi

# If no solution found, find unique projects for the modified files
if [ ${#FOUND_TARGETS[@]} -eq 0 ]; then
    for file in "${FILES_TO_CHECK[@]}"; do
        # Find nearest .csproj
        dir=$(dirname "$file")
        while [ "$dir" != "/" ] && [ "$dir" != "." ]; do
            if compgen -G "$dir/*.csproj" > /dev/null; then
                project_file=$(ls "$dir"/*.csproj 2>/dev/null | head -1)
                if [ -n "$project_file" ]; then
                    # Check if we already added this project
                    if [[ ! " ${FOUND_TARGETS[@]:-} " =~ " ${project_file} " ]]; then
                        FOUND_TARGETS+=("$project_file")
                    fi
                    break
                fi
            fi
            dir=$(dirname "$dir")
        done
    done
fi

# Remove duplicates
if [ ${#FOUND_TARGETS[@]} -gt 0 ]; then
    readarray -t FORMAT_TARGETS < <(printf '%s\n' "${FOUND_TARGETS[@]}" | sort -u)
fi

if [ ${#FORMAT_TARGETS[@]} -eq 0 ]; then
    echo "✗ No solution or project files found for formatting"
    exit 1
fi

FORMAT_FAILED=false
VIOLATION_COUNT=0

for target in "${FORMAT_TARGETS[@]}"; do
    target_name=$(basename "$target")
    echo "  Checking format: $target_name"

    # Run dotnet format in verify mode
    # We use --include to only check our modified files
    INCLUDE_ARGS=""
    for file in "${FILES_TO_CHECK[@]}"; do
        INCLUDE_ARGS="$INCLUDE_ARGS --include $file"
    done

    # Run format check
    if dotnet format "$target" \
        --verify-no-changes \
        --verbosity quiet \
        --no-restore \
        $INCLUDE_ARGS \
        > "$CACHE_DIR/format-output-${target_name}.txt" 2>&1; then
        echo "    ✓ Format check passed for $target_name"
    else
        FORMAT_FAILED=true
        echo "    ✗ Format violations found in $target_name"
        echo ""

        # Try to extract specific violations
        if [ -s "$CACHE_DIR/format-output-${target_name}.txt" ]; then
            echo "    Format violations:"
            grep -E "^[[:space:]]*(.*\.cs|Formatted)" "$CACHE_DIR/format-output-${target_name}.txt" | sed 's/^/      /' || true
            VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
        fi
        echo ""
    fi
done

if [ "$FORMAT_FAILED" = true ]; then
    echo "✗ Format validation failed"
    echo ""
    echo "To fix formatting automatically:"
    for target in "${FORMAT_TARGETS[@]}"; do
        echo "  dotnet format \"$target\""
    done
    echo ""
    echo "Or to format all files in the solution:"
    echo "  dotnet format"
    echo ""
    echo "To see detailed output:"
    echo "  cat $CACHE_DIR/format-output-*.txt"
    exit 1
fi

echo "✓ Format validation passed for ${#FORMAT_TARGETS[@]} target(s)"
exit 0
