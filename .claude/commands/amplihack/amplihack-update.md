---
name: amplihack-update
version: 1.0.0
description: Update the amplihack Rust binary and reinstall the framework assets in one step
triggers:
  - "Update amplihack"
  - "Refresh amplihack"
  - "Upgrade amplihack"
  - "/amplihack-update"
---

# Update amplihack

This command brings the local amplihack installation fully up to date in one shot:

1. `amplihack update` — downloads and installs the latest released `amplihack` Rust binary (self-update).
2. `amplihack install` — re-stages the framework assets (agents, commands, tools, skills, recipes, and the `amplifier-bundle/` tree) so the freshly-updated binary is paired with matching on-disk assets.

Step 2 is mandatory after step 1: a new binary version may ship updated recipes (e.g. `smart-orchestrator.yaml`) or new bundled tools that the old install dir doesn't contain. Skipping the reinstall is the root cause of "I updated but the fix isn't there" reports.

## When this is invoked

Run both commands sequentially. If `amplihack update` exits non-zero, stop and surface the error — do not run the install step against a half-updated binary.

```bash
set -euo pipefail
amplihack update
amplihack install
```

After completion, print:
- The new version (`amplihack --version`)
- A short note that the framework assets at `~/.amplihack/` have been refreshed
- A reminder that any open agent sessions should be restarted to pick up the new binary and assets
