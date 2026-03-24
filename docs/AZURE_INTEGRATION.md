# Azure OpenAI Integration

How to connect amplihack to an Azure OpenAI deployment.

## Contents

- [Quick start](#quick-start)
- [Configuration reference](#configuration-reference)
- [Model selection](#model-selection)
- [Persist credentials](#persist-credentials)
- [Advanced setups](#advanced-setups)
- [Troubleshooting](#troubleshooting)

---

## Quick start

```bash
# 1. Export your Azure credentials
export ANTHROPIC_API_KEY="<your-azure-openai-resource-key>"
export ANTHROPIC_BASE_URL="https://<resource-name>.openai.azure.com"
export AZURE_OPENAI_API_VERSION="2024-10-21"

# 2. Launch
amplihack launch
```

Claude Code connects directly to the Azure endpoint. No proxy or intermediary is required.

---

## Configuration reference

### Required environment variables

| Variable                   | Example value                     | Description                                                               |
| -------------------------- | --------------------------------- | ------------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`        | `abc123...`                       | Azure OpenAI resource key from **Keys and Endpoint** in the Azure portal. |
| `ANTHROPIC_BASE_URL`       | `https://my-org.openai.azure.com` | Base URL of the Azure resource. No deployment path, no trailing slash.    |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21`                      | API version string supported by your deployment.                          |

### Locating your Azure credentials

1. Open the [Azure portal](https://portal.azure.com) and navigate to your Azure OpenAI resource.
2. Select **Keys and Endpoint** from the left navigation panel.
3. Copy **KEY 1** or **KEY 2** — this is your `ANTHROPIC_API_KEY`.
4. Copy the **Endpoint** — this is your `ANTHROPIC_BASE_URL`. It takes the form `https://<resource-name>.openai.azure.com`.

### Supported API versions

Use `2024-10-21` unless your deployment requires a different version. See the
[Azure OpenAI API release notes](https://learn.microsoft.com/en-us/azure/ai-services/openai/whats-new)
for the full list of available versions.

---

## Model selection

Specify which model (deployment) to use via the `--model` flag:

```bash
amplihack launch -- --model claude-3-5-sonnet-20241022
```

The model name you pass must match the **Deployment name** configured in Azure AI Studio. If the names do not match, Claude Code returns a `ResourceNotFound` error.

To set a default model for all sessions without passing `--model` every time, set `AMPLIHACK_DEFAULT_MODEL`:

```bash
export AMPLIHACK_DEFAULT_MODEL="claude-3-5-sonnet-20241022"
amplihack launch
```

---

## Persist credentials

### Project-local credentials file

Create `.azure.env` in the project root and add it to `.gitignore`:

```bash
# .azure.env — never commit this file
export ANTHROPIC_API_KEY="abc123..."
export ANTHROPIC_BASE_URL="https://my-org.openai.azure.com"
export AZURE_OPENAI_API_VERSION="2024-10-21"
export AMPLIHACK_DEFAULT_MODEL="claude-3-5-sonnet-20241022"
```

```gitignore
# .gitignore
.azure.env
```

Source it before launching:

```bash
source .azure.env && amplihack launch
```

### Shell profile (machine-wide)

Add the exports to `~/.bashrc` or `~/.zshrc` for all sessions on the machine:

```bash
echo 'export ANTHROPIC_API_KEY="abc123..."' >> ~/.bashrc
echo 'export ANTHROPIC_BASE_URL="https://my-org.openai.azure.com"' >> ~/.bashrc
echo 'export AZURE_OPENAI_API_VERSION="2024-10-21"' >> ~/.bashrc
```

---

## Advanced setups

### Multiple Azure resources

Use shell functions to switch between environments:

```bash
# ~/.bashrc
azure-prod() {
  export ANTHROPIC_API_KEY="<prod-key>"
  export ANTHROPIC_BASE_URL="https://prod.openai.azure.com"
  export AZURE_OPENAI_API_VERSION="2024-10-21"
}

azure-dev() {
  export ANTHROPIC_API_KEY="<dev-key>"
  export ANTHROPIC_BASE_URL="https://dev.openai.azure.com"
  export AZURE_OPENAI_API_VERSION="2024-10-21"
}
```

```bash
azure-prod && amplihack launch
```

### CI / non-interactive environments

In CI pipelines, inject credentials as masked environment variables. Then launch with `AMPLIHACK_NONINTERACTIVE=1` to skip prompts:

```yaml
# GitHub Actions example
env:
  ANTHROPIC_API_KEY: ${{ secrets.AZURE_OPENAI_KEY }}
  ANTHROPIC_BASE_URL: ${{ secrets.AZURE_OPENAI_BASE_URL }}
  AZURE_OPENAI_API_VERSION: "2024-10-21"
  AMPLIHACK_NONINTERACTIVE: "1"

steps:
  - run: amplihack launch -- -p "Run the test suite and report failures"
```

---

## Troubleshooting

### `AuthenticationError` / `401`

`ANTHROPIC_API_KEY` contains the wrong key. Regenerate it from the Azure portal and re-export it.

### `ResourceNotFound` / `404`

One of:

- `ANTHROPIC_BASE_URL` contains the deployment path. Strip everything after the hostname:

  ```
  # Correct
  https://my-org.openai.azure.com

  # Wrong
  https://my-org.openai.azure.com/openai/deployments/claude-model
  ```

- The deployment name passed to `--model` does not match the name in Azure AI Studio.

### `InvalidApiVersion` / `400`

`AZURE_OPENAI_API_VERSION` is not supported by your deployment. Update to a version listed in the Azure OpenAI documentation.

### `claude: command not found` or `amplihack: command not found`

See [Prerequisites](./PREREQUISITES.md) for installation instructions.

---

## See Also

- [Configure Azure OpenAI (how-to guide)](./howto/configure-azure-openai.md)
- [Migrate from the built-in proxy](./howto/migrate-from-proxy.md)
- [launch flags reference](./reference/cli.md#launch)
- [Prerequisites](./PREREQUISITES.md)
