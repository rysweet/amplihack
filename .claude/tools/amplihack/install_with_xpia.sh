#!/bin/bash
# Enhanced install script with XPIA security hook integration
# Fixes Issue #137: XPIA hooks not configured during installation

AMPLIHACK_INSTALL_LOCATION=${AMPLIHACK_INSTALL_LOCATION:-https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Python3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not found. Please install Python3."
        return 1
    fi

    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_status "Found Python $PYTHON_VERSION"
    return 0
}

# Function to run Python-based hook merge
merge_xpia_hooks() {
    print_status "Integrating XPIA security hooks..."

    # Use the hook merge utility from the installed amplihack
    HOOK_MERGE_SCRIPT="$HOME/.claude/tmpamplihack/src/amplihack/utils/hook_merge_utility.py"

    if [ ! -f "$HOOK_MERGE_SCRIPT" ]; then
        print_error "Hook merge utility not found: $HOOK_MERGE_SCRIPT"
        return 1
    fi

    # Run the hook merge utility
    cd "$HOME/.claude"
    python3 "$HOOK_MERGE_SCRIPT" --settings "$HOME/.claude/settings.json"
    MERGE_RESULT=$?

    if [ $MERGE_RESULT -eq 0 ]; then
        print_success "XPIA security hooks integrated successfully"
        return 0
    else
        print_error "Failed to integrate XPIA security hooks (exit code: $MERGE_RESULT)"
        return 1
    fi
}

# Function to run XPIA health check
run_xpia_health_check() {
    print_status "Running XPIA security health check..."

    HEALTH_CHECK_SCRIPT="$HOME/.claude/tmpamplihack/src/amplihack/security/xpia_health.py"

    if [ ! -f "$HEALTH_CHECK_SCRIPT" ]; then
        print_warning "XPIA health check script not found, skipping health validation"
        return 0
    fi

    cd "$HOME/.claude"
    python3 "$HEALTH_CHECK_SCRIPT" --verbose
    HEALTH_RESULT=$?

    case $HEALTH_RESULT in
        0)
            print_success "XPIA security system is healthy"
            ;;
        1)
            print_warning "XPIA security system is partially functional"
            ;;
        2)
            print_error "XPIA security system is unhealthy"
            ;;
        *)
            print_warning "XPIA health check returned unexpected result: $HEALTH_RESULT"
            ;;
    esac

    return $HEALTH_RESULT
}

# Main installation process
main() {
    print_status "Starting amplihack installation with XPIA security integration"
    print_status "Repository: $AMPLIHACK_INSTALL_LOCATION"

    # Check prerequisites
    if ! check_python; then
        exit 1
    fi

    # Clean up any existing temp directory
    if [ -d "./tmpamplihack" ]; then
        print_error "./tmpamplihack directory already exists. Please remove it and try again."
        exit 1
    fi

    # Clone repository
    print_status "Cloning amplihack repository..."
    git clone $AMPLIHACK_INSTALL_LOCATION ./tmpamplihack

    if [ $? -ne 0 ]; then
        print_error "Failed to clone repository"
        exit 1
    fi

    # Create backup of existing settings.json
    if [ -f "$HOME/.claude/settings.json" ]; then
        BACKUP_FILE="$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
        print_status "Backing up existing settings.json to $BACKUP_FILE"
        cp "$HOME/.claude/settings.json" "$BACKUP_FILE"

        if [ $? -ne 0 ]; then
            print_error "Failed to backup existing settings.json"
            rm -rf ./tmpamplihack
            exit 1
        fi
        print_success "Backup created successfully"
    else
        print_status "No existing settings.json found, fresh installation"
    fi

    # Install amplihack files
    print_status "Installing amplihack files to ~/.claude..."
    cp -r ./tmpamplihack/.claude/* "$HOME/.claude/" 2>/dev/null || {
        # Create .claude directory if it doesn't exist
        mkdir -p "$HOME/.claude"
        cp -r ./tmpamplihack/.claude/* "$HOME/.claude/"
    }

    if [ $? -ne 0 ]; then
        print_error "Failed to copy files to ~/.claude"
        rm -rf ./tmpamplihack
        exit 1
    fi

    # Copy source files for hook merge utility
    print_status "Installing amplihack source modules..."
    mkdir -p "$HOME/.claude/tmpamplihack"
    cp -r ./tmpamplihack/src "$HOME/.claude/tmpamplihack/"
    cp -r ./tmpamplihack/Specs "$HOME/.claude/tmpamplihack/"

    # Merge XPIA hooks using Python utility
    if ! merge_xpia_hooks; then
        print_error "XPIA hook integration failed"

        # Try to restore backup if it exists
        if [ -f "$BACKUP_FILE" ]; then
            print_status "Attempting to restore backup settings..."
            cp "$BACKUP_FILE" "$HOME/.claude/settings.json"
            if [ $? -eq 0 ]; then
                print_success "Backup restored successfully"
            else
                print_error "Failed to restore backup"
            fi
        fi

        # Clean up
        rm -rf ./tmpamplihack
        rm -rf "$HOME/.claude/tmpamplihack"
        exit 1
    fi

    # Update traditional amplihack hook paths (for backward compatibility)
    print_status "Updating amplihack hook paths for global installation..."
    if [ -f "$HOME/.claude/settings.json" ]; then
        # Update amplihack hook paths to absolute paths
        sed -i.tmp \
            -e 's|"\.claude/tools/amplihack/hooks/|"'"$HOME"'/.claude/tools/amplihack/hooks/|g' \
            -e 's|"~/.claude/tools/amplihack/hooks/|"'"$HOME"'/.claude/tools/amplihack/hooks/|g' \
            "$HOME/.claude/settings.json"

        if [ $? -eq 0 ]; then
            rm "$HOME/.claude/settings.json.tmp" 2>/dev/null
            print_success "Amplihack hook paths updated successfully"
        else
            print_warning "Failed to update amplihack hook paths"
            # Restore from temp if available
            if [ -f "$HOME/.claude/settings.json.tmp" ]; then
                mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"
            fi
        fi
    fi

    # Verify hook files exist
    print_status "Verifying hook files..."
    MISSING_HOOKS=0

    # Check amplihack hooks
    for hook in "session_start.py" "stop.py" "post_tool_use.py" "pre_compact.py"; do
        if [ -f "$HOME/.claude/tools/amplihack/hooks/$hook" ]; then
            print_success "Amplihack $hook found"
        else
            print_warning "Amplihack $hook missing"
            MISSING_HOOKS=$((MISSING_HOOKS + 1))
        fi
    done

    # Check XPIA hooks
    for hook in "session_start.py" "post_tool_use.py" "pre_tool_use.py"; do
        if [ -f "$HOME/.claude/tools/xpia/hooks/$hook" ]; then
            print_success "XPIA $hook found"
        else
            print_warning "XPIA $hook missing"
            MISSING_HOOKS=$((MISSING_HOOKS + 1))
        fi
    done

    if [ $MISSING_HOOKS -eq 0 ]; then
        print_success "All hook files verified"
    else
        print_warning "$MISSING_HOOKS hook files missing"
    fi

    # Run XPIA health check
    run_xpia_health_check
    HEALTH_EXIT_CODE=$?

    # Clean up temporary files
    rm -rf ./tmpamplihack
    rm -rf "$HOME/.claude/tmpamplihack"

    # Final status report
    echo ""
    print_success "Amplihack installation completed successfully!"
    print_status "Features installed:"
    echo "  ✅ Amplihack core tools and hooks"
    echo "  ✅ XPIA security defense system"
    echo "  ✅ Smart hook configuration merging"

    if [ -f "$BACKUP_FILE" ]; then
        print_status "Your previous settings.json has been backed up to:"
        echo "  $BACKUP_FILE"
    fi

    echo ""
    print_status "Next steps:"
    echo "  1. Restart Claude Code to activate the hooks"
    echo "  2. Run 'amplihack xpia health' to verify XPIA security status"
    echo "  3. Check ~/.claude/logs/xpia/ for security monitoring logs"

    # Exit with health check result
    exit $HEALTH_EXIT_CODE
}

# Run main function
main "$@"
