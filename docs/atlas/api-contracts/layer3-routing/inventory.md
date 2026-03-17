# Route Inventory

**Generated:** 2026-03-17

## CLI Commands

| Command | Subcommand | Handler | Passthrough | Description |
|---------|-----------|---------|-------------|-------------|
| (default) | - | ClaudeLauncher | Yes | Launch Claude Code |
| launch | - | ClaudeLauncher | Yes | Launch Claude Code |
| claude | - | ClaudeLauncher | Yes | Launch Claude Code |
| copilot | - | ClaudeLauncher | Yes | Launch GitHub Copilot |
| codex | - | ClaudeLauncher | Yes | Launch OpenAI Codex |
| amplifier | - | ClaudeLauncher | Yes | Launch Microsoft Amplifier |
| install | - | _local_install | No | Install to ~/.claude |
| uninstall | - | uninstall | No | Remove from ~/.claude |
| plugin | install | plugin_install_command | No | Install plugin |
| plugin | uninstall | plugin_uninstall_command | No | Uninstall plugin |
| plugin | verify | plugin_verify_command | No | Verify plugin |
| memory | evaluate | cli_evaluate | No | Evaluate memory |
| memory | visualize | cli_visualize | No | Visualize memory |
| memory | cleanup | cli_cleanup | No | Clean memory |
| memory | config | cli_config | No | Memory config |
| health | - | run_checks | No | Health check |
| version | - | print version | No | Show version |

## HTTP Routes (Proxy)

| Method | Path | Handler File | Auth | Request DTO | Response DTO | Middleware |
|--------|------|-------------|------|------------|--------------|-----------|
| GET | / | integrated_proxy.py:1223 | None | - | JSON | http middleware |
| GET | /health | integrated_proxy.py:238 | None | - | JSON | http middleware |
| POST | /v1/messages | integrated_proxy.py:689 | API Key | Messages request | Messages response (streaming) | http middleware |
| POST | /v1/messages/count_tokens | integrated_proxy.py:1152 | API Key | Count request | Token count | http middleware |
| GET | /performance/metrics | integrated_proxy.py:1228 | None | - | JSON | http middleware |
| GET | /performance/cache/status | integrated_proxy.py:1257 | None | - | JSON | http middleware |
| GET | /performance/cache/clear | integrated_proxy.py:1286 | None | - | JSON | http middleware |
| GET | /performance/benchmark | integrated_proxy.py:1321 | None | - | JSON | http middleware |
| GET | /azure/status | integrated_proxy.py:275 | None | - | JSON | http middleware |
| GET | /azure/test-error-handling | integrated_proxy.py:1363 | None | - | JSON | http middleware |
| GET | /stream/logs | log_streaming.py:116 | None | - | SSE stream | - |
