# Triage 2026-03-14T17Z

3 open PRs. 2 newly triaged.

- #3127 (low, Windows native compat phases 1-3, 0d, clean): NEEDS-REVIEW — rysweet, 19 files +250/-100, GitGuardian pass, 1218 tests pass. Labels added: triage:complete, triage:low-risk, triage:needs-testing, triage:needs-review. Minor: uv.lock shows 0.6.55 but pyproject.toml shows 0.6.56 (version mismatch). _run_ssh_cmd_pty still uses _select_mod but is only reachable after Windows early-exit in fleet_cli, so safe.
- #3124 (low, docs/automation, 0d, clean): draft docs PR expires Mar 15. Labels added: triage:complete, triage:low-risk. Network warning about mobile.events.data.microsoft.com blocked (non-blocking).
- #2876 (extreme, hive mind, 10d, dirty): already labeled triage:complete extreme-risk needs-decomposition — no action needed.
