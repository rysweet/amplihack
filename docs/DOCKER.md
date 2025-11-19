# Running amplihack in Docker

## The Proper Way: Non-Root User

Claude Code blocks `--dangerously-skip-permissions` when running as root (`uid == 0`) for security.

**Solution:** Run as non-root user in your Docker containers.

### Dockerfile Template

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y nodejs npm git sudo

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Install amplihack
RUN pip install amplihack

# Create non-root user
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER claude
WORKDIR /home/claude

# Verify
RUN claude --version && amplihack --version
```

### Why This Works

- Container runs as `claude` user (uid != 0)
- `--dangerously-skip-permissions` flag works fine
- No amplihack code changes needed
- Follows Docker best practices

### Usage

```bash
# Build image
docker build -t amplihack:latest .

# Run
docker run -it -e ANTHROPIC_API_KEY=sk-ant-... amplihack:latest amplihack claude

# Or with docker-compose
docker-compose run amplihack claude
```

### DO NOT

❌ Run containers as root
❌ Add containerized detection code
❌ Work around Claude Code's security check

### DO

✅ Use non-root user (USER directive)
✅ Follow Docker security best practices
✅ Keep amplihack code simple

## For eval-recipes

See agent configs in `.claude/agents/eval-recipes/` which follow this pattern.

## References

- Issue #1406
- Docker best practices: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
