# Go Module Supply Chain — Dimension 11

## Lock Files and Build Integrity

**High**: `go.sum` not committed or out of sync with `go.mod`.
**High**: `go get` in CI pipeline — mutates `go.mod` and `go.sum`.
Fix: use `go install pkg@version` for tool installation; use `go build ./...` for builds.
**High**: `GONOSUMCHECK` or `GONOSUMDB` environment variables set in CI — disables
checksum verification for matching modules.
**Medium**: `GOFLAGS` does not include `-mod=readonly` or `-mod=vendor` in CI.

## Module Proxy and Verification

**High**: `GONOSUMCHECK=*` — disables all Go checksum verification.
**Medium**: `GOPROXY` does not include `sum.golang.org` — bypasses checksum database.
Compliant: `GOPROXY=https://proxy.golang.org,direct` (includes sum verification).
**High**: `replace` directive in `go.mod` pointing to a local path or unversioned git repo:

```
replace github.com/some/dep => ../local/dep
replace github.com/some/dep => github.com/fork/dep v0.0.0-unpinned
```

Flag `replace` directives that use local filesystem paths (unsafe in CI).

## Module Verification Commands

When auditing, check if these are set in CI environment or workflow files:

```bash
# Check for sum database bypass
grep -r "GONOSUMCHECK\|GONOSUMDB\|GONOSUMCHECK" .github/workflows/

# Verify go.sum is not in .gitignore
grep go.sum .gitignore

# Check for go get in workflows
grep "go get" .github/workflows/
```
