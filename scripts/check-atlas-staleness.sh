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
    # Validate that both refs contain only characters valid in a git ref/SHA.
    # This prevents shell metacharacter injection via CI-supplied github.event.pull_request.*.sha
    # values. Allowed: hex digits, alphanumerics, dots, slashes, hyphens, underscores,
    # tildes (~) and carets (^) for git ancestry notation (e.g. HEAD~1, main^).
    if ! [[ "$BASE_REF" =~ ^[0-9a-zA-Z/._~^-]+$ ]]; then
        echo "Error: BASE_REF contains invalid characters: ${BASE_REF}" >&2
        exit 2
    fi
    if ! [[ "$HEAD_REF" =~ ^[0-9a-zA-Z/._~^-]+$ ]]; then
        echo "Error: HEAD_REF contains invalid characters: ${HEAD_REF}" >&2
        exit 2
    fi
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
        # Fallback: if merge-base is unavailable (shallow clone, no common ancestor),
        # fall back to a direct three-dot diff. This is intentional CI robustness, not
        # silent degradation — the diff is always computed; only the base revision differs.
        CHANGED_FILES=$(git diff --name-only "$(git merge-base origin/main HEAD)"...HEAD 2>/dev/null || git diff --name-only origin/main...HEAD)
        ;;
    range)
        CHANGED_FILES=$(git diff --name-only "${BASE_REF}..${HEAD_REF}")
        ;;
    commit)
        # Fallback: HEAD~1 does not exist on the first commit of a repo. Silently
        # falling back to `git diff --name-only HEAD` (initial commit diff) is
        # intentional — the staleness check still runs; it simply diffs against the
        # empty tree rather than the previous commit.
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
# Layer 7: any source file in a service directory (internal module structure changes)
# Layer 8: any source file (function signatures, exports, imports affect symbol bindings)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Staleness detection — single pass over changed files
#
# Guard blocks skip pattern checks for layers already confirmed stale,
# reducing work as layers are marked. The short-circuit break exits once
# all 8 layers are stale so no further files need scanning.
# ---------------------------------------------------------------------------
declare -A STALE_SET=()

while IFS= read -r f; do
    [[ -z "$f" ]] && continue

    # Layer 1: Runtime Topology
    if [[ -z "${STALE_SET[1]:-}" ]]; then
        if  [[ "$f" == *docker-compose*.yml  ]] || \
            [[ "$f" == *docker-compose*.yaml ]] || \
            [[ "$f" == */k8s/*.yaml          ]] || \
            [[ "$f" == k8s/*.yaml            ]] || \
            [[ "$f" == kubernetes/*.yaml     ]] || \
            [[ "$f" == */kubernetes/*.yaml   ]] || \
            [[ "$f" == helm/*.yaml           ]] || \
            [[ "$f" == helm/*/*.yaml         ]] || \
            [[ "$f" == */helm/*.yaml         ]] || \
            [[ "$f" == */helm/*/*.yaml       ]]; then
            printf 'STALE: runtime-topology (Runtime Topology) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer1"
            STALE_SET[1]=1
        fi
    fi

    # Layer 2: Compile-time Dependencies
    if [[ -z "${STALE_SET[2]:-}" ]]; then
        if  [[ "$f" == go.mod              ]] || \
            [[ "$f" == */go.mod            ]] || \
            [[ "$f" == package.json        ]] || \
            [[ "$f" == */package.json      ]] || \
            [[ "$f" == *.csproj            ]] || \
            [[ "$f" == Cargo.toml          ]] || \
            [[ "$f" == */Cargo.toml        ]] || \
            [[ "$f" == requirements*.txt   ]] || \
            [[ "$f" == */requirements*.txt ]] || \
            [[ "$f" == pyproject.toml      ]] || \
            [[ "$f" == */pyproject.toml    ]]; then
            printf 'STALE: compile-deps (Compile-time Dependencies) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer2"
            STALE_SET[2]=1
        fi
    fi

    # Layer 3: API Contracts (HTTP routes, gRPC, GraphQL, OpenAPI)
    if [[ -z "${STALE_SET[3]:-}" ]]; then
        if  [[ "$f" == *route*.ts      ]] || \
            [[ "$f" == *route*.go      ]] || \
            [[ "$f" == *controller*.go ]] || \
            [[ "$f" == *controller*.ts ]] || \
            [[ "$f" == *controller*.cs ]] || \
            [[ "$f" == *views*.py      ]] || \
            [[ "$f" == *router*.ts     ]] || \
            [[ "$f" == *router*.go     ]] || \
            [[ "$f" == *handler*.go    ]] || \
            [[ "$f" == *.proto         ]] || \
            [[ "$f" == *.graphql       ]] || \
            [[ "$f" == *.gql           ]] || \
            [[ "$f" == *openapi*.yaml  ]] || \
            [[ "$f" == *openapi*.json  ]] || \
            [[ "$f" == *swagger*.yaml  ]] || \
            [[ "$f" == *swagger*.json  ]]; then
            printf 'STALE: api-contracts (API Contracts) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer3"
            STALE_SET[3]=1
        fi
    fi

    # Layer 4: Data Flows
    if [[ -z "${STALE_SET[4]:-}" ]]; then
        if  [[ "$f" == *dto*.ts      ]] || \
            [[ "$f" == *schema*.py   ]] || \
            [[ "$f" == *_request.go  ]] || \
            [[ "$f" == *_response.go ]] || \
            [[ "$f" == *types*.ts    ]] || \
            [[ "$f" == *model*.go    ]]; then
            printf 'STALE: data-flow (Data Flow) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer4"
            STALE_SET[4]=1
        fi
    fi

    # Layer 5: User Journey Scenarios
    if [[ -z "${STALE_SET[5]:-}" ]]; then
        if  [[ "$f" == *page*.tsx  ]] || \
            [[ "$f" == *page*.ts   ]] || \
            [[ "$f" == cmd/*.go    ]] || \
            [[ "$f" == */cmd/*.go  ]] || \
            [[ "$f" == cli/*.py    ]] || \
            [[ "$f" == */cli/*.py  ]]; then
            printf 'STALE: user-journeys (User Journeys) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer5"
            STALE_SET[5]=1
        fi
    fi

    # Layer 6: Exhaustive Inventory (service-level README changes, not root README)
    if [[ -z "${STALE_SET[6]:-}" ]]; then
        if  [[ "$f" == .env.example         ]] || \
            [[ "$f" == */.env.example       ]] || \
            [[ "$f" == services/*/README.md ]] || \
            [[ "$f" == apps/*/README.md     ]]; then
            printf 'STALE: inventory (Exhaustive Inventory) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer6"
            STALE_SET[6]=1
        fi
    fi

    # Layer 7: Service Component Architecture (internal module changes)
    if [[ -z "${STALE_SET[7]:-}" ]]; then
        if  [[ "$f" == services/*/*.go     ]] || \
            [[ "$f" == services/*/*.ts     ]] || \
            [[ "$f" == services/*/*.py     ]] || \
            [[ "$f" == services/*/*.rs     ]] || \
            [[ "$f" == services/*/*.cs     ]] || \
            [[ "$f" == apps/*/*.go         ]] || \
            [[ "$f" == apps/*/*.ts         ]] || \
            [[ "$f" == src/*/__init__.py   ]] || \
            [[ "$f" == */mod.rs            ]]; then
            printf 'STALE: service-components (Service Components) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer7"
            STALE_SET[7]=1
        fi
    fi

    # Layer 8: AST+LSP Symbol Bindings (any source file change affects cross-file refs)
    if [[ -z "${STALE_SET[8]:-}" ]]; then
        if  [[ "$f" == *.go  ]] || \
            [[ "$f" == *.ts  ]] || \
            [[ "$f" == *.py  ]] || \
            [[ "$f" == *.rs  ]] || \
            [[ "$f" == *.cs  ]] || \
            [[ "$f" == *.js  ]] || \
            [[ "$f" == *.java ]]; then
            printf 'STALE: ast-lsp-bindings (AST+LSP Bindings) — triggered by: %q\n' "${f}"
            echo "  Rebuild: /code-atlas rebuild   # or: code-atlas rebuild layer8"
            STALE_SET[8]=1
        fi
    fi

    # Short-circuit: all 8 layers stale — no further files need scanning
    [[ ${#STALE_SET[@]} -eq 8 ]] && break

done <<< "$CHANGED_FILES"

# ---------------------------------------------------------------------------
# Reconciliation — check if stale layers were rebuilt in the same diff
#
# A layer is considered rebuilt if docs/atlas/{slug}/ files appear in the
# changed file list.  This lets PRs that update both source code and atlas
# diagrams pass the staleness check.
# ---------------------------------------------------------------------------
declare -A LAYER_SLUG_MAP=(
    [1]="runtime-topology"
    [2]="compile-deps"
    [3]="api-contracts"
    [4]="data-flow"
    [5]="user-journeys"
    [6]="inventory"
    [7]="service-components"
    [8]="ast-lsp-bindings"
)

for layer_num in "${!STALE_SET[@]}"; do
    slug="${LAYER_SLUG_MAP[$layer_num]:-}"
    [[ -z "$slug" ]] && continue

    # Check if any docs/atlas/{slug}/ file was updated in the same diff
    if echo "$CHANGED_FILES" | grep -q "^docs/atlas/${slug}/"; then
        printf 'REBUILT: %s — atlas files updated in this PR\n' "$slug"
        unset "STALE_SET[$layer_num]"
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [[ ${#STALE_SET[@]} -eq 0 ]]; then
    echo "Atlas is fresh. No stale layers detected."
    exit 0
else
    # Collect sorted stale layer numbers without spawning a subprocess
    STALE_SORTED=()
    for _k in 1 2 3 4 5 6 7 8; do
        [[ -n "${STALE_SET[$_k]:-}" ]] && STALE_SORTED+=("$_k")
    done
    echo ""
    echo "Summary: ${#STALE_SORTED[@]} layer(s) stale: [${STALE_SORTED[*]}]"
    echo "Run '/code-atlas rebuild all' to refresh the full atlas."
    exit 1
fi
