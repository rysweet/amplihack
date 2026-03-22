# Parity Scenario YAML Format

Declarative test scenarios for comparing two CLI implementations side-by-side.

## Structure

```yaml
cases:
  - name: "unique-test-name"          # Required: unique identifier
    category: "install"                # Optional: grouping for audit reports
    argv: ["subcommand", "--flag"]     # Required: CLI arguments (same for both engines)
    timeout: 30                        # Optional: seconds (default: 30)
    stdin: "y\n"                       # Optional: stdin data
    cwd: "subdir"                      # Optional: working directory relative to sandbox
    env:                               # Optional: extra environment variables
      MY_VAR: "value"
      PATH: "${SANDBOX_ROOT}/bin:${PATH}"  # Template variables supported
    setup: |                           # Optional: bash setup script run in both sandboxes
      mkdir -p bin
      cat > bin/stub <<'EOF'
      #!/usr/bin/env bash
      echo "stubbed"
      EOF
      chmod +x bin/stub
    compare:                           # Optional: what to compare (default: all three)
      - stdout                         # Compare stdout (JSON-semantic if both are valid JSON)
      - stderr                         # Compare stderr text
      - exit_code                      # Compare process exit codes
      - "fs:path/to/file"             # Compare file content/existence
      - "jsonfs:path/to/file.json"    # Compare JSON file (semantic, ignores key order)
```

## Template Variables

Available in `env` values and `setup` scripts:

| Variable | Expands To |
|----------|------------|
| `${SANDBOX_ROOT}` | Sandbox root directory |
| `${HOME}` | Sandbox home directory (`${SANDBOX_ROOT}/home`) |
| `${PATH}` | Parent process PATH |

## Comparison Modes

### `stdout` / `stderr`

1. Both outputs are normalized (sandbox paths replaced with `<SANDBOX>`)
2. If both parse as valid JSON, **semantic comparison** (ignores key ordering)
3. Otherwise, exact text comparison

### `exit_code`

Exact integer match.

### `fs:<relative-path>`

Compares file or directory at the relative path within each sandbox:
- Both missing → match
- One missing → divergence
- Both files → SHA-256 hash comparison
- Both directories → recursive hash comparison

### `jsonfs:<relative-path>`

Loads both files as JSON and compares semantically (ignores key ordering).

## Sandbox Isolation

Each engine (legacy and candidate) gets its own sandbox:

```
/tmp/parity-<run_id>-<engine>-<case>/
├── home/          # $HOME for the engine
├── tmp/           # $TMPDIR for the engine
└── <cwd>/         # Working directory (if specified)
```

Environment is isolated:
- `HOME`, `TMPDIR`, `TMP`, `TEMP` → sandbox paths
- `GIT_AUTHOR_*`, `GIT_COMMITTER_*` → shadow identity
- `PARITY_SHADOW_RUN=1` → flag for shadow-aware code
- `SANDBOX_ROOT` → sandbox root path

## Examples

### Minimal smoke test

```yaml
cases:
  - name: version-check
    argv: ["--version"]
    compare: ["exit_code"]
```

### Command with setup and filesystem comparison

```yaml
cases:
  - name: install-success
    argv: ["install", "--local", "${SANDBOX_ROOT}/repo"]
    env:
      PATH: "${SANDBOX_ROOT}/bin:${PATH}"
    setup: |
      mkdir -p bin repo/config
      echo '{"key": "value"}' > repo/config/settings.json
      cat > bin/helper <<'EOF'
      #!/usr/bin/env bash
      exit 0
      EOF
      chmod +x bin/helper
    compare:
      - exit_code
      - "fs:home/.config/myapp/settings.json"
      - "jsonfs:home/.config/myapp/manifest.json"
```

### Non-interactive launcher test

```yaml
cases:
  - name: launch-missing-binary
    argv: ["launch"]
    timeout: 10
    env:
      PATH: "${SANDBOX_ROOT}/bin:${PATH}"
      MY_APP_NONINTERACTIVE: "1"
    setup: |
      mkdir -p bin
      # No target binary — should fail fast
    compare:
      - exit_code
      - stderr
```

### Stub binary capturing args and env

```yaml
cases:
  - name: launch-captures-args
    argv: ["launch"]
    timeout: 15
    env:
      PATH: "${SANDBOX_ROOT}/bin:${PATH}"
    setup: |
      mkdir -p bin
      cat > bin/target-app <<'SCRIPT'
      #!/usr/bin/env bash
      printf '%s\n' "$@" > "$SANDBOX_ROOT/captured_args.txt"
      env | grep MY_APP_ | sort > "$SANDBOX_ROOT/captured_env.txt"
      exit 0
      SCRIPT
      chmod +x bin/target-app
    compare:
      - exit_code
      - "fs:captured_args.txt"
      - "fs:captured_env.txt"
```

## Best Practices

1. **Always set timeout** for tests that launch subprocesses
2. **Use NONINTERACTIVE env vars** for launcher tests to prevent hangs
3. **Use stub binaries** to capture args/env instead of running real apps
4. **Keep setup scripts idempotent** — they run identically in both sandboxes
5. **Prefer `jsonfs:` over `fs:`** for JSON files (ignores key ordering)
6. **Group tests by category** for meaningful audit reports
7. **Start with exit_code only**, add stdout/stderr/fs as you narrow gaps
