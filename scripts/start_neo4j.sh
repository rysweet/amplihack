#!/bin/bash
# Start Neo4j container directly using docker run
# Bypasses docker-compose entirely

set -e

# Configuration
CONTAINER_NAME="amplihack-neo4j"
NEO4J_IMAGE="neo4j:5.15-community"
PASSWORD_FILE="$HOME/.amplihack/.neo4j_password"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Neo4j Container Startup Script"
echo "============================================================"

# Create password file directory
mkdir -p "$(dirname "$PASSWORD_FILE")"

# Generate or load password
if [ ! -f "$PASSWORD_FILE" ]; then
    echo -e "${GREEN}Generating secure password...${NC}"
    # Generate 32-character random password
    PASSWORD=$(tr -dc 'A-Za-z0-9!@#$%^&*()_+=-' < /dev/urandom | head -c 32)
    echo "$PASSWORD" > "$PASSWORD_FILE"
    chmod 600 "$PASSWORD_FILE"
    echo -e "${GREEN}✅ Password saved to $PASSWORD_FILE${NC}"
else
    echo -e "${GREEN}Using existing password from $PASSWORD_FILE${NC}"
fi

PASSWORD=$(cat "$PASSWORD_FILE")

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Container exists, check if running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}✅ Container $CONTAINER_NAME is already running${NC}"
        exit 0
    else
        echo -e "${YELLOW}🔄 Starting existing container $CONTAINER_NAME${NC}"
        docker start "$CONTAINER_NAME"
        echo -e "${GREEN}✅ Container started${NC}"
        exit 0
    fi
fi

# Pull image if not present
echo -e "${YELLOW}📥 Pulling Neo4j image...${NC}"
docker pull "$NEO4J_IMAGE"

# Start new container
echo -e "${YELLOW}🚀 Starting new Neo4j container: $CONTAINER_NAME${NC}"

docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p 127.0.0.1:7474:7474 \
    -p 127.0.0.1:7687:7687 \
    -e NEO4J_AUTH="neo4j/$PASSWORD" \
    -e NEO4J_PLUGINS='["apoc"]' \
    -e NEO4J_server_memory_heap_initial__size=1G \
    -e NEO4J_server_memory_heap_max__size=2G \
    -e NEO4J_server_memory_pagecache_size=1G \
    -v amplihack-neo4j-data:/data \
    "$NEO4J_IMAGE"

echo -e "${GREEN}✅ Container started successfully!${NC}"

# Wait for Neo4j to be ready
echo -e "${YELLOW}⏳ Waiting for Neo4j to be ready...${NC}"
MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "Started\."; then
        echo -e "${GREEN}✅ Neo4j is ready!${NC}"
        echo ""
        echo "================================================"
        echo "Neo4j is now running:"
        echo "  - UI: http://localhost:7474"
        echo "  - Bolt: bolt://localhost:7687"
        echo "  - Username: neo4j"
        echo "  - Password: (in $PASSWORD_FILE)"
        echo "================================================"
        exit 0
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo -n "."
done

echo ""
echo -e "${RED}❌ Timeout waiting for Neo4j (${MAX_WAIT}s)${NC}"
echo "Check logs with: docker logs $CONTAINER_NAME"
exit 1
