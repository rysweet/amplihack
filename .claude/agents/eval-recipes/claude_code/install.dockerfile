# Install Node.js and npm
RUN apt-get update && apt-get install -y nodejs npm curl

# Install Claude Code CLI globally (vanilla, no amplihack)
RUN npm install -g @anthropic-ai/claude-code

# Verify installation
RUN claude --version
