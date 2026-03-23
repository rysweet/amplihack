# Container Supply Chain — Dimensions 5 and 12

## Dimension 5: Container Base Image Pinning

Scan all `Dockerfile*` for `FROM` directives.

**High**: mutable tag used — `:latest`, `:alpine`, `:3.23`, `:slim`, etc.
Examples:

- `FROM node:20` — mutable minor/patch updates
- `FROM python:3.12-alpine` — mutable patch updates
- `FROM ubuntu:latest` — maximally mutable

Compliant form: `FROM alpine@sha256:4bcff0c56a0e48a4e4c1...`

**Check multi-stage builds**: intermediate `FROM` stages must also be pinned.

**Check `docker pull` in CI `run:` steps** using unpinned tags.

**Fix template:**

```
# Find current digest:
# docker pull <image>:<tag> && docker inspect --format='{{index .RepoDigests 0}}' <image>:<tag>
#
# Replace:
# FROM python:3.12-slim
# with:
# FROM python:3.12-slim@sha256:<digest>  # 3.12-slim
```

## Dimension 12: Docker / OCI Build Chain

**Critical**: `RUN curl | sh` or `RUN wget -O- | bash` patterns — unsigned remote execution.
**Critical**: `ADD <url>` with remote URLs (downloads without checksum verification).
**High**: `ARG`-passed secrets in multi-stage builds (leaks into image layers).
Recommend `--mount=type=secret` instead.
**Medium**: `.dockerignore` missing or not excluding `.git/`, `.env`, `*.key`, `*.pem`.
**Medium**: `docker login` with `--password` on command line in CI scripts.
**Info**: image pulls from public registries without `DOCKER_CONTENT_TRUST=1`.

Check ACR/GHCR/ECR authentication: flag stored passwords; recommend token-based auth.
