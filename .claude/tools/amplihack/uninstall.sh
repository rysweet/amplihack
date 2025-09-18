#!/bin/bash

# uninstall the amplihack tools by removing the ~/.claude/agents/amplihack and ~/.claude/commands/amplihack directories
rm -rf ~/.claude/agents/amplihack
rm -rf ~/.claude/commands/amplihack
rm -rf ~/.claude/tools/amplihack

# copy the ~/.claude/settings.json file to ~/.claude/settings.json.bak.amplihack as a backup
cp ~/.claude/settings.json ~/.claude/settings.json.bak.amplihack
echo "Backup of ~/.claude/settings.json created at ~/.claude/settings.json.bak.amplihack"
rm -rf ~/.claude/settings.json
