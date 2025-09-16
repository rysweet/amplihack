#!/usr/bin/env bash

# Disable Amplifier's Claude configuration in claude-flow
# This script removes the symlink and optionally restores the backup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="${SCRIPT_DIR}/.claude"
BACKUP_DIR="${SCRIPT_DIR}/.claude.backup"

echo "🔓 Disabling Amplifier Claude Bridge..."

# Check if .claude exists
if [ ! -e "$CLAUDE_DIR" ]; then
    echo -e "${YELLOW}⚠️  No .claude directory found. Nothing to disable.${NC}"

    # Check if backup exists
    if [ -e "$BACKUP_DIR" ]; then
        echo ""
        echo -e "${BLUE}📦 Found backup at .claude.backup${NC}"
        read -p "Would you like to restore the backup? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv "$BACKUP_DIR" "$CLAUDE_DIR"
            echo -e "${GREEN}✅ Backup restored to .claude${NC}"
        fi
    fi
    exit 0
fi

# Check if .claude is a symlink
if [ -L "$CLAUDE_DIR" ]; then
    TARGET=$(readlink "$CLAUDE_DIR")
    echo -e "${YELLOW}🔗 Found symlink pointing to: ${TARGET}${NC}"

    # Remove the symlink
    rm "$CLAUDE_DIR"
    echo -e "${GREEN}✅ Symlink removed${NC}"

    # Check if backup exists
    if [ -e "$BACKUP_DIR" ]; then
        echo ""
        echo -e "${BLUE}📦 Found backup at .claude.backup${NC}"
        read -p "Would you like to restore the backup? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv "$BACKUP_DIR" "$CLAUDE_DIR"
            echo -e "${GREEN}✅ Backup restored to .claude${NC}"
        else
            echo "Backup preserved at .claude.backup"
            echo "You can manually restore it later by running:"
            echo "  mv .claude.backup .claude"
        fi
    else
        echo ""
        echo "No backup found. The .claude directory has been removed."
        echo "You can create a new local .claude configuration if needed."
    fi
else
    echo -e "${YELLOW}⚠️  .claude exists but is not a symlink${NC}"
    echo "This might be a local configuration. No action taken."
    echo ""

    # Check if backup exists
    if [ -e "$BACKUP_DIR" ]; then
        echo -e "${YELLOW}📦 Note: A backup exists at .claude.backup${NC}"
        echo "You may want to manually review both directories."
    fi
    exit 0
fi

# Handle .ai directory
AI_DIR="${SCRIPT_DIR}/.ai"
AI_BACKUP_DIR="${SCRIPT_DIR}/.ai.backup"

# Check if .ai is a symlink to amplifier
if [ -L "$AI_DIR" ]; then
    AI_TARGET=$(readlink "$AI_DIR")
    if [[ "$AI_TARGET" == *"amplifier"* ]]; then
        echo ""
        echo -e "${YELLOW}📚 Found .ai symlink pointing to: ${AI_TARGET}${NC}"

        # Remove the symlink
        rm "$AI_DIR"
        echo -e "${GREEN}✅ .ai symlink removed${NC}"

        # Check if .ai backup exists
        if [ -e "$AI_BACKUP_DIR" ]; then
            echo ""
            echo -e "${BLUE}📦 Found .ai backup at .ai.backup${NC}"
            read -p "Would you like to restore the .ai backup? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                mv "$AI_BACKUP_DIR" "$AI_DIR"
                echo -e "${GREEN}✅ .ai backup restored${NC}"
            else
                echo "Backup preserved at .ai.backup"
            fi
        fi
    fi
fi

# Handle .mcp.json file
MCP_FILE="${SCRIPT_DIR}/.mcp.json"
MCP_BACKUP="${SCRIPT_DIR}/.mcp.json.backup"

# Check if .mcp.json is a symlink to amplifier
if [ -L "$MCP_FILE" ]; then
    MCP_TARGET=$(readlink "$MCP_FILE")
    if [[ "$MCP_TARGET" == *"amplifier"* ]]; then
        echo ""
        echo -e "${YELLOW}🔌 Found .mcp.json symlink pointing to: ${MCP_TARGET}${NC}"

        # Remove the symlink
        rm "$MCP_FILE"
        echo -e "${GREEN}✅ .mcp.json symlink removed${NC}"

        # Check if .mcp.json backup exists
        if [ -e "$MCP_BACKUP" ]; then
            echo ""
            echo -e "${BLUE}📦 Found .mcp.json backup${NC}"
            read -p "Would you like to restore the .mcp.json backup? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                mv "$MCP_BACKUP" "$MCP_FILE"
                echo -e "${GREEN}✅ .mcp.json backup restored${NC}"
            else
                echo "Backup preserved at .mcp.json.backup"
            fi
        fi
    fi
fi

echo ""
echo -e "${GREEN}✅ Amplifier Claude Bridge disabled successfully!${NC}"
echo ""
echo "The claude-flow project now uses:"
if [ -d "$CLAUDE_DIR" ]; then
    echo "  • Its own local .claude configuration"
else
    echo "  • No .claude configuration (you can create one if needed)"
fi
if [ -d "$AI_DIR" ] && [ ! -L "$AI_DIR" ]; then
    echo "  • Its own local .ai documentation"
elif [ ! -e "$AI_DIR" ]; then
    echo "  • No .ai documentation"
fi
if [ -f "$MCP_FILE" ] && [ ! -L "$MCP_FILE" ]; then
    echo "  • Its own MCP server configuration"
elif [ ! -e "$MCP_FILE" ]; then
    echo "  • No MCP servers configured"
fi
echo ""
echo "To re-enable the bridge, run: ./enable-amplifier-claude.sh"