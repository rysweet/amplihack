FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy full source tree and install from source so agents/ is included
COPY . /build
RUN cd /build && pip install --no-cache-dir . && \
    pip install --no-cache-dir kuzu && \
    pip install --no-cache-dir sentence-transformers && \
    pip install --no-cache-dir "azure-eventhub==5.11.7" redis pyyaml \
        opentelemetry-exporter-otlp-proto-http \
        opentelemetry-exporter-otlp-proto-grpc

# Create non-root user (security best practice for Container Apps)
RUN useradd -m -s /bin/bash amplihack-agent \
    && mkdir -p /data \
    && chown -R amplihack-agent:amplihack-agent /app /data

# Copy entrypoint
COPY deploy/azure_hive/agent_entrypoint.py /app/agent_entrypoint.py

USER amplihack-agent
ENV HOME=/home/amplihack-agent

# Data directory for Kuzu persistence (mounted as Azure File Share)
VOLUME ["/data"]

# Health check via process existence
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import os, sys; sys.exit(0 if os.path.exists('/tmp/.agent_ready') else 1)"

CMD ["python3", "/app/agent_entrypoint.py"]
