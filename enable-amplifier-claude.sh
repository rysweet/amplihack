#!/usr/bin/env bash

# Enable Amplifier's Claude configuration in claude-flow
# This script creates a symlink from .claude to ../amplifier/.claude

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="${SCRIPT_DIR}/.claude"
AMPLIFIER_CLAUDE="${SCRIPT_DIR}/../amplifier/.claude"
BACKUP_DIR="${SCRIPT_DIR}/.claude.backup"
GITIGNORE="${SCRIPT_DIR}/.gitignore"

echo "🔗 Enabling Amplifier Claude Bridge..."

# Check if amplifier/.claude exists
if [ ! -d "$AMPLIFIER_CLAUDE" ]; then
    echo -e "${RED}❌ Error: Amplifier's .claude directory not found at ${AMPLIFIER_CLAUDE}${NC}"
    echo "Please ensure the amplifier project is located at ../amplifier/"
    exit 1
fi

# Check if .claude already exists
if [ -e "$CLAUDE_DIR" ]; then
    if [ -L "$CLAUDE_DIR" ]; then
        # It's already a symlink
        CURRENT_TARGET=$(readlink "$CLAUDE_DIR")
        if [ "$CURRENT_TARGET" = "../amplifier/.claude" ]; then
            echo -e "${YELLOW}⚠️  Symlink already exists and points to amplifier/.claude${NC}"
            echo "Bridge is already enabled. No action needed."
            exit 0
        else
            echo -e "${YELLOW}⚠️  Symlink exists but points to: ${CURRENT_TARGET}${NC}"
            echo "Removing old symlink..."
            rm "$CLAUDE_DIR"
        fi
    else
        # It's a regular directory/file
        echo -e "${YELLOW}📦 Backing up existing .claude directory...${NC}"
        if [ -e "$BACKUP_DIR" ]; then
            echo -e "${YELLOW}⚠️  Backup already exists at .claude.backup${NC}"
            echo "Please manually resolve the backup before proceeding."
            exit 1
        fi
        mv "$CLAUDE_DIR" "$BACKUP_DIR"
        echo -e "${GREEN}✅ Backed up to .claude.backup${NC}"
    fi
fi

# Create the symlink
echo "Creating symlink from .claude to ../amplifier/.claude..."
ln -s ../amplifier/.claude "$CLAUDE_DIR"

if [ -L "$CLAUDE_DIR" ]; then
    echo -e "${GREEN}✅ Symlink created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create symlink${NC}"
    exit 1
fi

# Handle .ai directory symlink
AI_DIR="${SCRIPT_DIR}/.ai"
AMPLIFIER_AI="${SCRIPT_DIR}/../amplifier/.ai"
AI_BACKUP_DIR="${SCRIPT_DIR}/.ai.backup"

# Check if amplifier/.ai exists
if [ -d "$AMPLIFIER_AI" ]; then
    echo ""
    echo "📚 Setting up .ai documentation link..."

    # Check if .ai already exists
    if [ -e "$AI_DIR" ]; then
        if [ -L "$AI_DIR" ]; then
            # It's already a symlink
            CURRENT_AI_TARGET=$(readlink "$AI_DIR")
            if [ "$CURRENT_AI_TARGET" = "../amplifier/.ai" ]; then
                echo -e "${YELLOW}⚠️  .ai symlink already points to amplifier/.ai${NC}"
            else
                echo -e "${YELLOW}⚠️  .ai symlink exists but points to: ${CURRENT_AI_TARGET}${NC}"
                echo "Removing old symlink..."
                rm "$AI_DIR"
                ln -s ../amplifier/.ai "$AI_DIR"
                echo -e "${GREEN}✅ .ai symlink updated${NC}"
            fi
        else
            # It's a regular directory/file
            echo -e "${YELLOW}📦 Backing up existing .ai directory...${NC}"
            if [ -e "$AI_BACKUP_DIR" ]; then
                echo -e "${YELLOW}⚠️  .ai backup already exists at .ai.backup${NC}"
                echo "Skipping .ai symlink to preserve existing backup."
            else
                mv "$AI_DIR" "$AI_BACKUP_DIR"
                echo -e "${GREEN}✅ Backed up to .ai.backup${NC}"
                ln -s ../amplifier/.ai "$AI_DIR"
                echo -e "${GREEN}✅ .ai symlink created${NC}"
            fi
        fi
    else
        # .ai doesn't exist, create symlink
        ln -s ../amplifier/.ai "$AI_DIR"
        echo -e "${GREEN}✅ .ai symlink created successfully${NC}"
    fi
fi

# Handle .mcp.json symlink for MCP servers
MCP_FILE="${SCRIPT_DIR}/.mcp.json"
AMPLIFIER_MCP="${SCRIPT_DIR}/../amplifier/.mcp.json"
MCP_BACKUP="${SCRIPT_DIR}/.mcp.json.backup"

# Check if amplifier/.mcp.json exists
if [ -f "$AMPLIFIER_MCP" ]; then
    echo ""
    echo "🔌 Setting up MCP servers configuration..."

    # Check if .mcp.json already exists
    if [ -e "$MCP_FILE" ]; then
        if [ -L "$MCP_FILE" ]; then
            # It's already a symlink
            CURRENT_MCP_TARGET=$(readlink "$MCP_FILE")
            if [ "$CURRENT_MCP_TARGET" = "../amplifier/.mcp.json" ]; then
                echo -e "${YELLOW}⚠️  .mcp.json symlink already points to amplifier/.mcp.json${NC}"
            else
                echo -e "${YELLOW}⚠️  .mcp.json symlink exists but points to: ${CURRENT_MCP_TARGET}${NC}"
                echo "Removing old symlink..."
                rm "$MCP_FILE"
                ln -s ../amplifier/.mcp.json "$MCP_FILE"
                echo -e "${GREEN}✅ .mcp.json symlink updated${NC}"
            fi
        else
            # It's a regular file
            echo -e "${YELLOW}📦 Backing up existing .mcp.json...${NC}"
            if [ -e "$MCP_BACKUP" ]; then
                echo -e "${YELLOW}⚠️  .mcp.json backup already exists${NC}"
                echo "Skipping .mcp.json symlink to preserve existing backup."
            else
                mv "$MCP_FILE" "$MCP_BACKUP"
                echo -e "${GREEN}✅ Backed up to .mcp.json.backup${NC}"
                ln -s ../amplifier/.mcp.json "$MCP_FILE"
                echo -e "${GREEN}✅ .mcp.json symlink created${NC}"
            fi
        fi
    else
        # .mcp.json doesn't exist, create symlink
        ln -s ../amplifier/.mcp.json "$MCP_FILE"
        echo -e "${GREEN}✅ .mcp.json symlink created${NC}"
        echo "  MCP servers available: browser-use, context7, deepwiki, repomix, zen"
    fi
fi

# Add .claude, .ai, and .mcp.json to .gitignore if not already present
if [ -f "$GITIGNORE" ]; then
    ADDED_TO_GITIGNORE=false

    if ! grep -q "^\.claude$" "$GITIGNORE" 2>/dev/null; then
        echo ".claude" >> "$GITIGNORE"
        ADDED_TO_GITIGNORE=true
        echo "✓ Added .claude to .gitignore"
    fi

    if ! grep -q "^\.ai$" "$GITIGNORE" 2>/dev/null; then
        echo ".ai" >> "$GITIGNORE"
        ADDED_TO_GITIGNORE=true
        echo "✓ Added .ai to .gitignore"
    fi

    if ! grep -q "^\.mcp\.json$" "$GITIGNORE" 2>/dev/null; then
        echo ".mcp.json" >> "$GITIGNORE"
        ADDED_TO_GITIGNORE=true
        echo "✓ Added .mcp.json to .gitignore"
    fi

    if [ "$ADDED_TO_GITIGNORE" = false ]; then
        echo "✓ .claude, .ai, and .mcp.json already in .gitignore"
    fi
else
    echo "Creating .gitignore with entries..."
    echo -e ".claude\n.ai\n.mcp.json" > "$GITIGNORE"
    echo -e "${GREEN}✅ Created .gitignore with entries${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Amplifier Claude Bridge enabled successfully!${NC}"
echo ""
echo "You now have access to:"
echo "  • All Amplifier's Claude agents and tools"
echo "  • Shared context and configurations"
echo "  • Knowledge synthesis capabilities"
echo ""
echo "To disable the bridge, run: ./disable-amplifier-claude.sh"