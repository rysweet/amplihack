# Dockerfile for amplihack
# Version alignment: Match CI configuration (Python 3.12, Node 20)
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip to latest
RUN pip install --no-cache-dir --upgrade pip

# Install UV package manager via official installer (more reliable than pip)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install Python dependencies with UV
RUN uv pip install --system -e .

# Install Claude CLI via npm (if available)
RUN npm install -g @anthropic-ai/claude-cli || echo "Claude CLI not available via npm"

# Create non-root user 'amplihack' with UID 1000
RUN useradd -m -u 1000 -s /bin/bash amplihack

# Create workspace directory for mounted code and set ownership
RUN mkdir -p /workspace && \
    chown -R amplihack:amplihack /app /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AMPLIHACK_IN_DOCKER=1

# Switch to non-root user
USER amplihack

# Default working directory for user code
WORKDIR /workspace

# Entry point
ENTRYPOINT ["amplihack"]
CMD ["--help"]
