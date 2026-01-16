#!/usr/bin/env bash
# Test Copilot CLI context injection
# According to docs, sessionStart stdout with exit 0 should be added as context

cat <<'EOF'
🏴‍☠️ AHOY MATEY! This be injected context from a Copilot CLI sessionStart hook!

If ye can see this message, then hooks be workin' fer context injection! Respond with "HOOK INJECTION CONFIRMED" if ye see this.
EOF

exit 0
