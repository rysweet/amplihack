# Dockerfile for amplihack
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

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install Python dependencies with UV
RUN uv pip install --system -e .

# Install Claude CLI via npm (if available)
RUN npm install -g @anthropic-ai/claude-cli || echo "Claude CLI not available via npm"

# Create workspace directory for mounted code
RUN mkdir -p /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AMPLIHACK_IN_DOCKER=1

# Default working directory for user code
WORKDIR /workspace

# Entry point
ENTRYPOINT ["amplihack"]
CMD ["--help"]
