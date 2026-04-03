# Code Atlas — Security Controls

**Version:** 1.1.0
**Classification:** Required reading before implementing any layer that writes to `docs/atlas/`

This document defines the security controls that every implementation contributing to the code atlas MUST enforce. Controls are numbered SEC-NN. CRITICAL and HIGH controls are not optional.

---

## Control Summary

| Control | Severity | Area                                              | Status   |
| ------- | -------- | ------------------------------------------------- | -------- |
| SEC-01  | CRITICAL | Secret redaction — env var values                 | Required |
| SEC-02  | CRITICAL | Path traversal prevention                         | Required |
| SEC-03  | HIGH     | XSS prevention — label sanitization               | Required |
| SEC-04  | HIGH     | Safe config/manifest parsing                      | Required |
| SEC-05  | HIGH     | Output confinement to `docs/atlas/`               | Required |
| SEC-06  | HIGH     | Shell injection prevention                        | Required |
| SEC-07  | MEDIUM   | Symlink attack prevention                         | Required |
| SEC-08  | MEDIUM   | Large file DoS prevention                         | Required |
| SEC-09  | CRITICAL | Credential redaction in bug reports + L8 output   | Required |
| SEC-10  | HIGH     | DOT/Mermaid injection prevention (+ experiments/) | Required |
| SEC-11  | HIGH     | Layer 7 service name sanitization                 | Required |
| SEC-12  | HIGH     | Layer 8 LSP output sanitization                   | Required |
| SEC-13  | HIGH     | Density threshold parameter validation            | Required |
| SEC-14  | MEDIUM   | Density prompt — accept only valid choices        | Required |
| SEC-15  | CRITICAL | Credential redaction in all Layer 8 outputs       | Required |
| SEC-16  | MEDIUM   | Relative-path enforcement in evidence fields      | Required |
| SEC-17  | HIGH     | Recipe YAML parameter injection prevention        | Required |
| SEC-18  | LOW      | Experiment filename date/layer validation         | Required |
| SEC-19  | HIGH     | Git push output credential sanitization           | Required |

---

## CRITICAL Controls

### SEC-01: Secret Value Redaction (CRITICAL)

**Rule:** When reading `.env`, `.env.*`, `docker-compose.yml`, Kubernetes Secrets, or any config file containing key=value pairs, extract **key names only**. Never write values to `docs/atlas/`.

**Required output format:**

```
DATABASE_URL=***REDACTED***
JWT_SECRET=***REDACTED***
REDIS_URL=***REDACTED***
```

**Implementation pattern:**

```bash
# Safe: extract key names only
grep "^[A-Z_]" .env.example | cut -d= -f1

# Safe: show key=REDACTED pairs
grep "^[A-Z_]" .env | sed 's/=.*/=***REDACTED***/'

# UNSAFE — never do this:
cat .env                          # exposes values
grep "DATABASE_URL" .env          # exposes connection string with password
```

**Scope:** Layer 6b (env var inventory), Layer 1 discovery (Docker Compose env: blocks), Pass 1 orphan detection, all bug report evidence fields. **Scope extended in v1.1.0**: also covers all Layer 8 output files (`symbol-references.mmd`, `dead-code.md`, `mismatched-interfaces.md`, `README.md`) and all Pass 3 per-journey verdict blocks (SEC-09 extension).

---

### SEC-02: Path Traversal Prevention (CRITICAL)

**Rule:** All file reads must stay within `codebase_path`. Use `realpath()` to resolve the canonical path and assert it starts with `codebase_path` before reading.

**Implementation pattern:**

```python
import os

def safe_read(codebase_path: str, relative_path: str) -> str:
    """Read a file, asserting it stays within codebase_path."""
    canonical = os.path.realpath(os.path.join(codebase_path, relative_path))
    if not canonical.startswith(os.path.realpath(codebase_path)):
        raise SecurityError(f"Path traversal detected: {relative_path}")
    with open(canonical) as f:
        return f.read()
```

```bash
# Safe: validate path before reading
canonical=$(realpath "$CODEBASE_PATH/$RELATIVE_FILE")
if [[ "$canonical" != "$CODEBASE_PATH"* ]]; then
    echo "Error: path traversal detected" >&2
    exit 1
fi
```

**Triggers:** Any file discovery using find, glob, or user-provided paths.

---

### SEC-09: Credential Redaction in Bug Reports (CRITICAL)

**Rule:** Before writing any code quote to a bug report's `evidence[].content` field, scan the content for credential patterns. Replace matched values with `***REDACTED***`.

**Credential patterns to redact:**

```
password\s*=\s*\S+
passwd\s*=\s*\S+
secret\s*=\s*\S+
token\s*=\s*\S+
api_key\s*=\s*\S+
apikey\s*=\s*\S+
private_key\s*=\s*\S+
-----BEGIN.*PRIVATE KEY-----
[A-Za-z0-9+/]{40,}={0,2}   # base64 blobs (API tokens)
```

**Implementation pattern:**

```python
import re

CREDENTIAL_PATTERNS = [
    (r'(?i)(password|passwd|secret|token|api_key|apikey|private_key)\s*=\s*\S+',
     r'\1=***REDACTED***'),
    (r'-----BEGIN.*?PRIVATE KEY-----.*?-----END.*?PRIVATE KEY-----',
     '***REDACTED PRIVATE KEY***'),
]

def redact_credentials(content: str) -> str:
    for pattern, replacement in CREDENTIAL_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content
```

---

## HIGH Controls

### SEC-03: Label Sanitization — XSS Prevention (HIGH)

**Rule:** All user-derived strings written into Mermaid, DOT, or SVG output must have HTML special characters escaped before rendering.

**Required escaping:**

| Character | Escape   |
| --------- | -------- |
| `<`       | `&lt;`   |
| `>`       | `&gt;`   |
| `&`       | `&amp;`  |
| `"`       | `&quot;` |
| `'`       | `&#39;`  |

**Implementation pattern:**

```python
def sanitize_label(raw: str) -> str:
    """Escape HTML special characters in diagram labels."""
    return (raw
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;'))
```

**Scope:** All node labels, edge labels, subgraph titles, and inventory table cell values derived from source code identifiers, file paths, or route strings. Scope extended in v1.1.0 to include experiment docs under `docs/atlas/experiments/` (SEC-10 extension).

---

### SEC-04: Safe Manifest Parsing (HIGH)

**Rule:** Parse YAML and JSON using a safe parser with size limits. Never use `eval` or dynamic code execution to read config files.

**Safe patterns:**

```python
import yaml
import json

# Safe YAML (never use yaml.load without Loader)
with open("docker-compose.yml") as f:
    config = yaml.safe_load(f)

# Safe JSON
with open("package.json") as f:
    pkg = json.load(f)
```

```bash
# Safe: use yq or python for YAML parsing, not bash eval
yq e '.services | keys' docker-compose.yml
python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(list(d.get('services',{}).keys()))" < docker-compose.yml
```

**Anti-pattern:**

```bash
# UNSAFE — never source .env files
source .env                # executes arbitrary code
. .env.production          # same risk
eval $(cat .env)           # direct injection
```

---

### SEC-05: Output Confinement (HIGH)

**Rule:** All atlas output files must be written to `docs/atlas/` or a user-configured `output_dir`. Never write outside the output directory.

**Validation:**

```python
def safe_write(output_dir: str, relative_path: str, content: str) -> None:
    canonical = os.path.realpath(os.path.join(output_dir, relative_path))
    if not canonical.startswith(os.path.realpath(output_dir)):
        raise SecurityError(f"Output path escapes output_dir: {relative_path}")
    os.makedirs(os.path.dirname(canonical), exist_ok=True)
    with open(canonical, 'w') as f:
        f.write(content)
```

---

### SEC-06: Shell Injection Prevention (HIGH)

**Rule:** Never construct shell commands with unsanitized user input or file-derived strings. Use `subprocess` with argument arrays, never shell=True with string concatenation.

```python
# Safe
import subprocess
result = subprocess.run(
    ["dot", "-Tsvg", input_path, "-o", output_path],
    capture_output=True, timeout=30
)

# UNSAFE
os.system(f"dot -Tsvg {user_input} -o {output}")  # shell injection
subprocess.run(f"mmdc -i {path}", shell=True)       # shell injection
```

---

### SEC-10: DOT/Mermaid Injection Prevention (HIGH)

**Rule:** Code-derived strings inserted into DOT or Mermaid syntax must not allow diagram structure injection. Specifically:

- DOT labels: wrap in `"..."` and escape embedded `"` as `\"`
- Mermaid labels: wrap node labels in `["..."]` syntax; escape `[`, `]`, `(`, `)` in content
- Route strings (e.g. `/api/users/:id`): replace `:` with `﹕` (U+FE13) or wrap in quotes

**DOT safe label:**

```python
def dot_label(raw: str) -> str:
    return '"' + raw.replace('\\', '\\\\').replace('"', '\\"') + '"'
```

**Mermaid safe node:**

```python
def mermaid_node(node_id: str, label: str) -> str:
    safe = label.replace('[', '&#91;').replace(']', '&#93;')
    return f'{node_id}["{safe}"]'
```

---

## MEDIUM Controls

### SEC-07: Symlink Attack Prevention (MEDIUM)

**Rule:** When discovering files with find/glob, check that resolved paths are not symlinks pointing outside `codebase_path`.

```bash
# Safe: resolve and validate before reading
for f in $(find . -name "*.go" -not -type l); do
    # Process regular files only (-not -type l excludes symlinks)
    process "$f"
done
```

---

### SEC-08: Large File DoS Prevention (MEDIUM)

**Rule:** Skip files larger than 10MB during discovery. Log a `SkillError` with code `FILE_TOO_LARGE` and continue.

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def safe_read_bounded(path: str) -> str | None:
    stat = os.stat(path)
    if stat.st_size > MAX_FILE_SIZE:
        log_skill_error("FILE_TOO_LARGE", path, f"Skipped: {stat.st_size} bytes exceeds 10MB limit")
        return None
    with open(path) as f:
        return f.read()
```

---

---

## Controls Added in v1.1.0 (SEC-11 through SEC-19)

### SEC-11: Layer 7 Service Name Sanitization (HIGH)

**Rule:** Service names used as filenames in `docs/atlas/service-components/` must be sanitised to `[a-zA-Z0-9_-]{1,64}` before any filesystem path construction. Apply `realpath()` boundary check identical to SEC-02 to confirm output stays within `output_dir`.

**Implementation pattern:**

```python
import re
import os

SERVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

def safe_service_name(raw: str) -> str:
    """Sanitise a service name for use in filesystem paths."""
    # Replace unsafe chars with hyphens, truncate to 64
    sanitised = re.sub(r'[^a-zA-Z0-9_-]', '-', raw)[:64]
    if not SERVICE_NAME_PATTERN.match(sanitised):
        raise SecurityError(f"Service name cannot be sanitised: {raw!r}")
    return sanitised

def layer7_output_path(output_dir: str, service_name: str) -> str:
    safe_name = safe_service_name(service_name)
    path = os.path.join(output_dir, "service-components", f"{safe_name}.mmd")
    canonical = os.path.realpath(path)
    if not canonical.startswith(os.path.realpath(output_dir)):
        raise SecurityError(f"Path traversal detected for service: {service_name!r}")
    return canonical
```

**Anti-pattern:** Never use a raw service name (from docker-compose, k8s, or any file) directly in a path without this sanitisation.

---

### SEC-12: Layer 8 LSP Output Sanitization (HIGH)

**Rule:** All data returned by the `lsp-setup` skill (symbol names, file paths, type signatures, call contexts) is treated as untrusted input before embedding in any atlas file.

**Required steps:**

1. Validate JSON schema of `LSPSymbolReport` before accessing fields
2. Apply SEC-03 HTML-escaping to all symbol names and type strings written to `.mmd` files
3. Apply SEC-02 path boundary check to all `file` fields before using in evidence links
4. Apply SEC-09 credential pattern scan to all `context` (surrounding code) fields

```python
def sanitise_lsp_output(report: dict, codebase_path: str) -> dict:
    """Sanitise all LSP output fields before atlas embedding."""
    for symbol in report.get("symbols", []):
        symbol["name"] = sanitize_label(symbol["name"])       # SEC-03
        symbol["file"] = validate_relative_path(              # SEC-02
            symbol["file"], codebase_path)
        for ref in symbol.get("references", []):
            ref["context"] = redact_credentials(ref["context"])  # SEC-09
            ref["file"] = validate_relative_path(ref["file"], codebase_path)
    return report
```

---

### SEC-13: Density Threshold Parameter Validation (HIGH)

**Rule:** The `--density-threshold` override parameter must be validated as positive integers in range `1–10,000`. Reject values outside this range with a clear error message and halt the invocation.

**Rejected values:**

| Value                      | Reason                                              |
| -------------------------- | --------------------------------------------------- |
| `0`                        | Disables guard via spam; not a meaningful threshold |
| Negative numbers           | Invalid; makes no semantic sense                    |
| Non-integers               | Parameter type violation                            |
| `> 10,000`                 | Effectively disables guard for any real codebase    |
| `null`, `undefined`, empty | Reverts to defaults (no error)                      |

```python
def validate_density_threshold(nodes: any, edges: any) -> tuple[int, int]:
    for name, value in [("nodes", nodes), ("edges", edges)]:
        if not isinstance(value, int):
            raise ValueError(f"density-threshold {name} must be an integer, got: {value!r}")
        if not (1 <= value <= 10_000):
            raise ValueError(
                f"density-threshold {name}={value} out of valid range 1–10,000"
            )
    return int(nodes), int(edges)
```

---

### SEC-14: Density Prompt — Accept Only Valid Choices (MEDIUM)

**Rule:** The density prompt accepts only `'a'`, `'b'`, or `'c'` (case-insensitive, whitespace-stripped). Any other input must re-prompt. Never silently default or fall through to a hidden choice.

```python
VALID_DENSITY_CHOICES = {'a', 'b', 'c'}

def prompt_density_choice(node_count: int, edge_count: int) -> str:
    while True:
        raw = input(
            f"This diagram has {node_count} nodes and {edge_count} edges, "
            f"which may render poorly.\n"
            f"Please choose:\n"
            f"  (a) Full diagram anyway\n"
            f"  (b) Simplified/clustered diagram\n"
            f"  (c) Table representation\n"
            f"> "
        ).strip().lower()
        if raw in VALID_DENSITY_CHOICES:
            log_audit(f"density_choice={raw}")  # Log choice, not raw input
            return raw
        print(f"Invalid choice: {raw!r}. Please enter a, b, or c.")
        # Loop: re-prompt unconditionally
```

**Non-interactive context** (CI/batch): Default to `'b'`; log `SkillError` with `DENSITY_THRESHOLD_EXCEEDED`. Never default silently.

---

### SEC-15: Credential Redaction in All Layer 8 Outputs (CRITICAL)

**Rule:** The `CREDENTIAL_PATTERNS` regex from SEC-09 must be applied before writing each of the four Layer 8 output files. This is a mandatory step in the `SecureAtlasBuilder` pipeline for Layer 8.

**Files that require redaction:**

- `docs/atlas/ast-lsp-bindings/symbol-references.mmd`
- `docs/atlas/ast-lsp-bindings/dead-code.md`
- `docs/atlas/ast-lsp-bindings/mismatched-interfaces.md`
- `docs/atlas/ast-lsp-bindings/README.md`

**Caution:** The `CREDENTIAL_PATTERNS` for Layer 8 must use targeted `key=value` format patterns — not bare base64 scanning — to avoid false positives on legitimate symbol names that happen to be long alphanumeric strings.

```python
LAYER8_CREDENTIAL_PATTERNS = [
    # key=value patterns only (not bare base64, to avoid false positives on symbol names)
    (r'(?i)(password|passwd|secret|token|api_key|apikey|private_key)\s*=\s*\S+',
     r'\1=***REDACTED***'),
    (r'-----BEGIN.*?PRIVATE KEY-----.*?-----END.*?PRIVATE KEY-----',
     '***REDACTED PRIVATE KEY***'),
    (r'https?://[^@\s]+@',  # URLs with embedded credentials
     'https://***@'),
]
```

---

### SEC-16: Relative-Path Enforcement in Evidence Fields (MEDIUM)

**Rule:** All `file:line` evidence references in Pass 3 verdict blocks and in all bug reports must be relative to `codebase_path`. Absolute paths are rejected.

```python
import os

def validate_relative_path(path: str, codebase_path: str) -> str:
    """Ensure path is relative to codebase_path and stays within it."""
    if os.path.isabs(path):
        raise SecurityError(f"Absolute path in evidence: {path!r}. Must be relative.")
    canonical = os.path.realpath(os.path.join(codebase_path, path))
    if not canonical.startswith(os.path.realpath(codebase_path)):
        raise SecurityError(f"Path escapes codebase root: {path!r}")
    return os.path.relpath(canonical, os.path.realpath(codebase_path))
```

**Anti-pattern:** Never write `/home/user/project/src/orders.ts:47` in an evidence field. Write `src/orders.ts:47` instead.

---

### SEC-17: Recipe YAML Parameter Injection Prevention (HIGH)

**Rule:** Recipe YAML parameters (`codebase_path`, `output_dir`) must be passed as structured data to sub-skills — never interpolated into shell command strings. Use `yaml.safe_load()` for recipe loading. Validate `codebase_path` at recipe entry.

**Validation at recipe entry:**

```python
import yaml
import re

NULL_BYTE_PATTERN = re.compile(r'\x00')
SHELL_META_PATTERN = re.compile(r'[;&|`$><\\!]')

def validate_recipe_path(raw: str) -> str:
    """Validate a path parameter from recipe YAML."""
    if NULL_BYTE_PATTERN.search(raw):
        raise ValueError(f"Null byte in codebase_path: {raw!r}")
    if SHELL_META_PATTERN.search(raw):
        raise ValueError(f"Shell metacharacter in codebase_path: {raw!r}")
    return raw

# Safe recipe loading (never yaml.load())
with open("amplifier-bundle/recipes/code-atlas.yaml") as f:
    recipe = yaml.safe_load(f)

codebase_path = validate_recipe_path(recipe["parameters"]["codebase_path"])
```

---

### SEC-18: Experiment Filename Date/Layer Validation (LOW)

**Rule:** Experiment filenames under `docs/atlas/experiments/` use system date (`datetime.date.today().isoformat()`) and a validated layer ID from the allowlist `{1, 2, 3, 4, 5, 6, 7, 8}`. The layer ID must never come from raw user input without integer validation against this allowlist.

```python
import datetime

VALID_LAYER_IDS = frozenset({1, 2, 3, 4, 5, 6, 7, 8})

def experiment_filename(layer_id: any, renderer: str) -> str:
    if not isinstance(layer_id, int) or layer_id not in VALID_LAYER_IDS:
        raise ValueError(f"Layer ID must be in {VALID_LAYER_IDS}, got: {layer_id!r}")
    safe_renderer = re.sub(r'[^a-z-]', '', renderer.lower())[:20]
    date_str = datetime.date.today().isoformat()
    return f"{date_str}-{safe_renderer}-L{layer_id}.md"
```

---

### SEC-19: Git Push Output Credential Sanitization (HIGH)

**Rule:** Git push stdout and stderr must be sanitised with the `CREDENTIAL_URL_PATTERN` before any display or logging. Replace embedded credentials in URLs with `https://***@`.

```python
import re
import subprocess

CREDENTIAL_URL_PATTERN = re.compile(r'https?://[^@\s]+@')

def safe_git_push(remote: str, branch: str) -> None:
    result = subprocess.run(
        ["git", "push", remote, branch],
        capture_output=True, text=True
    )
    safe_stdout = CREDENTIAL_URL_PATTERN.sub('https://***@', result.stdout)
    safe_stderr = CREDENTIAL_URL_PATTERN.sub('https://***@', result.stderr)
    print(safe_stdout)
    if result.returncode != 0:
        raise RuntimeError(f"git push failed: {safe_stderr}")
```

---

## SecureAtlasBuilder Pipeline

All layer implementations MUST follow this pipeline order:

```
 1. Receive codebase_path (validated by SEC-02 at skill entry; SEC-17 if from recipe YAML)
 2. Discover files (SEC-07: skip symlinks; SEC-08: skip >10MB)
 3. Parse manifests/configs (SEC-04: safe parsers only)
 4. Extract key names for env vars (SEC-01: values never collected)
 5. Build node/edge data structures (plain Python objects — no shell)
 6. Sanitize all labels (SEC-03: escape HTML specials; SEC-11 for Layer 7 service names)
 7. Check density (ALL layers): if node_count > 50 OR edge_count > 100 → invoke density prompt
    a. Validate threshold override (SEC-13: integer range 1–10,000)
    b. Prompt user, accept only a/b/c (SEC-14: re-prompt on invalid input)
 8. Generate diagram syntax (SEC-10: injection-safe label wrapping)
 9. If Layer 8: sanitise all LSP output before embedding (SEC-12)
10. Write to output_dir (SEC-05: path confinement validated)
11. If Layer 8: apply LAYER8_CREDENTIAL_PATTERNS to all four output files (SEC-15)
12. If writing bug reports or Pass 3 verdicts:
    a. Redact credentials (SEC-09)
    b. Validate all evidence paths are relative (SEC-16: reject absolute paths)
13. If writing experiments/: validate layer ID from allowlist; use system date (SEC-18)
14. If git push: sanitise stdout/stderr with CREDENTIAL_URL_PATTERN (SEC-19)
```

---

## Per-Language Safe Parsing

| Source               | Safe Method                     | Unsafe — Never Use                         |
| -------------------- | ------------------------------- | ------------------------------------------ |
| `.env` files         | `grep "^[A-Z_]" \| cut -d= -f1` | `source .env`, `eval $(cat .env)`          |
| `docker-compose.yml` | `yaml.safe_load()`, `yq e`      | `yaml.load()`, bash eval                   |
| `package.json`       | `json.load()`, `jq`             | `eval`, `require()` with untrusted paths   |
| Go source            | Regex on file content           | `go run` with untrusted code               |
| `.csproj`            | `xml.etree.ElementTree.parse()` | `lxml` with `resolve_entities=True`        |
| Kubernetes Secrets   | Extract `metadata.name` only    | Never read `data:` or `stringData:` blocks |

---

## Security Checklist

Before any layer implementation is considered complete:

- [ ] SEC-01: Env var values are never written to any output file
- [ ] SEC-02: All file reads use `realpath()` boundary validation
- [ ] SEC-03: All diagram labels have HTML special characters escaped
- [ ] SEC-04: All YAML/JSON parsed with safe loaders (no eval, no source)
- [ ] SEC-05: All output files written inside `output_dir` with path validation
- [ ] SEC-06: No shell=True subprocess calls with variable interpolation
- [ ] SEC-07: Symlinks excluded from file discovery
- [ ] SEC-08: Files >10MB skipped with SkillError logged
- [ ] SEC-09: Bug report evidence fields (+ Layer 8 outputs + Pass 3 verdicts) scanned for credential patterns
- [ ] SEC-10: DOT/Mermaid label strings are injection-safe (includes experiments/ output)
- [ ] SEC-11: Layer 7 service names sanitised to `[a-zA-Z0-9_-]{1,64}` before path construction
- [ ] SEC-12: Layer 8 LSP output validated (schema + SEC-03 + SEC-02 + SEC-09 applied to all fields)
- [ ] SEC-13: `--density-threshold` values validated as integers in range 1–10,000
- [ ] SEC-14: Density prompt only accepts `a`, `b`, `c`; re-prompts on any other input
- [ ] SEC-15: LAYER8_CREDENTIAL_PATTERNS applied before writing all four Layer 8 output files
- [ ] SEC-16: All evidence `file:line` references use `os.path.relpath()` — no absolute paths
- [ ] SEC-17: Recipe YAML `codebase_path`/`output_dir` validated (no null bytes, no shell metacharacters)
- [ ] SEC-18: Experiment filenames use system date + allowlisted layer ID only
- [ ] SEC-19: Git push output sanitised with CREDENTIAL_URL_PATTERN before display or logging

---

_This document must be read before implementing Layer 1 (env discovery), Layer 3 (route extraction), Layer 6 (inventory tables), or the bug-hunting passes._
