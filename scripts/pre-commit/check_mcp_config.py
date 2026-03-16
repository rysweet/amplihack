#!/usr/bin/env python3
"""MCP config validator for CI compatibility.

Validates .mcp.json to ensure no MCP servers that require infrastructure
unavailable in GitHub Actions (e.g. Docker daemon) are configured without
being explicitly disabled.

Root cause: PR #3136 had `docker-mcp` in .mcp.json without `disabled: true`,
causing the Repo Guardian workflow to fail with:
  ##[error]ERR_API: MCP server(s) failed to launch: docker-mcp

See .claude/skills/gh-aw-adoption/reference.md for full details.

Usage:
    python scripts/pre-commit/check_mcp_config.py .mcp.json

Exit Codes:
    0: No issues found
    1: CI-incompatible MCP servers detected
"""

import json
import sys
from pathlib import Path

# MCP servers known to require Docker daemon or other CI-unavailable resources.
# These fail silently-but-loudly in the AWF container: the agent task succeeds
# but the "Parse agent logs" step reports ERR_API and marks the job as failed.
CI_INCOMPATIBLE_SERVERS = {
    "docker-mcp": "requires Docker daemon (unavailable inside AWF container)",
}


def check_mcp_config(path: Path) -> list[str]:
    """Check .mcp.json for CI-incompatible MCP servers.

    Returns a list of error messages (empty if all OK).
    """
    errors: list[str] = []

    if not path.exists():
        return errors

    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return errors

    mcp_servers = config.get("mcpServers", {})
    for server_name, reason in CI_INCOMPATIBLE_SERVERS.items():
        if server_name not in mcp_servers:
            continue
        server_cfg = mcp_servers[server_name]
        if not server_cfg.get("disabled", False):
            errors.append(
                f"{path}: MCP server '{server_name}' is enabled but CI-incompatible "
                f'({reason}). Add `"disabled": true` to disable it for CI, or '
                f"remove it entirely."
            )

    return errors


def main() -> int:
    files = sys.argv[1:] if len(sys.argv) > 1 else [".mcp.json"]
    all_errors: list[str] = []

    for file_arg in files:
        path = Path(file_arg)
        all_errors.extend(check_mcp_config(path))

    if all_errors:
        print("MCP config CI compatibility check FAILED:", file=sys.stderr)
        for error in all_errors:
            print(f"  ✗ {error}", file=sys.stderr)
        print(
            '\nFix: add `"disabled": true` to the server config or remove it.\n'
            "See .claude/skills/gh-aw-adoption/reference.md for details.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
