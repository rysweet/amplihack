#!/bin/bash
# Enhanced install script for dual-mode hook path management
# if the AMPLIHACK_INSTALL_LOCATION variable is not set, default to https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding
AMPLIHACK_INSTALL_LOCATION=${AMPLIHACK_INSTALL_LOCATION:-https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding}

# clone the repository to a tmp local directory
# make sure the dir does not exist first - exit if it does
if [ -d "./tmpamplihack" ]; then
  echo "Error: ./tmpamplihack directory already exists. Please remove it and try again."
  exit 1
fi

echo "Downloading amplihack from $AMPLIHACK_INSTALL_LOCATION..."
git clone $AMPLIHACK_INSTALL_LOCATION ./tmpamplihack

if [ $? -ne 0 ]; then
  echo "Error: Failed to clone repository"
  exit 1
fi

# Backup existing settings.json if it exists
if [ -f ~/.claude/settings.json ]; then
  BACKUP_FILE=~/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)
  echo "Backing up existing settings.json to $BACKUP_FILE"
  cp ~/.claude/settings.json "$BACKUP_FILE"

  if [ $? -ne 0 ]; then
    echo "Error: Failed to backup existing settings.json"
    rm -rf ./tmpamplihack
    exit 1
  fi
fi

# copy the contents of the tmp local directory to the ~/.claude directory
echo "Installing amplihack to ~/.claude..."
cp -r ./tmpamplihack/.claude ~/

if [ $? -ne 0 ]; then
  echo "Error: Failed to copy files to ~/.claude"
  rm -rf ./tmpamplihack
  exit 1
fi

# Update hook paths in settings.json for global installation
echo "Updating hook paths for global installation..."
if [ -f ~/.claude/settings.json ]; then
  # Use sed to replace project-relative paths with global $HOME paths
  sed -i.tmp 's|"\.claude/tools/amplihack/hooks/session_start\.py"|"$HOME/.claude/tools/amplihack/hooks/session_start.py"|g' ~/.claude/settings.json
  sed -i.tmp 's|"\.claude/tools/amplihack/hooks/stop\.py"|"$HOME/.claude/tools/amplihack/hooks/stop.py"|g' ~/.claude/settings.json
  sed -i.tmp 's|"\.claude/tools/amplihack/hooks/post_tool_use\.py"|"$HOME/.claude/tools/amplihack/hooks/post_tool_use.py"|g' ~/.claude/settings.json

  # Remove temporary files created by sed
  rm -f ~/.claude/settings.json.tmp

  if [ $? -ne 0 ]; then
    echo "Warning: Failed to update hook paths in settings.json"
  else
    echo "Successfully updated hook paths for global installation"
  fi
else
  echo "Warning: settings.json not found after installation"
fi

# remove the tmp local directory
rm -rf ./tmpamplihack

echo "Installation complete! Amplihack hooks are now available globally."
