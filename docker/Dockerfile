FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

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
