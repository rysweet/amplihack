# Dimension 10: Node.js Supply Chain

---

## Check 1: npm ci vs npm install

### Detection

```bash
grep -rn "npm install\|yarn install\|pnpm install" .github/workflows/ Makefile Dockerfile 2>/dev/null
```

### Pattern

```yaml
# VIOLATION — npm install updates lock file, allows version drift
- run: npm install

# CORRECT — npm ci uses lock file exactly, fails if package-lock.json is missing
- run: npm ci

# CORRECT — yarn equivalent
- run: yarn install --frozen-lockfile

# CORRECT — pnpm equivalent
- run: pnpm install --frozen-lockfile
```

### Why It Matters

`npm install` will update `package-lock.json` if a package version has changed.
In CI, this silently installs a different version than what was tested locally.
`npm ci` fails if `package-lock.json` is out of sync — making the issue visible.

### Lock File Committed

```bash
# Check lock file exists and is not in .gitignore
ls package-lock.json yarn.lock pnpm-lock.yaml 2>/dev/null
grep -E "package-lock.json|yarn.lock|pnpm-lock.yaml" .gitignore 2>/dev/null
```

### Severity

| Finding                                           | Severity |
| ------------------------------------------------- | -------- |
| `npm install` in CI (no lock file enforcement)    | High     |
| Lock file present but in `.gitignore`             | High     |
| Lock file missing entirely                        | High     |
| `npm install` in Dockerfile (no lock enforcement) | High     |

---

## Check 2: npx Risk

`npx` downloads and executes packages on demand. Without a version pin or SHA,
it installs the latest published version — a supply chain risk.

### Detection

```bash
grep -rn "npx " .github/workflows/ Makefile scripts/ 2>/dev/null
```

### Pattern

```yaml
# VIOLATION — downloads latest version at runtime
- run: npx create-react-app my-app

# VIOLATION — no version pinning
- run: npx prettier --check .

# BETTER — pin version
- run: npx prettier@3.2.5 --check .

# BEST — install as dev dependency, use local binary
- run: npm ci && ./node_modules/.bin/prettier --check .

# BEST — package.json script
- run: npm run lint # delegates to local binary via scripts
```

### Severity

| Finding                                          | Severity |
| ------------------------------------------------ | -------- |
| `npx <package>` without version in production CI | High     |
| `npx <package>` without version in dev/test CI   | Medium   |

---

## Check 3: postinstall Scripts

`postinstall` scripts in `package.json` execute automatically on `npm install`.
Malicious packages abuse this to execute arbitrary code.

### Detection

```bash
# Check own package.json for postinstall scripts
python3 -c "
import json
with open('package.json') as f:
    pkg = json.load(f)
scripts = pkg.get('scripts', {})
for name in ['postinstall', 'install', 'preinstall', 'prepare']:
    if name in scripts:
        print(f'{name}: {scripts[name]}')
"

# Check dependencies for postinstall scripts (requires node_modules to be installed)
# Static analysis — check lock file for known risky patterns
grep -l "postinstall" node_modules/*/package.json 2>/dev/null | head -20
```

### Severity

| Finding                                                            | Severity                 |
| ------------------------------------------------------------------ | ------------------------ |
| Dependency with `postinstall` that curl/wget external URLs         | Critical                 |
| Own `postinstall` script fetching remote resources                 | High                     |
| `postinstall` in direct dependency that does not obviously need it | Medium (flag for review) |

---

## Check 4: package-lock.json Integrity

### Detect Suspicious Lock File Patterns

```bash
# Check for non-registry sources in package-lock.json
python3 -c "
import json
with open('package-lock.json') as f:
    lock = json.load(f)
packages = lock.get('packages', lock.get('dependencies', {}))
for name, info in packages.items():
    resolved = info.get('resolved', '')
    # Flag non-npm registry URLs
    if resolved and 'registry.npmjs.org' not in resolved and 'npmjs.com' not in resolved:
        if 'github.com' in resolved or 'gitlab.com' in resolved:
            print(f'GIT SOURCE: {name} -> {resolved}')
        elif resolved.startswith('http'):
            print(f'UNKNOWN SOURCE: {name} -> {resolved}')
" 2>/dev/null
```

### Severity

| Finding                                    | Severity               |
| ------------------------------------------ | ---------------------- |
| Package resolved from non-registry git URL | High (flag for review) |
| Package with `integrity` hash missing      | High                   |
| Package resolved from unknown HTTP URL     | Critical               |

---

## Check 5: npm audit

```bash
# Run audit
npm audit --json | python3 -c "
import sys, json
report = json.load(sys.stdin)
vulns = report.get('vulnerabilities', {})
for name, info in vulns.items():
    severity = info.get('severity', 'unknown')
    if severity in ('high', 'critical'):
        print(f'{severity.upper()}: {name}')
        for via in info.get('via', []):
            if isinstance(via, dict):
                print(f'  CVE: {via.get(\"url\", \"N/A\")}')
"

# Fail CI on high/critical
npm audit --audit-level=high
```

### CI Integration

```yaml
- name: Security audit
  run: npm audit --audit-level=high
```

---

## Verification Checklist (Node.js)

- [ ] CI uses `npm ci` (not `npm install`)
- [ ] `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` committed and not in `.gitignore`
- [ ] No unversioned `npx <package>` in CI scripts
- [ ] `npm audit --audit-level=high` fails CI on High/Critical CVEs
- [ ] Direct dependencies with `postinstall` scripts reviewed
- [ ] Lock file has no packages resolved from non-registry URLs
