# Node.js / npm Supply Chain — Dimension 10

## Lock Files and Install Integrity

**Critical**: `npm install` used in CI instead of `npm ci` — `npm install` mutates lockfile.
**High**: `npx <package>` in CI — downloads and executes package without pinning.
Fix: install explicitly with exact version first, then run.
**High**: `yarn install` without `--frozen-lockfile` or `npm install` without `--frozen-lockfile`.
**Medium**: no lock file committed (`package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`).

`postinstall` / `preinstall` / `install` scripts in `package.json` dependencies:
**High**: direct dependency with lifecycle script — arbitrary code execution on install.
Check `node_modules/<pkg>/package.json` for `scripts.postinstall` in critical dependencies.

## Registry Verification

**High**: `.npmrc` or `npm install --registry <url>` using non-default registry without
verification policy.
**Medium**: scoped packages (`@myorg/pkg`) resolved from public npm registry rather than
private registry — potential dependency confusion.

Compliant private registry `.npmrc`:

```
@myorg:registry=https://pkgs.dev.azure.com/org/_packaging/feed/npm/registry/
//pkgs.dev.azure.com/org/_packaging/feed/npm/registry/:always-auth=true
```

## Dependency Health

**Medium**: `overrides` in `package.json` silently replacing transitive dependencies
(can mask security patches in transitive deps).
**Info**: devDependency in `dependencies` (bloats production bundle; minor concern).
