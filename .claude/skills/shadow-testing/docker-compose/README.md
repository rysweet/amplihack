# Docker Compose Examples for Shadow Testing

These Docker Compose configurations provide declarative shadow environment setups for different use cases.

## Files

- `single-repo.yml` - Basic single repository shadow
- `multi-repo.yml` - Multiple coordinated repositories
- `ci-shadow.yml` - CI-optimized automated testing

## Prerequisites

- Docker or Podman with Docker Compose support
- Git bundles created from your local repositories

## Quick Start

### Single Repository

```bash
# 1. Create bundle from your local repo
git -C ~/repos/my-lib bundle create snapshots/my-lib.bundle --all

# 2. Create directory structure
mkdir -p snapshots workspace

# 3. Start shadow
docker-compose -f docker-compose/single-repo.yml up -d

# 4. Watch logs
docker-compose -f docker-compose/single-repo.yml logs -f

# 5. Once ready, test
docker-compose exec shadow bash
```

Inside the shadow container:
```bash
# Verify git URL rewriting works
git clone https://github.com/myorg/my-lib /tmp/test
cd /tmp/test
git log -1 --oneline  # Should show your local commit

# Or use pre-cloned workspace
cd /workspace/myorg/my-lib
pip install -e .
pytest
```

### Multi-Repository

```bash
# 1. Create bundles for each repo
git -C ~/repos/core-lib bundle create snapshots/core-lib.bundle --all
git -C ~/repos/cli-tool bundle create snapshots/cli-tool.bundle --all

# 2. Start shadow
docker-compose -f docker-compose/multi-repo.yml up -d

# 3. Test coordinated changes
docker-compose exec shadow bash -c "
  cd /workspace &&
  git clone https://github.com/myorg/cli-tool &&
  cd cli-tool &&
  pip install git+https://github.com/myorg/core-lib &&
  pytest
"
```

### CI Integration

#### GitHub Actions

```yaml
# .github/workflows/shadow-test.yml
name: Shadow Test

on: [push, pull_request]

jobs:
  shadow-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create git bundle
        run: |
          git bundle create snapshot.bundle --all
          mkdir -p test-results

      - name: Run shadow tests
        run: |
          docker-compose -f docker-compose/ci-shadow.yml run --rm ci-shadow
        env:
          REPO_ORG: myorg
          REPO_NAME: my-repo

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

#### GitLab CI

```yaml
# .gitlab-ci.yml
shadow-test:
  image: docker:latest
  services:
    - docker:dind
  script:
    - git bundle create snapshot.bundle --all
    - mkdir -p test-results
    - docker-compose -f docker-compose/ci-shadow.yml run --rm ci-shadow
  artifacts:
    paths:
      - test-results/
    when: always
```

## Configuration

### Environment Variables

Pass environment variables to the shadow:

```yaml
environment:
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - CUSTOM_VAR=value
```

Or use `.env` file:
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Custom Repository Names

Edit the compose file to match your org/repo:

```yaml
# Change these lines in the command section
echo 'Setting up repository myorg/my-lib...' &&
curl -s -u shadow:shadow -H 'Content-Type: application/json' \
  -d '{"username":"myorg"}' \
  http://localhost:3000/api/v1/orgs &&
curl -s -u shadow:shadow -H 'Content-Type: application/json' \
  -d '{"name":"my-lib","private":false}' \
  http://localhost:3000/api/v1/orgs/myorg/repos &&
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs shadow
```

Common issues:
- Bundle file not found: Check path in volumes section
- Gitea timeout: Increase sleep time in command
- Port conflict: Change exposed ports in compose file

### Tests Fail Inside Shadow

Verify local sources are being used:
```bash
docker-compose exec shadow bash -c "
  git clone https://github.com/myorg/my-lib /tmp/test &&
  cd /tmp/test &&
  git log -1 --format='%H'
"
# Compare with your local commit SHA
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (workspace, etc.)
docker-compose down -v

# Remove all shadow-related containers
docker ps -a | grep shadow | awk '{print $1}' | xargs docker rm -f
```

## Advanced Usage

### Custom Docker Image

Build your own shadow image with additional tools:

```dockerfile
# Dockerfile.custom-shadow
FROM ghcr.io/microsoft/amplifier-shadow:latest

# Add tools
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    jq

# Add custom scripts
COPY scripts/ /usr/local/bin/
```

Update compose file:
```yaml
services:
  shadow:
    build:
      context: .
      dockerfile: Dockerfile.custom-shadow
    # ... rest of config
```

### Multiple Shadows in Parallel

```yaml
# docker-compose.parallel.yml
version: '3.8'

services:
  shadow-python:
    image: ghcr.io/microsoft/amplifier-shadow:latest
    container_name: shadow-python-test
    volumes:
      - ./snapshots/python-lib.bundle:/snapshots/lib.bundle:ro
    # ... config for Python project

  shadow-node:
    image: ghcr.io/microsoft/amplifier-shadow:latest
    container_name: shadow-node-test
    volumes:
      - ./snapshots/node-pkg.bundle:/snapshots/pkg.bundle:ro
    # ... config for Node.js project
```

Run both:
```bash
docker-compose -f docker-compose.parallel.yml up -d
```

## See Also

- Main shadow-testing skill: `../SKILL.md`
- Shell scripts: `../scripts/`
- Amplifier shadow bundle: https://github.com/microsoft/amplifier-bundle-shadow
