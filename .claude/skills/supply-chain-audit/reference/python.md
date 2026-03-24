# Dimension 8: Python Dependency Integrity

## Overview

Python supply chain attacks target `requirements.txt` files without hash pinning,
the `--extra-index-url` flag's resolution order, and typosquatted package names
that mimic popular packages.

---

## Check 1: Hash Pinning in requirements.txt

### Detection

```bash
# Check if requirements files have hash pinning
grep -c "sha256:" requirements*.txt requirements/**/*.txt 2>/dev/null
```

### Pattern

```
# VIOLATION — version-only pin, no hash verification
requests==2.31.0
numpy==1.26.4

# CORRECT — with hash pinning
requests==2.31.0 \
    --hash=sha256:58cd2187423d... \
    --hash=sha256:942c5a758f98...
numpy==1.26.4 \
    --hash=sha256:2a02aba9ed12...
```

### Generate Hash-Pinned Requirements

```bash
# pip-compile (pip-tools) — generates hash-pinned requirements from .in file
pip install pip-tools
pip-compile --generate-hashes requirements.in -o requirements.txt

# pip-compile for extras
pip-compile --generate-hashes --extra dev pyproject.toml -o requirements-dev.txt

# pip install with hashes (enforces hashes present)
pip install --require-hashes -r requirements.txt
```

### Severity

| Finding                                                       | Severity |
| ------------------------------------------------------------- | -------- |
| Production `requirements.txt` without any hashes              | High     |
| Development requirements without hashes                       | Medium   |
| `pip install` in CI without `--require-hashes`                | High     |
| `pip install` without `-r requirements.txt` (ad-hoc installs) | High     |

---

## Check 2: --extra-index-url Risk

### Detection

```bash
grep -rn "extra-index-url\|extra_index_url\|--index-url" \
    requirements*.txt setup.cfg pyproject.toml pip.conf .pip/ 2>/dev/null
```

### The Risk

When `--extra-index-url` is combined with `--index-url`, pip resolves by choosing
the **highest version** across all sources — not the first source. An attacker can
publish a package with a higher version to PyPI if your internal package name is
not reserved there.

```
# VIOLATION — dependency confusion risk
--extra-index-url https://my-internal-registry.example.com/simple/
requests==2.31.0      # fetched from PyPI (correct)
mycompany-auth==1.2.0  # intended from internal, but attacker could publish 1.2.1 on PyPI
```

### Mitigation

```
# CORRECT — use --index-url to make internal source primary, add PyPI as extra
--index-url https://my-internal-registry.example.com/simple/
--extra-index-url https://pypi.org/simple/

# Better — use hash pinning to prevent substitution
mycompany-auth==1.2.0 \
    --hash=sha256:abc123...   # hash prevents attacker version from being accepted
```

### Severity

| Finding                                                                | Severity |
| ---------------------------------------------------------------------- | -------- |
| `--extra-index-url` pointing to internal registry without hash pinning | High     |
| `--extra-index-url` with publicly-guessable internal package names     | Critical |

---

## Check 3: Typosquatting Detection

### Heuristic Signals (Static Analysis)

Without live PyPI data, use these signals to flag likely typosquats for manual review:

```python
# Packages with edit distance 1-2 from popular packages
# Common typosquatting patterns:
SUSPICIOUS_PATTERNS = [
    r"re-quests",      # requests
    r"reqeusts",       # requests
    r"pillow-pil",     # Pillow
    r"np-numpy",       # numpy
    r"panda-s",        # pandas
    r"scikit-learn2",  # scikit-learn
    r"boto-3",         # boto3
    r"crypto-graphy",  # cryptography
]
```

### Known Malicious Pattern Families

Flag packages matching these patterns for review:

- Name differs from popular package by 1-2 character substitution (e.g., `o` → `0`)
- Name adds/removes a hyphen or underscore vs. well-known package
- Name is `<package>-utils`, `<package>-tools`, `<package>-helper` variants of core packages
- Package was published within 7 days of a popular package's major release

**Note**: Typosquatting detection is heuristic-based without live PyPI download data.
Flag suspicious packages; do not assert they are malicious.

### Severity

| Finding                                                         | Severity               |
| --------------------------------------------------------------- | ---------------------- |
| Package name within edit-distance 1 of top-100 PyPI package     | High (flag for review) |
| Package with 0 stars and published in last 30 days in prod deps | Medium                 |

---

## Check 4: pyproject.toml and setup.cfg

### Detection

```bash
# Check for version specifiers without upper bounds in pyproject.toml
grep -E ">=|~=" pyproject.toml setup.cfg 2>/dev/null
```

### Pattern

```toml
# VIOLATION — no upper bound allows installing attacker-published future version
[project]
dependencies = [
    "requests>=2.0",    # will install any future version including attacker-published 99.0
]

# BETTER — pinned range
dependencies = [
    "requests>=2.31,<3.0",
]

# BEST (for deployed applications) — use requirements.txt with hash pinning
# pyproject.toml is for libraries; requirements.txt for deployed apps
```

### Severity

| Finding                                                          | Severity |
| ---------------------------------------------------------------- | -------- |
| Production app using `pyproject.toml` deps without lock file     | High     |
| Library using `>=` without upper bound on security-sensitive dep | Medium   |

---

## Verification Checklist (Python)

- [ ] `requirements.txt` uses `--hash=sha256:` for all packages
- [ ] CI uses `pip install --require-hashes -r requirements.txt`
- [ ] `--extra-index-url` (if present) is combined with hash pinning
- [ ] Internal package names are reserved on PyPI
- [ ] No obvious typosquats in dependency list
- [ ] `pip-tools` or equivalent generates lock files from `.in` source files
- [ ] `pip-compile --generate-hashes` in contributor documentation
