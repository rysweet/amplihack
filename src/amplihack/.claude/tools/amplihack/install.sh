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

echo "Cloning amplihack from $AMPLIHACK_INSTALL_LOCATION..."
git clone $AMPLIHACK_INSTALL_LOCATION ./tmpamplihack

if [ $? -ne 0 ]; then
  echo "Error: Failed to clone repository"
  exit 1
fi

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

# Update hook paths in settings.json with comprehensive path handling
if [ -f "$HOME/.claude/settings.json" ]; then
  echo "Updating hook paths in settings.json for global installation..."

  # Check current path format and report status
  if grep -q '"\.claude/tools/amplihack/hooks/' "$HOME/.claude/settings.json"; then
    echo "  → Found relative paths, converting to absolute paths..."
    PATH_FORMAT="relative"
  elif grep -q '"~/.claude/tools/amplihack/hooks/' "$HOME/.claude/settings.json"; then
    echo "  → Found tilde paths, converting to absolute paths..."
    PATH_FORMAT="tilde"
  elif grep -q "\"$HOME/.claude/tools/amplihack/hooks/" "$HOME/.claude/settings.json"; then
    echo "  → Paths already absolute, checking consistency..."
    PATH_FORMAT="absolute"
  else
    echo "  → No amplihack hook paths found, this may be a new installation"
    PATH_FORMAT="unknown"
  fi

  # Comprehensive sed replacement handling all path formats
  sed -i.tmp \
    -e 's|"\.claude/tools/amplihack/hooks/session_start\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/session_start.py"|g' \
    -e 's|"~/.claude/tools/amplihack/hooks/session_start\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/session_start.py"|g' \
    -e 's|"'"$HOME"'/.claude/tools/amplihack/hooks/session_start\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/session_start.py"|g' \
    -e 's|"\.claude/tools/amplihack/hooks/stop\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/stop.py"|g' \
    -e 's|"~/.claude/tools/amplihack/hooks/stop\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/stop.py"|g' \
    -e 's|"'"$HOME"'/.claude/tools/amplihack/hooks/stop\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/stop.py"|g' \
    -e 's|"\.claude/tools/amplihack/hooks/post_tool_use\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/post_tool_use.py"|g' \
    -e 's|"~/.claude/tools/amplihack/hooks/post_tool_use\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/post_tool_use.py"|g' \
    -e 's|"'"$HOME"'/.claude/tools/amplihack/hooks/post_tool_use\.py"|"'"$HOME"'/.claude/tools/amplihack/hooks/post_tool_use.py"|g' \
    "$HOME/.claude/settings.json"

  if [ $? -eq 0 ]; then
    # Verify the changes were applied correctly
    UPDATED_PATHS=$(grep -c "\"$HOME/.claude/tools/amplihack/hooks/" "$HOME/.claude/settings.json")

    if [ "$UPDATED_PATHS" -eq 3 ]; then
      rm "$HOME/.claude/settings.json.tmp"
      echo "  ✅ Hook paths updated successfully (found $UPDATED_PATHS hook entries)"
      echo "  → Session start, stop, and post-tool-use hooks configured"
    elif [ "$UPDATED_PATHS" -gt 0 ]; then
      rm "$HOME/.claude/settings.json.tmp"
      echo "  ⚠️  Partial update: $UPDATED_PATHS of 3 hook paths updated"
      echo "  → Some hook paths may already be correct or have different names"
    else
      echo "  ⚠️  Warning: No hook paths were updated"
      echo "  → This might indicate the settings.json format has changed"
      echo "  → Hooks may still work if paths are already correct"
      rm "$HOME/.claude/settings.json.tmp"
    fi

    # Verify hook files exist
    echo "Verifying hook files exist..."
    MISSING_HOOKS=0
    for hook in "session_start.py" "stop.py" "post_tool_use.py"; do
      if [ -f "$HOME/.claude/tools/amplihack/hooks/$hook" ]; then
        echo "  ✅ $hook found"
      else
        echo "  ❌ $hook missing"
        MISSING_HOOKS=$((MISSING_HOOKS + 1))
      fi
    done

    if [ $MISSING_HOOKS -eq 0 ]; then
      echo "  ✅ All hook files verified"
    else
      echo "  ⚠️  Warning: $MISSING_HOOKS hook files missing"
    fi

    # StatusLine Configuration Management
    echo "Checking statusLine configuration..."

    # Check if statusLine exists in settings.json
    if grep -q '"statusLine"' "$HOME/.claude/settings.json"; then
      echo "  → Found existing statusLine configuration, updating path..."

      # Update all path formats to absolute (matches hook update pattern)
      sed -i.tmp \
        -e 's|"\.claude/tools/statusline\.sh"|"'"$HOME"'/.claude/tools/statusline.sh"|g' \
        -e 's|"\./\.claude/tools/statusline\.sh"|"'"$HOME"'/.claude/tools/statusline.sh"|g' \
        -e 's|"~/\.claude/tools/statusline\.sh"|"'"$HOME"'/.claude/tools/statusline.sh"|g' \
        -e 's|"'"$HOME"'/\.claude/tools/statusline\.sh"|"'"$HOME"'/.claude/tools/statusline.sh"|g' \
        "$HOME/.claude/settings.json"

      if [ $? -eq 0 ]; then
        rm -f "$HOME/.claude/settings.json.tmp"
        echo "  ✅ StatusLine path updated to absolute"
      else
        echo "  ⚠️  Warning: Failed to update statusLine path"
        if [ -f "$HOME/.claude/settings.json.tmp" ]; then
          mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
          echo "  → Restored original settings.json"
        fi
      fi
    else
      echo "  → No statusLine configuration found, adding..."

      # Insert statusLine configuration after the opening brace
      sed -i.tmp '0,/{/s/{/{\n  "statusLine": {\n    "type": "command",\n    "command": "'"$HOME"'/.claude/tools/statusline.sh"\n  },/' "$HOME/.claude/settings.json"

      if [ $? -eq 0 ] && grep -q '"statusLine"' "$HOME/.claude/settings.json"; then
        rm -f "$HOME/.claude/settings.json.tmp"
        echo "  ✅ StatusLine configuration added successfully"
      else
        echo "  ⚠️  Warning: Failed to add statusLine configuration"
        if [ -f "$HOME/.claude/settings.json.tmp" ]; then
          mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
          echo "  → Restored original settings.json"
        fi
      fi
    fi

    # Verify statusline.sh file exists and is executable
    if [ -f "$HOME/.claude/tools/statusline.sh" ]; then
      if [ ! -x "$HOME/.claude/tools/statusline.sh" ]; then
        chmod +x "$HOME/.claude/tools/statusline.sh" 2>/dev/null && \
          echo "  ✅ Made statusline.sh executable" || \
          echo "  ⚠️  Warning: Could not make statusline.sh executable"
      fi
    else
      echo "  ⚠️  Warning: statusline.sh not found at $HOME/.claude/tools/statusline.sh"
    fi

  else
    echo "Error: Failed to update hook paths in settings.json"
    # Restore from temp file if sed failed
    if [ -f "$HOME/.claude/settings.json.tmp" ]; then
      mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
      echo "  → Restored original settings.json"
    fi
    rm -rf ./tmpamplihack
    exit 1
  fi
else
  echo "Warning: No settings.json found after installation"
  echo "  → Creating basic settings.json with hook configuration..."

  # Create a basic settings.json if none exists
  cat > "$HOME/.claude/settings.json" << 'EOF'
{
  "permissions": {
    "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
    "deny": [],
    "defaultMode": "bypassPermissions",
    "additionalDirectories": [".claude", "Specs"]
  },
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": [],
  "statusLine": {
    "type": "command",
    "command": "HOME_PLACEHOLDER/.claude/tools/statusline.sh"
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "HOME_PLACEHOLDER/.claude/tools/amplihack/hooks/session_start.py",
            "timeout": 10000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "HOME_PLACEHOLDER/.claude/tools/amplihack/hooks/stop.py",
            "timeout": 30000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "HOME_PLACEHOLDER/.claude/tools/amplihack/hooks/post_tool_use.py"
          }
        ]
      }
    ]
  }
}
EOF

  # Replace HOME_PLACEHOLDER with actual home directory
  sed -i.tmp "s|HOME_PLACEHOLDER|$HOME|g" "$HOME/.claude/settings.json"
  rm "$HOME/.claude/settings.json.tmp"
  echo "  ✅ Created new settings.json with amplihack hooks"
fi

# remove the tmp local directory
rm -rf ./tmpamplihack

echo "Amplihack installation completed successfully!"
echo "Hook paths have been updated for global operation."
if [ -f "$HOME/.claude/settings.json.backup."* ]; then
  echo "Your previous settings.json has been backed up."
fi
