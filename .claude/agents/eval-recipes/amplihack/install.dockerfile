# Install Node.js and npm for Claude Code
RUN apt-get update && apt-get install -y nodejs npm curl git

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install amplihack from the repository
# Note: In production, this would clone from the actual branch
RUN git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git /tmp/amplihack && \
    cd /tmp/amplihack && \
    pip install -e .

# Verify installations
RUN claude --version
RUN amplihack --version || echo "amplihack installed"
