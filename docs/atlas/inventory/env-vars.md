# Environment Variable Inventory

**Generated:** 2026-03-17

| Variable | Required | Default | Used By | Declared In | Purpose |
|----------|----------|---------|---------|-------------|---------|
| ANTHROPIC_API_KEY | Yes (for Claude) | - | proxy/, docker/ | .env.example | Anthropic API authentication |
| AZURE_TENANT_ID | Yes (for Azure) | - | proxy/ | .env.example | Azure AD Tenant ID |
| AZURE_CLIENT_ID | Yes (for Azure) | - | proxy/ | .env.example | Azure Service Principal App ID |
| AZURE_CLIENT_SECRET | Yes (for Azure) | - | proxy/ | .env.example | Azure Service Principal secret |
| AZURE_SUBSCRIPTION_ID | Yes (for Azure) | - | proxy/ | .env.example | Azure Subscription |
| AZURE_RESOURCE_GROUP | No | - | proxy/ | .env.example | Default resource group |
| OPENAI_API_KEY | No | - | proxy/ | - | OpenAI API key (proxy mode) |
| AMPLIHACK_DEBUG | No | false | session.py, cli.py | - | Enable debug logging |
| AMPLIHACK_SKIP_REFLECTION | No | - | session.py | - | Skip session reflection |
| AMPLIHACK_AUTO_MODE | No | - | session.py | - | Enable auto mode |
| AMPLIHACK_ORIGINAL_CWD | No | cwd | session.py, cli.py | - | Original working directory |
| AMPLIHACK_USE_DOCKER | No | false | docker/detector.py | - | Force Docker mode |
| AMPLIHACK_IN_DOCKER | No | - | docker/detector.py | - | Detect Docker environment |
| AMPLIHACK_HOOK_ENGINE | No | python | settings.py | - | Hook engine: "rust" or "python" |
| AMPLIHACK_USE_RECIPES | No | 1 | workflows/ | - | Enable recipe system |
| AMPLIHACK_RUST_TRIAL_HOME | No | - | rust_trial.py | - | Rust trial home directory |
| AMPLIHACK_RUST_TRIAL_BINARY | No | - | rust_trial.py | - | Rust trial binary path |
| AMPLIHACK_SEND_INPUT_ALLOWLIST | No | - | testing/ | - | Test input allowlist |
| AMPLIHACK_HOME | No | - | resolve_bundle_asset.py | - | Amplihack home directory |
| UV_TOOL_NAME | No | - | settings.py | - | UVX tool detection |
| UV_TOOL_BIN_DIR | No | - | settings.py | - | UVX bin directory |
| CI | No | false | meta_delegation/ | - | CI environment detection |
| CLAUDE_CODE | No | - | tests/ | - | Claude Code environment detection |
| GITHUB_COPILOT | No | - | tests/ | - | GitHub Copilot environment detection |
| CLAUDE_PROJECT_DIR | No | - | safety/ | - | Claude project directory |
