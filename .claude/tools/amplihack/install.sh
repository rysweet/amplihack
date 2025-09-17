#!/bin/bash
# if the AMPLIHACK_INSTALL_LOCATION variable is not set, default to https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding
AMPLIHACK_INSTALL_LOCATION=${AMPLIHACK_INSTALL_LOCATION:-https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding}

# clone the repository to a tmp local directory
# make sure the dir does not exist first - exit if it does
if [ -d "./tmpamplihack" ]; then
  echo "Error: ./tmpamplihack directory already exists. Please remove it and try again."
  exit 1
fi

echo "Cloning amplihack from $AMPLIHACK_INSTALL_LOCATION..."
git clone $AMPLIHACK_INSTALL_LOCATION ./tmpamplihack

# Backup existing settings.json if it exists
if [ -f "$HOME/.claude/settings.json" ]; then
  echo "Backing up existing settings.json..."
  cp "$HOME/.claude/settings.json" "$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to backup existing settings.json"
    rm -rf ./tmpamplihack
    exit 1
  fi
  echo "Backup created successfully"
fi

# copy the contents of the tmp local directory to the ~/.claude directory
echo "Installing amplihack to ~/.claude..."
cp -r ./tmpamplihack/.claude ~/
if [ $? -ne 0 ]; then
  echo "Error: Failed to copy files to ~/.claude"
  rm -rf ./tmpamplihack
  exit 1
fi

# Update hook paths in settings.json from project-relative to global paths
if [ -f "$HOME/.claude/settings.json" ]; then
  echo "Updating hook paths in settings.json for global installation..."

  # Use sed to replace project-relative paths with global paths
  sed -i.tmp \
    -e 's|"\.claude/tools/amplihack/hooks/session_start\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/session_start.py"|g' \
    -e 's|"\.claude/tools/amplihack/hooks/stop\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/stop.py"|g' \
    -e 's|"\.claude/tools/amplihack/hooks/post_tool_use\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/post_tool_use.py"|g' \
    "$HOME/.claude/settings.json"

  if [ $? -eq 0 ]; then
    rm "$HOME/.claude/settings.json.tmp"
    echo "Hook paths updated successfully"
  else
    echo "Error: Failed to update hook paths in settings.json"
    # Restore from temp file if sed failed
    if [ -f "$HOME/.claude/settings.json.tmp" ]; then
      mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
    fi
    rm -rf ./tmpamplihack
    exit 1
  fi
else
  echo "Warning: No settings.json found after installation"
fi

# remove the tmp local directory
rm -rf ./tmpamplihack

echo "Amplihack installation completed successfully!"
echo "Hook paths have been updated for global operation."
if [ -f "$HOME/.claude/settings.json.backup."* ]; then
  echo "Your previous settings.json has been backed up."
fi
