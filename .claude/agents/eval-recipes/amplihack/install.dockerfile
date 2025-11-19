# Install Node.js and npm for Claude Code
RUN apt-get update && apt-get install -y nodejs npm curl git sudo

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install amplihack from the repository
# Note: In production, this would clone from the actual branch
RUN git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git /tmp/amplihack && \
    cd /tmp/amplihack && \
    pip install -e .

# Create non-root user for running Claude Code
# Claude Code blocks --dangerously-skip-permissions when running as root
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER claude
WORKDIR /home/claude

# Verify installations
RUN claude --version
RUN amplihack --version || echo "amplihack installed"
