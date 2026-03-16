# Code Atlas — Security Controls

**Version:** 1.0.0
**Classification:** Required reading before implementing any layer that writes to `docs/atlas/`

This document defines the security controls that every implementation contributing to the code atlas MUST enforce. Controls are numbered SEC-NN. CRITICAL and HIGH controls are not optional.

---

## Control Summary

| Control | Severity | Area | Status |
|---------|----------|------|--------|
| SEC-01 | CRITICAL | Secret redaction — env var values | Required |
| SEC-02 | CRITICAL | Path traversal prevention | Required |
| SEC-03 | HIGH | XSS prevention — label sanitization | Required |
| SEC-04 | HIGH | Safe config/manifest parsing | Required |
| SEC-05 | HIGH | Output confinement to `docs/atlas/` | Required |
| SEC-06 | HIGH | Shell injection prevention | Required |
| SEC-07 | MEDIUM | Symlink attack prevention | Required |
| SEC-08 | MEDIUM | Large file DoS prevention | Required |
| SEC-09 | CRITICAL | Credential redaction in bug reports | Required |
| SEC-10 | HIGH | DOT/Mermaid injection prevention | Required |

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

**Scope:** Layer 6b (env var inventory), Layer 1 discovery (Docker Compose env: blocks), Pass 1 orphan detection, all bug report evidence fields.

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

| Character | Escape |
|-----------|--------|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |
| `"` | `&quot;` |
| `'` | `&#39;` |

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

**Scope:** All node labels, edge labels, subgraph titles, and inventory table cell values derived from source code identifiers, file paths, or route strings.

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

## SecureAtlasBuilder Pipeline

All layer implementations MUST follow this pipeline order:

```
1. Receive codebase_path (validated by SEC-02 at skill entry)
2. Discover files (SEC-07: skip symlinks; SEC-08: skip >10MB)
3. Parse manifests/configs (SEC-04: safe parsers only)
4. Extract key names for env vars (SEC-01: values never collected)
5. Build node/edge data structures (plain Python objects — no shell)
6. Sanitize all labels (SEC-03: escape HTML specials)
7. Generate diagram syntax (SEC-10: injection-safe label wrapping)
8. Write to output_dir (SEC-05: path confinement validated)
9. If writing bug reports: redact credentials (SEC-09)
```

---

## Per-Language Safe Parsing

| Source | Safe Method | Unsafe — Never Use |
|--------|------------|-------------------|
| `.env` files | `grep "^[A-Z_]" \| cut -d= -f1` | `source .env`, `eval $(cat .env)` |
| `docker-compose.yml` | `yaml.safe_load()`, `yq e` | `yaml.load()`, bash eval |
| `package.json` | `json.load()`, `jq` | `eval`, `require()` with untrusted paths |
| Go source | Regex on file content | `go run` with untrusted code |
| `.csproj` | `xml.etree.ElementTree.parse()` | `lxml` with `resolve_entities=True` |
| Kubernetes Secrets | Extract `metadata.name` only | Never read `data:` or `stringData:` blocks |

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
- [ ] SEC-09: Bug report evidence fields scanned for credential patterns
- [ ] SEC-10: DOT/Mermaid label strings are injection-safe

---

*This document must be read before implementing Layer 1 (env discovery), Layer 3 (route extraction), Layer 6 (inventory tables), or the bug-hunting passes.*
