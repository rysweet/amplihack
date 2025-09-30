#!/bin/bash
# C# Analyzer Check - Run Roslyn analyzers on modified projects
# Validates code quality using static analysis

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CACHE_DIR="${ROOT_DIR}/.cache/cs-validator"
CONFIG_FILE="${ROOT_DIR}/.claude/config/cs-validator.json"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Check if dotnet is available
if ! command -v dotnet &> /dev/null; then
    echo "✗ dotnet CLI not found. Please install .NET SDK."
    exit 4
fi

# Read severity threshold from config (default: Error)
SEVERITY_THRESHOLD="Error"
if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    SEVERITY_THRESHOLD=$(jq -r '.analyzerSeverityThreshold // "Error"' "$CONFIG_FILE")
fi

# Get list of modified files
if [ $# -eq 0 ]; then
    echo "Usage: analyzer-check.sh <file1.cs> [file2.cs ...]"
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
    exit 1
fi

echo "Running code analyzers (threshold: $SEVERITY_THRESHOLD)..."

ANALYZER_FAILED=false
VIOLATION_COUNT=0

for project in "${PROJECTS[@]}"; do
    project_name=$(basename "$project" .csproj)
    echo "  Analyzing: $project_name"

    # Build with analyzers enabled
    # Note: We use build instead of analyze because it's more compatible
    if dotnet build "$project" \
        --no-restore \
        --nologo \
        --verbosity quiet \
        -p:RunAnalyzers=true \
        -p:EnforceCodeStyleInBuild=true \
        -p:GenerateFullPaths=true \
        -p:TreatWarningsAsErrors=false \
        > "$CACHE_DIR/analyzer-output-${project_name}.txt" 2>&1; then
        echo "    ✓ No analyzer violations found in $project_name"
    else
        # Check for analyzer violations in output
        FOUND_VIOLATIONS=false

        # Filter by severity threshold
        case "$SEVERITY_THRESHOLD" in
            Error)
                # Look for analyzer errors
                if grep -E "(error (SA|CA|IDE|CS)[0-9]+)" "$CACHE_DIR/analyzer-output-${project_name}.txt" > "$CACHE_DIR/analyzer-errors-${project_name}.txt" 2>/dev/null; then
                    FOUND_VIOLATIONS=true
                fi
                ;;
            Warning)
                # Look for analyzer warnings and errors
                if grep -E "(warning|error) (SA|CA|IDE|CS)[0-9]+:" "$CACHE_DIR/analyzer-output-${project_name}.txt" > "$CACHE_DIR/analyzer-errors-${project_name}.txt" 2>/dev/null; then
                    FOUND_VIOLATIONS=true
                fi
                ;;
            Info)
                # Look for all analyzer messages
                if grep -E "(info|warning|error) (SA|CA|IDE|CS)[0-9]+:" "$CACHE_DIR/analyzer-output-${project_name}.txt" > "$CACHE_DIR/analyzer-errors-${project_name}.txt" 2>/dev/null; then
                    FOUND_VIOLATIONS=true
                fi
                ;;
        esac

        if [ "$FOUND_VIOLATIONS" = true ]; then
            ANALYZER_FAILED=true
            echo "    ✗ Analyzer violations found in $project_name"
            echo ""

            # Display violations
            echo "    Violations:"
            while IFS= read -r violation_line; do
                echo "      $violation_line"
                VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
            done < "$CACHE_DIR/analyzer-errors-${project_name}.txt"
            echo ""
        else
            # If build failed but no violations matched threshold, it's likely a build error
            # which should have been caught by build-check
            echo "    ⚠ Build failed but no analyzer violations at $SEVERITY_THRESHOLD level"
        fi
    fi
done

if [ "$ANALYZER_FAILED" = true ]; then
    echo "✗ Analyzer validation failed with $VIOLATION_COUNT violation(s)"
    echo ""
    echo "To see full analyzer output:"
    echo "  cat $CACHE_DIR/analyzer-output-*.txt"
    echo ""
    echo "To adjust severity threshold, edit:"
    echo "  $CONFIG_FILE"
    echo "  Set 'analyzerSeverityThreshold' to 'Error', 'Warning', or 'Info'"
    exit 1
fi

echo "✓ Analyzer validation passed for all ${#PROJECTS[@]} project(s)"
exit 0
