# Docker Support for amplihack

Working Docker setup for running amplihack in containers.

## Quick Start

```bash
# Build image
docker build -f docker/Dockerfile -t amplihack:latest .

# Run with API key
docker run -it -e ANTHROPIC_API_KEY=sk-ant-... amplihack:latest amplihack claude

# Or use docker-compose
export ANTHROPIC_API_KEY=sk-ant-...
docker-compose -f docker/docker-compose.yml run amplihack claude
```

## Why This Works

Claude Code blocks `--dangerously-skip-permissions` when running as root (uid == 0).

**Solution:** Run as non-root user in the container:

```dockerfile
RUN useradd -m -s /bin/bash claude
USER claude
```

Now:

- Container runs as `claude` user (uid != 0)
- `--dangerously-skip-permissions` works fine
- No amplihack code changes needed

## Files

- `Dockerfile` - Working container image with non-root user
- `docker-compose.yml` - Convenient docker-compose setup
- `README.md` - This file

## Usage Examples

### Interactive Session

```bash
docker run -it \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/workspace:/home/claude/workspace \
  amplihack:latest \
  amplihack claude
```

### One-Shot Task

```bash
docker run --rm \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  amplihack:latest \
  amplihack claude -- "Create a Python script for data analysis"
```

### With docker-compose

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run
docker-compose -f docker/docker-compose.yml run amplihack claude

# Or with specific task
docker-compose -f docker/docker-compose.yml run amplihack claude -- "task here"
```

## For eval-recipes

For eval-recipes benchmarking, use the agent configs in `~/.amplihack/.claude/agents/eval-recipes/` which follow this same non-root pattern.

## Troubleshooting

**Error: "--dangerously-skip-permissions cannot be used with root"**

- Check Dockerfile has `USER claude` directive
- Verify you're not using `--user root` when running container

**Permission denied in workspace**

- Ensure volume mount has correct permissions
- Container runs as `claude` user (uid 1000 by default)

## References

- Issue #1406
- Docker best practices: Use non-root users
