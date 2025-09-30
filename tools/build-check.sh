#!/bin/bash
# C# Build Check - Incremental build validation for modified projects
# Validates that modified C# files compile successfully

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CACHE_DIR="${ROOT_DIR}/.cache/cs-validator"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Check if dotnet is available
if ! command -v dotnet &> /dev/null; then
    echo "✗ dotnet CLI not found. Please install .NET SDK."
    echo "  Visit: https://dotnet.microsoft.com/download"
    exit 4
fi

# Get list of modified files
if [ $# -eq 0 ]; then
    echo "Usage: build-check.sh <file1.cs> [file2.cs ...]"
    exit 2
fi

# Extract unique project directories from modified files
declare -a PROJECTS=()
declare -a FOUND_PROJECTS=()

for file in "$@"; do
    # Skip if file doesn't exist
    [ ! -f "$file" ] && continue

    # Find nearest .csproj
    dir=$(dirname "$file")
    while [ "$dir" != "/" ] && [ "$dir" != "." ]; do
        # Look for .csproj files in current directory
        if compgen -G "$dir/*.csproj" > /dev/null; then
            project_file=$(ls "$dir"/*.csproj 2>/dev/null | head -1)
            if [ -n "$project_file" ]; then
                # Check if we already added this project
                if [[ ! " ${FOUND_PROJECTS[@]:-} " =~ " ${project_file} " ]]; then
                    FOUND_PROJECTS+=("$project_file")
                fi
                break
            fi
        fi
        dir=$(dirname "$dir")
    done
done

# Remove duplicates and store in PROJECTS array
if [ ${#FOUND_PROJECTS[@]} -gt 0 ]; then
    readarray -t PROJECTS < <(printf '%s\n' "${FOUND_PROJECTS[@]}" | sort -u)
fi

if [ ${#PROJECTS[@]} -eq 0 ]; then
    echo "✗ No .csproj files found for modified C# files"
    echo "  Modified files may not be part of a valid project structure"
    exit 1
fi

echo "Building ${#PROJECTS[@]} affected project(s)..."

BUILD_FAILED=false
ERROR_COUNT=0

for project in "${PROJECTS[@]}"; do
    project_name=$(basename "$project" .csproj)
    echo "  Building: $project_name"

    # Build with minimal output, no restore (assume already restored)
    # We use quiet verbosity to reduce noise but capture errors
    if dotnet build "$project" \
        --no-restore \
        --nologo \
        --verbosity quiet \
        -p:TreatWarningsAsErrors=false \
        -p:GenerateFullPaths=true \
        > "$CACHE_DIR/build-output-${project_name}.txt" 2>&1; then
        echo "    ✓ $project_name built successfully"
    else
        BUILD_FAILED=true
        echo "    ✗ $project_name build failed"
        echo ""

        # Extract and display errors only
        if grep -E "error CS[0-9]+:" "$CACHE_DIR/build-output-${project_name}.txt" > "$CACHE_DIR/errors-${project_name}.txt" 2>/dev/null; then
            echo "    Errors found:"
            while IFS= read -r error_line; do
                echo "      $error_line"
                ERROR_COUNT=$((ERROR_COUNT + 1))
            done < "$CACHE_DIR/errors-${project_name}.txt"
        else
            # Show last 20 lines if no specific errors found
            echo "    Build output (last 20 lines):"
            tail -20 "$CACHE_DIR/build-output-${project_name}.txt" | sed 's/^/      /'
        fi
        echo ""
    fi
done

if [ "$BUILD_FAILED" = true ]; then
    echo "✗ Build validation failed with $ERROR_COUNT error(s)"
    echo ""
    echo "To see full build output:"
    echo "  cat $CACHE_DIR/build-output-*.txt"
    echo ""
    echo "To build manually:"
    for project in "${PROJECTS[@]}"; do
        echo "  dotnet build \"$project\""
    done
    exit 1
fi

echo "✓ Build validation passed for all ${#PROJECTS[@]} project(s)"
exit 0
