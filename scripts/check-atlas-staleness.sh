#!/bin/bash
# check-atlas-staleness.sh
#
# Checks whether the code atlas docs are stale by comparing recently changed
# files against the staleness trigger table defined in skills/code-atlas/SKILL.md.
#
# Usage:
#   bash scripts/check-atlas-staleness.sh               # diff HEAD~1..HEAD
#   bash scripts/check-atlas-staleness.sh <base> <head> # diff <base>..<head>
#   bash scripts/check-atlas-staleness.sh --pr           # diff origin/main...HEAD
#
# Exit codes:
#   0 - Atlas is fresh (no stale layers detected)
#   1 - One or more atlas layers are stale
#   2 - Usage error

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
BASE_REF=""
HEAD_REF=""
MODE="commit"

if [[ "${1:-}" == "--pr" ]]; then
    MODE="pr"
elif [[ -n "${1:-}" && -n "${2:-}" ]]; then
    BASE_REF="$1"
    HEAD_REF="$2"
    MODE="range"
elif [[ -n "${1:-}" ]]; then
    echo "Error: Provide both <base> and <head>, or use --pr" >&2
    echo "Usage: $0 [--pr | <base> <head>]" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Compute changed file list
# ---------------------------------------------------------------------------
case "$MODE" in
    pr)
        CHANGED_FILES=$(git diff --name-only "$(git merge-base origin/main HEAD)"...HEAD 2>/dev/null || git diff --name-only origin/main...HEAD)
        ;;
    range)
        CHANGED_FILES=$(git diff --name-only "${BASE_REF}..${HEAD_REF}")
        ;;
    commit)
        CHANGED_FILES=$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only HEAD)
        ;;
esac

if [[ -z "$CHANGED_FILES" ]]; then
    echo "No changed files detected. Atlas is fresh."
    exit 0
fi

# ---------------------------------------------------------------------------
# Staleness detection — trigger table from SKILL.md
#
# Layer 1: docker-compose*.yml, k8s/**/*.yaml
# Layer 2: go.mod, package.json, *.csproj, Cargo.toml, requirements*.txt, pyproject.toml
# Layer 3: *routes*.ts, *controller*.go, *views*.py, *router*.ts, *router*.go
# Layer 4: *dto*.ts, *schema*.py, *_request.go, *_response.go, *types*.ts
# Layer 5: user-facing page/CLI files (*page*.tsx, *page*.ts, cmd/**/*.go, cli/**/*.py)
# Layer 6: .env.example, service README.md files
# ---------------------------------------------------------------------------

STALE_LAYERS=()

check_layer() {
    local layer="$1"
    local label="$2"
    local rebuild_cmd="$3"
    local already_stale=false

    for f in $CHANGED_FILES; do
        local matched=false
        case "$layer" in
            1)
                [[ "$f" == *docker-compose*.yml ]] && matched=true
                [[ "$f" == *docker-compose*.yaml ]] && matched=true
                [[ "$f" == */k8s/*.yaml ]] && matched=true
                [[ "$f" == k8s/*.yaml ]] && matched=true
                [[ "$f" == kubernetes/*.yaml ]] && matched=true
                [[ "$f" == */kubernetes/*.yaml ]] && matched=true
                [[ "$f" == helm/*.yaml ]] && matched=true
                [[ "$f" == helm/*/*.yaml ]] && matched=true
                [[ "$f" == */helm/*.yaml ]] && matched=true
                [[ "$f" == */helm/*/*.yaml ]] && matched=true
                ;;
            2)
                [[ "$f" == go.mod ]] && matched=true
                [[ "$f" == */go.mod ]] && matched=true
                [[ "$f" == package.json ]] && matched=true
                [[ "$f" == */package.json ]] && matched=true
                [[ "$f" == *.csproj ]] && matched=true
                [[ "$f" == Cargo.toml ]] && matched=true
                [[ "$f" == */Cargo.toml ]] && matched=true
                [[ "$f" == requirements*.txt ]] && matched=true
                [[ "$f" == */requirements*.txt ]] && matched=true
                [[ "$f" == pyproject.toml ]] && matched=true
                [[ "$f" == */pyproject.toml ]] && matched=true
                ;;
            3)
                [[ "$f" == *route*.ts ]] && matched=true
                [[ "$f" == *route*.go ]] && matched=true
                [[ "$f" == *controller*.go ]] && matched=true
                [[ "$f" == *controller*.ts ]] && matched=true
                [[ "$f" == *views*.py ]] && matched=true
                [[ "$f" == *router*.ts ]] && matched=true
                [[ "$f" == *router*.go ]] && matched=true
                [[ "$f" == *handler*.go ]] && matched=true
                ;;
            4)
                [[ "$f" == *dto*.ts ]] && matched=true
                [[ "$f" == *schema*.py ]] && matched=true
                [[ "$f" == *_request.go ]] && matched=true
                [[ "$f" == *_response.go ]] && matched=true
                [[ "$f" == *types*.ts ]] && matched=true
                [[ "$f" == *model*.go ]] && matched=true
                ;;
            5)
                [[ "$f" == *page*.tsx ]] && matched=true
                [[ "$f" == *page*.ts ]] && matched=true
                [[ "$f" == cmd/*.go ]] && matched=true
                [[ "$f" == */cmd/*.go ]] && matched=true
                [[ "$f" == cli/*.py ]] && matched=true
                [[ "$f" == */cli/*.py ]] && matched=true
                ;;
            6)
                [[ "$f" == .env.example ]] && matched=true
                [[ "$f" == */.env.example ]] && matched=true
                # Service-level README changes (not root README)
                [[ "$f" == services/*/README.md ]] && matched=true
                [[ "$f" == apps/*/README.md ]] && matched=true
                ;;
        esac

        if [[ "$matched" == true && "$already_stale" == false ]]; then
            echo "Layer ${layer} STALE: ${label} — triggered by: ${f}"
            echo "  Rebuild: /code-atlas rebuild layer${layer}   # or: ${rebuild_cmd}"
            STALE_LAYERS+=("$layer")
            already_stale=true
        fi
    done
}

check_layer 1 "Runtime Topology"       "code-atlas rebuild layer1"
check_layer 2 "Compile-time Deps"      "code-atlas rebuild layer2"
check_layer 3 "HTTP Routing"           "code-atlas rebuild layer3"
check_layer 4 "Data Flows"             "code-atlas rebuild layer4"
check_layer 5 "User Journey Scenarios" "code-atlas rebuild layer5"
check_layer 6 "Exhaustive Inventory"   "code-atlas rebuild layer6"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [[ ${#STALE_LAYERS[@]} -eq 0 ]]; then
    echo "Atlas is fresh. No stale layers detected."
    exit 0
else
    UNIQUE_LAYERS=($(printf '%s\n' "${STALE_LAYERS[@]}" | sort -u))
    echo ""
    echo "Summary: ${#UNIQUE_LAYERS[@]} layer(s) stale: [${UNIQUE_LAYERS[*]}]"
    echo "Run '/code-atlas rebuild all' to refresh the full atlas."
    exit 1
fi
