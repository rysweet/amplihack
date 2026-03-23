# Python / PyPI Supply Chain — Dimension 8

## Lock Files and Install Integrity

**Critical**: `pip install` from git URL without SHA pin: `git+https://github.com/org/repo@main`
**High**: `pip install` in CI without `--require-hashes` and no lock file tool in use.
Lock file tools that satisfy this requirement: `pip-tools` (with hashes), `poetry.lock`,
`pdm.lock`, `uv.lock`.
**High**: `pip install -e .` (editable install) in CI — runs `setup.py` with full shell access.
**Medium**: `requirements.txt` lacks hash pinning and no alternative lock file exists.

Fix for hash pinning with pip-tools:

```
pip-compile --generate-hashes requirements.in -o requirements.txt
pip install --require-hashes -r requirements.txt
```

## Package Source Verification

**Critical**: `--extra-index-url` in CI install commands — PyPI is checked first, enabling
dependency confusion (attacker publishes higher version to PyPI for internal package name).
Fix: use `--index-url` (exclusive) instead, or configure `--no-index` with private mirror.
**High**: non-PyPI index URL in `pip.conf` or `pyproject.toml` `[tool.uv.sources]` without
hash pinning.

## Typosquatting

Flag packages with names within edit-distance 2 of known popular packages if they have:

- Very low download counts (< 1000/month)
- Recent first publish (< 30 days)
- Single maintainer

Common typosquatting targets: `requests`, `boto3`, `numpy`, `flask`, `django`, `fastapi`.
