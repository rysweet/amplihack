---
type: howto
skill: code-atlas
updated: 2026-03-16
---

# How to Configure Staleness Triggers

Staleness triggers define which file changes make each atlas layer outdated. The default triggers cover standard Go, TypeScript, Python, .NET, and Rust patterns. This guide explains how to customize them.

---

## Where triggers are defined

Two places (they must stay in sync):

1. `scripts/check-atlas-staleness.sh` — the shell patterns used in CI
2. `docs/atlas/staleness-map.yaml` — the canonical YAML map consumed by CI `paths:` filters

The YAML is the single source of truth. If you add a pattern, update both files.

---

## Default trigger table

| File Pattern                                                                                                  | Layer | Why                      |
| ------------------------------------------------------------------------------------------------------------- | ----- | ------------------------ |
| `docker-compose*.yml`, `k8s/**/*.yaml`, `kubernetes/**/*.yaml`, `helm/**/*.yaml`                              | 1     | Service topology changes |
| `go.mod`, `package.json`, `*.csproj`, `Cargo.toml`, `requirements*.txt`, `pyproject.toml`                     | 2     | Dependency changes       |
| `*route*.ts`, `*route*.go`, `*controller*.go`, `*controller*.ts`, `*views*.py`, `*router*.ts`, `*handler*.go` | 3     | HTTP routing changes     |
| `*dto*.ts`, `*schema*.py`, `*_request.go`, `*_response.go`, `*types*.ts`, `*model*.go`                        | 4     | Data shape changes       |
| `*page*.tsx`, `*page*.ts`, `cmd/**/*.go`, `cli/**/*.py`                                                       | 5     | User-facing entry points |
| `.env.example`, `services/*/README.md`, `apps/*/README.md`                                                    | 6     | Inventory changes        |

---

## Add a trigger for a non-standard framework

**Example:** Your project uses Django views in `views/` (not `*views*.py`):

1. Edit `scripts/check-atlas-staleness.sh`, find the `case 3)` block, add:

```bash
[[ "$f" == views/*.py ]] && matched=true
[[ "$f" == */views/*.py ]] && matched=true
```

2. Edit `docs/atlas/staleness-map.yaml`, find the Layer 3 glob and add:

```yaml
- glob: "views/**/*.py"
  layers_affected: [3]
  rebuild_command: "/code-atlas layers=3"
```

3. Run the staleness test to verify:

```bash
bash .claude/skills/code-atlas/tests/test_staleness_triggers.sh
```

---

## Scope triggers to a monorepo service

If you only want to track changes in `services/billing/`:

```yaml
- glob: "services/billing/**/*.go"
  layers_affected: [2, 3, 4]
  rebuild_command: "/code-atlas codebase_path=services/billing layers=2,3,4"
```

---

## Exclude files from triggering

Files that match a trigger but shouldn't cause rebuilds (e.g., generated files, test fixtures):

In `check-atlas-staleness.sh`, add an exclusion check before `matched=true`:

```bash
# Exclude generated files from Layer 3 detection
[[ "$f" == *_generated.go ]] && continue
[[ "$f" == */.gen/* ]] && continue
```

---

## Verify trigger changes with dry run

```bash
# Simulate a file change and check what would trigger
git stash
echo "test" > services/api/new_handler.go
git add .
bash scripts/check-atlas-staleness.sh
git stash pop
```

Expected output should include `Layer 3 STALE`.

---

## Common pitfalls

**Adding patterns to only one file**
If you update `check-atlas-staleness.sh` but not `staleness-map.yaml`, the CI `paths:` filter won't match and the workflow won't run. Always update both.

**Overly broad patterns**
Pattern `*.go` would trigger Layer 3 on every Go file change (including tests, utilities, etc.). Use specific naming patterns (`*handler*.go`, `*route*.go`) that reflect actual routing files.

**Missing new framework conventions**
If your team adopts a new router (e.g., Huma for Go), add its file patterns before the first PR that uses it. Otherwise staleness will go undetected.
