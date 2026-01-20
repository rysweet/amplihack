"""Hook verification for amplihack.

Philosophy:
- Single responsibility: Verify that hook files exist
- Self-contained: All hook verification logic in one place
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    verify_hooks: Verify that all hook files exist
"""

import os

# Import constants from package root
from . import CLAUDE_DIR, HOOK_CONFIGS


def verify_hooks():
    """Verify that all hook files exist."""
    all_exist = True

    for hook_system, hooks in HOOK_CONFIGS.items():
        hooks_dir = os.path.join(CLAUDE_DIR, "tools", hook_system, "hooks")

        # Skip XPIA if directory doesn't exist (optional feature)
        if hook_system == "xpia" and not os.path.exists(hooks_dir):
            print("  ℹ️  XPIA security hooks not installed (optional feature)")
            continue

        # Print header with appropriate icon
        icon = "🔒" if hook_system == "xpia" else "📋"
        print(f"  {icon} {hook_system.capitalize()} hooks:")

        system_all_exist = True
        for hook_info in hooks:
            hook_file = hook_info["file"]
            hook_path = os.path.join(hooks_dir, hook_file)
            if os.path.exists(hook_path):
                print(f"    ✅ {hook_file} found")
            else:
                print(f"    ❌ {hook_file} missing")
                system_all_exist = False

        # Only mark all_exist as False if amplihack hooks are missing
        if hook_system == "amplihack" and not system_all_exist:
            all_exist = False

        # Additional message for XPIA if all hooks found
        if hook_system == "xpia" and system_all_exist:
            print("  🔒 XPIA security hooks configured")

    return all_exist


__all__ = ["verify_hooks"]
