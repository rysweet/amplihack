# Dimensions 5 & 12: Container Supply Chain

## Dimension 5: Base Image Pinning

Container base images must be pinned by digest, not by tag.

### Pattern to Detect

```dockerfile
# VIOLATION — mutable tag
FROM python:3.12-slim

# VIOLATION — latest (most dangerous)
FROM ubuntu:latest

# CORRECT — digest-pinned with tag comment
FROM python:3.12-slim@sha256:a4c3b5d9e1f2a8c7b6d4e3f1a0b2c5d8e9f3a1b4c7d6e5f8a2b1c0d3e4f7a9b8  # 3.12.3-slim
```

### Digest Lookup

```bash
# Get current digest for an image
docker manifest inspect python:3.12-slim --verbose | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d[0]['Descriptor']['digest'])"

# Or via crane (preferred, no Docker daemon required)
crane digest python:3.12-slim

# Or via skopeo
skopeo inspect --format '{{.Digest}}' docker://python:3.12-slim
```

### Severity

| Finding                                  | Severity                           |
| ---------------------------------------- | ---------------------------------- |
| `FROM image:latest`                      | Critical                           |
| `FROM image:<semver-tag>` without digest | High                               |
| `FROM scratch`                           | Info (correct — no attack surface) |
| Digest present but tag comment missing   | Info                               |

### Multi-Stage Builds

For multi-stage builds, pin ALL stages including intermediate build stages:

```dockerfile
# Build stage — pin it too (supply chain risk in build tools)
FROM golang:1.22-alpine@sha256:<digest>  # 1.22.3-alpine3.19 AS builder

# Final stage — use minimal base
FROM gcr.io/distroless/static@sha256:<digest>  # latest-nonroot
```

---

## Dimension 12: Docker Build Chain Security

### Detection Commands

```bash
# Dim 12 — detect final stage running as root (no USER instruction before CMD/ENTRYPOINT)
grep -n "^USER\|^CMD\|^ENTRYPOINT\|^FROM" Dockerfile 2>/dev/null

# Dim 12 — count USER instructions; 0 means root execution
grep -c "^USER" Dockerfile 2>/dev/null || echo "0 — no USER instruction found"

# Dim 12 — detect RUN curl|bash pattern (any stage)
grep -n "curl.*|.*bash\|wget.*|.*sh\|curl.*sh" Dockerfile 2>/dev/null

# Dim 12 — detect ADD (allows remote URL expansion, use COPY instead)
grep -n "^ADD " Dockerfile 2>/dev/null
```

### Non-Root USER

Every production image must drop to a non-root user before the final `CMD`/`ENTRYPOINT`.

```dockerfile
# VIOLATION — runs as root
CMD ["./app"]

# CORRECT
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
CMD ["./app"]

# CORRECT — distroless nonroot variant handles this automatically
FROM gcr.io/distroless/static-debian12:nonroot@sha256:<digest>
```

### Minimal Final Stage

```dockerfile
# VIOLATION — shipping build tools to production
FROM golang:1.22@sha256:<digest> AS final
COPY . .
RUN go build -o /app .
CMD ["/app"]

# CORRECT — multi-stage, scratch or distroless final
FROM golang:1.22@sha256:<digest> AS builder
RUN go build -o /app ./cmd/server

FROM gcr.io/distroless/static@sha256:<digest> AS final
COPY --from=builder /app /app
ENTRYPOINT ["/app"]
```

### COPY --chown Pattern

When copying files as non-root, use `--chown` to avoid root-owned files:

```dockerfile
COPY --chown=appuser:appgroup --from=builder /app /app
```

### Checks

| Check                                                            | Severity                   |
| ---------------------------------------------------------------- | -------------------------- | -------- |
| Final stage runs as root (no `USER` instruction)                 | High                       |
| Final stage is not scratch/distroless/alpine-based               | Medium                     |
| `COPY` without `--chown` for non-root user                       | Medium                     |
| `RUN curl ...                                                    | bash` pattern in any stage | Critical |
| Package install without version pinning in `RUN apt-get install` | Medium                     |
| `ADD` used instead of `COPY` (allows remote URL expansion)       | High                       |

### APT/APK Version Pinning

```dockerfile
# VIOLATION — no version pins
RUN apt-get install -y curl git

# CORRECT — with version pins
RUN apt-get install -y \
    curl=7.88.1-10+deb12u5 \
    git=1:2.39.2-1.1

# ALTERNATIVE — use digest-pinned base that already has these tools
```

---

## SBOM for Container Images

Generate a Software Bill of Materials for audit and compliance:

```bash
# syft — generates SBOM from image
syft python:3.12-slim@sha256:<digest> -o spdx-json > sbom.spdx.json

# grype — scan SBOM for vulnerabilities
grype sbom:./sbom.spdx.json

```

Add to CI workflow (Dimension 1 applies — pin these actions too):

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@<sha> # pin to full SHA
  with:
    image: ${{ env.IMAGE_REF }}
    format: spdx-json
    output-file: sbom.spdx.json

- name: Scan for vulnerabilities
  uses: anchore/scan-action@<sha> # pin to full SHA
  with:
    sbom: sbom.spdx.json
    fail-build: true
    severity-cutoff: high
```

---

## Verification Checklist (Containers)

- [ ] All `FROM` instructions use digest pinning (`@sha256:...`)
- [ ] Digest has version comment (`# 3.12.3-slim`)
- [ ] Final stage is scratch, distroless, or minimal alpine
- [ ] `USER` instruction drops to non-root before `CMD`/`ENTRYPOINT`
- [ ] No `RUN curl ... | bash` or `RUN wget ... | sh` patterns
- [ ] Multi-stage: all intermediate stages also digest-pinned
- [ ] SBOM generation step in CI workflow
