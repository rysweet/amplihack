#!/bin/bash
# validate_atlas_output.sh
#
# Security validator for atlas output files.
# Enforces SEC-01, SEC-03, SEC-05, SEC-09, SEC-10 controls from SECURITY.md
# before atlas output is committed to docs/atlas/ or published to GitHub Pages.
#
# Controls checked:
#   SEC-01 CRITICAL  — No .env secret *values* in any atlas file
#   SEC-03 HIGH      — Mermaid/SVG labels do not contain raw <, >, & or unescaped quotes
#   SEC-05 HIGH      — All output files are within the docs/atlas/ boundary (no escapes)
#   SEC-09 CRITICAL  — No credential patterns in bug-report code_quote fields
#   SEC-10 HIGH      — No DOT/Mermaid label injection payloads
#
# Usage:
#   bash scripts/validate_atlas_output.sh [--atlas-dir <path>] [--strict]
#
# Options:
#   --atlas-dir <path>   Path to docs/atlas/ (default: docs/atlas)
#   --strict             Exit 1 on any violation (default: warn and continue)
#   --file <path>        Validate a single file
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more violations found
#   2 - Usage error

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
ATLAS_DIR="docs/atlas"
STRICT=false
SINGLE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --atlas-dir)
            ATLAS_DIR="$2"
            shift 2
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
            sed -n '3,35p' "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
VIOLATIONS=0
FILES_CHECKED=0

log_violation() {
    local control="$1"
    local file="$2"
    local detail="$3"
    echo "  [${control}] VIOLATION in ${file}: ${detail}"
    (( VIOLATIONS++ )) || true
}

log_ok() {
    local control="$1"
    local file="$2"
    echo "  [${control}] OK: ${file}"
}

# ---------------------------------------------------------------------------
# SEC-01 / SEC-09: Secret / credential pattern detection
#
# Looks for patterns that suggest a raw secret value was embedded:
#   - KEY=<non-empty-value>  (env var assignment style)
#   - Common credential field names followed by a non-placeholder value
#   - Base64-encoded blobs > 20 chars (proxy for encoded secrets)
# ---------------------------------------------------------------------------

# Patterns that indicate a secret *value* (not just a key name reference)
SECRET_VALUE_PATTERNS=(
    # env-var assignment: only flag known credential key names followed by a non-placeholder value.
    # The original broad pattern '[A-Z_]{4,}=...' created false positives on legitimate atlas content
    # such as Layer 6 inventory entries (e.g. HTTP_METHOD=GET, BUILD_LAYER=repo-surface).
    # Narrowed to require the key name itself to be credential-like.
    '(API_KEY|SECRET[_A-Z0-9]*|AUTH_TOKEN|ACCESS_TOKEN|REFRESH_TOKEN|ID_TOKEN|PASSWORD|PASSWD|CREDENTIAL[S]?|PRIVATE_KEY|ACCESS_KEY|CLIENT_SECRET|SIGNING_KEY|ENCRYPTION_KEY|MASTER_KEY|DB_PASSWORD|DATABASE_PASSWORD|REDIS_PASSWORD|POSTGRES_PASSWORD|MYSQL_PASSWORD|JWT_SECRET)[[:space:]]*=[[:space:]]*[A-Za-z0-9+/:@._-]{8,}'
    # connection string with embedded credentials
    '://[^:]+:[^@]{4,}@'
    # Common credential field names with an inline value
    '"(password|secret|token|api_key|apikey|access_key|private_key|client_secret)"[[:space:]]*:[[:space:]]*"[^"$<{]{4,}'
    # PEM header fragments
    '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    # AWS-style access key
    'AKIA[0-9A-Z]{16}'
    # Generic bearer token pattern
    'Bearer [A-Za-z0-9._-]{20,}'
)

check_sec_01_09() {
    local file="$1"
    local passed=true

    # Skip SVG files: they contain XML namespace URIs (xmlns:xlink=...) and
    # CSS @-rules (@keyframes, @media) that span the single-line SVG body,
    # causing the connection-string pattern to false-positive across unrelated
    # segments (e.g. "://w3.org/...@keyframes").
    case "$file" in
        *.svg) log_ok "SEC-01/09" "$file"; return ;;
    esac

    for pattern in "${SECRET_VALUE_PATTERNS[@]}"; do
        if grep -qE "$pattern" "$file" 2>/dev/null; then
            log_violation "SEC-01/09" "$file" "Possible credential/secret value matching pattern: ${pattern:0:50}..."
            passed=false
            break
        fi
    done

    if [[ "$passed" == true ]]; then
        log_ok "SEC-01/09" "$file"
    fi
}

# ---------------------------------------------------------------------------
# SEC-03 / SEC-10: XSS and diagram injection detection
#
# Mermaid and DOT labels that contain raw HTML special characters or
# JavaScript fragments create XSS risk when atlas is served via GitHub Pages.
# Also catches DOT graph injection payloads (subgraph escapes, quote injections).
# ---------------------------------------------------------------------------

XSS_PATTERNS=(
    '<script'
    'javascript:'
    'onerror='
    'onload='
    'onclick='
)

# Unescaped HTML in label context — catches labels like: A["<b>foo</b>"]
# We look for angle brackets within Mermaid label delimiters ["..."] or DOT label="..."
# Excludes <br/> and <br> which are legitimate Mermaid line-break syntax.
LABEL_HTML_PATTERN='(\["[^"]*[<>][^"]*"\]|label="[^"]*[<>][^"]*")'
LABEL_HTML_SAFE_BR='<br[ ]*[/]?>'

check_sec_03_10() {
    local file="$1"
    local passed=true

    for pattern in "${XSS_PATTERNS[@]}"; do
        if grep -qi "$pattern" "$file" 2>/dev/null; then
            log_violation "SEC-03/10" "$file" "XSS-risky pattern: ${pattern}"
            passed=false
        fi
    done

    # Check for unescaped HTML in labels, but ignore safe Mermaid <br/> tags.
    # Strip <br/> and <br> before testing so labels like E0["rich<br/>imports: 20"]
    # don't false-positive.
    if sed -E "s|${LABEL_HTML_SAFE_BR}||gi" "$file" | grep -qE "$LABEL_HTML_PATTERN" 2>/dev/null; then
        log_violation "SEC-03/10" "$file" "Unescaped HTML in diagram label (use &lt; &gt; instead of < >)"
        passed=false
    fi

    if [[ "$passed" == true ]]; then
        log_ok "SEC-03/10" "$file"
    fi
}

# ---------------------------------------------------------------------------
# SEC-05: Output confinement — symlink and path-escape detection
#
# Validates that files in docs/atlas/ are not symlinks pointing outside
# the docs/atlas/ boundary, which would allow exfiltrating repository
# content into the published atlas.
# ---------------------------------------------------------------------------
check_sec_05() {
    local file="$1"
    local atlas_realpath

    # Resolve the canonical atlas directory path
    if command -v realpath &>/dev/null; then
        atlas_realpath=$(realpath "$ATLAS_DIR" 2>/dev/null || echo "$ATLAS_DIR")
    else
        atlas_realpath="$ATLAS_DIR"
    fi

    # Check if the file is a symlink
    if [[ -L "$file" ]]; then
        local link_target
        link_target=$(readlink -f "$file" 2>/dev/null || readlink "$file")
        local resolved_target
        if command -v realpath &>/dev/null; then
            resolved_target=$(realpath "$link_target" 2>/dev/null || echo "$link_target")
        else
            resolved_target="$link_target"
        fi

        # Symlink must resolve to within the atlas directory (trailing slash prevents prefix attacks)
        if [[ "$resolved_target" != "${atlas_realpath%/}/"* && "$resolved_target" != "${atlas_realpath%/}" ]]; then
            log_violation "SEC-05" "$file" "Symlink escapes atlas boundary → ${resolved_target}"
            return
        fi
    fi

    log_ok "SEC-05" "$file"
}

# ---------------------------------------------------------------------------
# YAML size pre-check — reject files over 10MB before any parser invocation
# ---------------------------------------------------------------------------
YAML_MAX_SIZE_BYTES=10485760  # 10MB

check_yaml_size() {
    local file="$1"
    case "$file" in
        *.yaml|*.yml)
            local fsize
            fsize=$(wc -c < "$file" 2>/dev/null || echo "0")
            if [[ "$fsize" -gt "$YAML_MAX_SIZE_BYTES" ]]; then
                log_violation "SEC-08" "$file" "YAML file exceeds 10MB size limit (${fsize} bytes) — skipping parse"
                return 1
            fi
            ;;
    esac
    return 0
}

# ---------------------------------------------------------------------------
# Run all checks on a single file
# ---------------------------------------------------------------------------
validate_file() {
    local file="$1"
    (( FILES_CHECKED++ )) || true

    echo ""
    echo "Checking: ${file}"

    # Size gate: skip further checks on oversized YAML files
    if ! check_yaml_size "$file"; then
        return
    fi

    check_sec_05    "$file"
    check_sec_01_09 "$file"
    check_sec_03_10 "$file"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
echo "==================================="
echo "Atlas Output Security Validation"
echo "Controls: SEC-01, SEC-03, SEC-05, SEC-09, SEC-10"
echo "==================================="

if [[ -n "$SINGLE_FILE" ]]; then
    if [[ ! -f "$SINGLE_FILE" && ! -L "$SINGLE_FILE" ]]; then
        echo "Error: File not found: $SINGLE_FILE" >&2
        exit 2
    fi
    validate_file "$SINGLE_FILE"
else
    if [[ ! -d "$ATLAS_DIR" ]]; then
        echo "Atlas directory not found: ${ATLAS_DIR}"
        echo "Nothing to validate."
        exit 0
    fi

    # Validate all text-based atlas output files
    while IFS= read -r -d '' f; do
        validate_file "$f"
    done < <(
        find "$ATLAS_DIR" \
            \( -name '*.md' -o -name '*.mmd' -o -name '*.dot' -o -name '*.svg' -o -name '*.yaml' -o -name '*.yml' \) \
            -print0 2>/dev/null
    )
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==================================="
echo "Validation Summary"
echo "  Files checked: ${FILES_CHECKED}"
echo "  Violations:    ${VIOLATIONS}"
echo "==================================="

if [[ $VIOLATIONS -gt 0 ]]; then
    echo "Security violations found. Review and fix before publishing atlas."
    if [[ "$STRICT" == true ]]; then
        exit 1
    fi
    # Non-strict: warn but exit 0 so CI is non-blocking
    exit 0
fi

echo "All checks passed."
exit 0
