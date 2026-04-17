# Prerequisites

This document provides detailed installation instructions for all required tools across different platforms.

## Required Tools

The amplihack framework requires the following tools. Each entry explains **what** the tool does and **why** amplihack needs it:

| Tool        | Min Version    | What It Does                  | Why amplihack Needs It                                                                                 |
| ----------- | -------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Node.js** | v18+           | JavaScript runtime            | Runs Claude CLI                                                                                        |
| **npm**     | (with Node.js) | Node.js package manager       | Installs Claude CLI                                                                                    |
| **uv**      | latest         | Fast Python package installer | Installs amplihack itself and its Python dependencies                                                  |
| **git**     | 2.0+           | Version control               | Branch management, PRs, and workflow automation                                                        |
| **claude**  | latest         | Claude Code CLI               | Core AI coding assistant that amplihack extends                                                        |
| **cargo**   | 1.70+          | Rust package manager          | Installs the Rust recipe runner for fast recipe execution. Install via [rustup.rs](https://rustup.rs/) |

## Quick Check

Before installing amplihack, verify your prerequisites with this script:

```bash
# Copy-paste this into your terminal — no installation required
node --version && npm --version && uv --version && git --version && cargo --version && echo "All prerequisites OK"
```

After installing amplihack, running `amplihack` will also check for missing tools and display installation instructions.

## Platform-Specific Installation

### macOS

**Package Manager:** We recommend using [Homebrew](https://brew.sh/)

#### Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Install Required Tools

```bash
# Node.js and npm (installed together)
brew install node

# uv
brew install uv

# git
brew install git

# Rust/cargo (for recipe runner)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### Verify Installation

```bash
node --version   # Should show v18.x or higher
npm --version    # Should show 9.x or higher
uv --version     # Should show version info
git --version    # Should show 2.x or higher
cargo --version  # Should show 1.70 or higher
```

---

### Linux

**Package Managers:** apt (Ubuntu/Debian), dnf (Fedora/RHEL), pacman (Arch)

#### Ubuntu/Debian

```bash
# Node.js 18+ via NodeSource (Ubuntu ships an older version by default)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# git
sudo apt install git

# Rust/cargo (for recipe runner)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### Fedora/RHEL/CentOS

```bash
# Node.js and npm
sudo dnf install nodejs npm

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# git
sudo dnf install git

# Rust/cargo (for recipe runner)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### Arch Linux

```bash
# Node.js and npm
sudo pacman -S nodejs npm

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# git
sudo pacman -S git

# Rust/cargo (for recipe runner)
sudo pacman -S rust
```

#### Verify Installation

```bash
node --version   # Should show v18.x or higher
npm --version    # Should show 9.x or higher
uv --version     # Should show version info
git --version    # Should show 2.x or higher
cargo --version  # Should show 1.70 or higher
```

---

### Windows Subsystem for Linux (WSL)

**Recommended:** Use the Linux installation instructions for your WSL distribution (usually Ubuntu)

WSL is detected automatically and will show appropriate Linux-based installation commands.

#### Ubuntu WSL

```bash
# Node.js 18+ via NodeSource (Ubuntu ships an older version by default)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# git
sudo apt install git

# Rust/cargo (for recipe runner)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

#### After Installation

Restart your WSL terminal to ensure all tools are in your PATH:

```bash
# Close and reopen your WSL terminal, then verify:
node --version
npm --version
uv --version
git --version
cargo --version
```

---

### Windows (Native)

> **Improved native support in v0.6.69**: PR #3127 (Phases 1–3) added comprehensive Windows native compatibility. All core amplihack commands now work in native PowerShell without WSL. Some advanced features (fleet orchestration, Docker workflows) still require WSL.

**Package Managers:** winget (recommended) or Chocolatey

#### Using winget (Windows 10 1709+)

```powershell
# Node.js and npm (installed together)
winget install OpenJS.NodeJS

# uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# git
winget install Git.Git
```

#### Using Chocolatey

```powershell
# Install Chocolatey first (if not installed):
# See https://chocolatey.org/install

# Node.js and npm
choco install nodejs

# uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# git
choco install git
```

#### Verify Installation

```powershell
node --version   # Should show v18.x or higher
npm --version    # Should show 9.x or higher
uv --version     # Should show version info
git --version    # Should show 2.x or higher
```

#### Windows Feature Compatibility

| Feature                      | Windows Native                 | WSL  |
| ---------------------------- | ------------------------------ | ---- |
| Core recipe runner           | Full                           | Full |
| Agent orchestration (`/dev`) | Full                           | Full |
| Auto mode (TUI)              | Headless only                  | Full |
| Fleet CLI                    | Not supported                  | Full |
| File locking                 | Full (`msvcrt` fallback)       | Full |
| Keyboard input               | Full (`msvcrt` fallback)       | Full |
| Temp directories             | Full (`tempfile.gettempdir()`) | Full |
| Rust recipe runner           | Full                           | Full |

For WSL setup, follow the Linux instructions in [the Linux section above](#linux).

#### Configure PowerShell UTF-8 Encoding (Required for Windows)

AmplihHack uses Unicode characters (emojis, checkmarks) in output. Windows PowerShell defaults to Code Page 437, which causes these characters to display incorrectly as garbled text (e.g., `âœ…` instead of ✅).

**Fix this by adding UTF-8 configuration to your PowerShell profile:**

```powershell
# Create PowerShell profile if it doesn't exist
if (!(Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
}

# Add UTF-8 configuration
Add-Content $PROFILE @"
# Set console to UTF-8 to properly display Unicode characters (emojis, special characters)
[console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$OutputEncoding = [System.Text.Encoding]::UTF8
"@

# Reload profile
. $PROFILE
```

**To temporarily enable UTF-8 in the current session:**

```powershell
chcp 65001
```

**Verify encoding:**

```powershell
[console]::OutputEncoding
# Should show: BodyName: utf-8, CodePage: 65001
```

---

## Tool-Specific Documentation

### Node.js

**Purpose:** Runtime for Claude CLI

**Official Documentation:** https://nodejs.org/

**Minimum Version:** v18.0.0

**Alternative Installation Methods:**

- **nvm (Node Version Manager):** Recommended for managing multiple Node.js versions
  - macOS/Linux: https://github.com/nvm-sh/nvm
  - Windows: https://github.com/coreybutler/nvm-windows

### npm

**Purpose:** Package manager for installing Claude CLI

**Official Documentation:** https://www.npmjs.com/

**Note:** npm is automatically installed with Node.js

**Verify npm Configuration:**

```bash
npm config get prefix  # Should show global installation directory
```

### uv

**Purpose:** Fast Python package installer and resolver

**Official Documentation:** https://docs.astral.sh/uv/

**Alternative Installation Methods:**

- **pip:** `pip install uv` (not recommended, slower)
- **cargo:** `cargo install uv` (if you have Rust toolchain)

**Configuration:**

```bash
# Optional: Configure uv cache location
export UV_CACHE_DIR=/path/to/cache

# Optional: Use specific Python version
uv python install 3.12
```

### git

**Purpose:** Version control and repository management

**Official Documentation:** https://git-scm.com/

**Minimum Version:** 2.0.0

**Configuration:**

```bash
# Set up your identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify configuration
git config --list
```

---

## Required Tools (After Prerequisites)

### Claude CLI

**Purpose:** Official Claude Code command-line interface

**Documentation:** <https://code.claude.com/docs/en/setup>

**Installation — pick the method for your platform:**

| Platform            | Command                                           |
| ------------------- | ------------------------------------------------- |
| macOS (Homebrew)    | `brew install --cask claude-code`                 |
| macOS / Linux / WSL | `curl -fsSL https://claude.ai/install.sh \| bash` |
| Windows (WinGet)    | `winget install Anthropic.ClaudeCode`             |

> **Note:** The older `npm install -g @anthropic-ai/claude-code` method is
> **deprecated** and no longer recommended. Use the platform-specific
> installers above.

**Verification:**

```bash
claude --version
# Should show version information
```

**Auto-Installation (Opt-In):**

```bash
export AMPLIHACK_AUTO_INSTALL=1
```

When set, the framework will automatically install Claude CLI if missing.
This requires explicit opt-in for security.

---

## Troubleshooting

### "command not found" errors

**Problem:** Tool installed but not in PATH

**Solution:**

**macOS/Linux:**

```bash
# Check if tool is installed
which node npm uv git

# If missing from PATH, add to your shell profile:
# For bash:
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh:
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**

```powershell
# Add to PATH via System Settings:
# 1. Search for "Environment Variables"
# 2. Edit "Path" variable
# 3. Add tool installation directories
# 4. Restart PowerShell
```

### Permission errors during npm install

**Problem:** "permission denied" when installing npm packages globally

**Solution:**

**Option 1: Use a Node version manager (recommended)**

```bash
# Install nvm and use it to install Node.js
# This avoids permission issues
```

**Option 2: Fix npm permissions**

```bash
# Create a directory for global packages
mkdir ~/.npm-global

# Configure npm to use the new directory
npm config set prefix '~/.npm-global'

# Add to PATH
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.profile
source ~/.profile
```

**Option 3: Use sudo (not recommended)**

```bash
sudo npm install -g <package>
# Not recommended due to security implications
```

### uv installation fails

**Problem:** uv installer script fails or not found

**Solution:**

```bash
# Try alternative installation method
pip install uv

# Or if you have Rust:
cargo install uv

# Verify installation
uv --version
```

### Node.js version too old

**Problem:** Node.js version < 18

**Solution:**

**Using nvm:**

```bash
# Install latest LTS version
nvm install --lts
nvm use --lts
```

**Using package manager:**

```bash
# macOS
brew upgrade node

# Ubuntu/Debian - use NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Fedora
sudo dnf install nodejs

# Windows
winget upgrade OpenJS.NodeJS
```

---

## Verification Script

Run this script to verify all prerequisites:

```bash
#!/bin/bash

echo "Checking prerequisites..."
echo

# Check Node.js
if command -v node &> /dev/null; then
    echo "✓ Node.js: $(node --version)"
else
    echo "✗ Node.js: Not found"
fi

# Check npm
if command -v npm &> /dev/null; then
    echo "✓ npm: $(npm --version)"
else
    echo "✗ npm: Not found"
fi

# Check uv
if command -v uv &> /dev/null; then
    echo "✓ uv: $(uv --version)"
else
    echo "✗ uv: Not found"
fi

# Check git
if command -v git &> /dev/null; then
    echo "✓ git: $(git --version)"
else
    echo "✗ git: Not found"
fi

# Check claude
if command -v claude &> /dev/null; then
    echo "✓ claude: $(claude --version)"
else
    echo "✗ claude: Not found"
fi

echo
echo "For installation instructions, see docs/PREREQUISITES.md"
```

---

## Next Steps

After installing all prerequisites:

1. **Verify installation:** Run `amplihack` to check all tools are detected
2. **Configure git:** Set up your name and email
3. **Start using AmplihHack:** See README.md for usage instructions

---

## Support

If you encounter issues not covered in this guide:

1. Check the troubleshooting section above
2. Review the official documentation for each tool
3. Search for existing issues on GitHub
4. Create a new issue with:
   - Your platform and OS version
   - Command output showing the error
   - Steps you've already tried

---

**Last Updated:** 2026-03-17
