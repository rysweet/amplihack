# Install Node.js and npm for Claude Code
RUN apt-get update && apt-get install -y nodejs npm curl git sudo

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user (Claude Code blocks --dangerously-skip-permissions as root)
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER claude
WORKDIR /home/claude

# Verify installation
RUN claude --version
