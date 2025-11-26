# Version alignment: Match CI configuration (Python 3.12, Node 20)
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (aligned with CI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager via official installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Upgrade pip to latest
RUN pip install --no-cache-dir --upgrade pip

# Install amplihack
COPY . /tmp/amplihack
RUN cd /tmp/amplihack && pip install -e . && rm -rf /tmp/amplihack

# Create non-root user (Claude Code blocks --dangerously-skip-permissions as root)
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER claude
WORKDIR /home/claude

# Set up workspace
RUN mkdir -p /home/claude/workspace
WORKDIR /home/claude/workspace

# Verify installations
RUN claude --version && amplihack --version

# Default command
CMD ["amplihack", "claude"]
