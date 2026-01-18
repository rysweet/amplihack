# Authentication Setup

Complete guide to setting up authentication for Azure DevOps CLI tools.

## Prerequisites

- Azure CLI installed
- Azure account with DevOps access
- Network access to dev.azure.com

## Step 1: Install Azure CLI

### macOS

```bash
brew install azure-cli
```

### Windows

```powershell
winget install Microsoft.AzureCLI
```

### Linux (Ubuntu/Debian)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

Verify installation:

```bash
az --version
```

## Step 2: Install DevOps Extension

```bash
az extension add --name azure-devops
```

Verify extension:

```bash
az extension list --output table | grep azure-devops
```

## Step 3: Login to Azure

```bash
az login
```

This opens your browser for interactive login. After successful login, you'll see your subscriptions listed.

### Alternative: Service Principal Login

For automation/CI:

```bash
az login --service-principal \
  --username APP_ID \
  --password PASSWORD \
  --tenant TENANT_ID
```

## Step 4: Configure Defaults

Set default organization and project:

```bash
az devops configure --defaults \
  organization=https://dev.azure.com/YOUR_ORG \
  project=YOUR_PROJECT
```

View current configuration:

```bash
az devops configure --list
```

## Step 5: Verify Access

Use the auth_check tool:

```bash
python .claude/scenarios/az-devops-tools/auth_check.py
```

Expected output:

```
✓ Azure CLI installed
✓ Logged in
✓ DevOps extension installed
✓ Organization configured
✓ Project configured
✓ Organization accessible
✓ Project accessible
```

## Auto-Fix Common Issues

```bash
python .claude/scenarios/az-devops-tools/auth_check.py --auto-fix
```

This attempts to:

- Install DevOps extension if missing
- Guide you through missing configuration

## Configuration Priority

Tools load configuration in this order (highest to lowest):

1. Command-line arguments (`--org`, `--project`)
2. Environment variables
3. az devops configure defaults
4. Config file (if specified)

### Environment Variables

```bash
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/YOUR_ORG"
export AZURE_DEVOPS_PROJECT="YOUR_PROJECT"
```

Add to your `~/.bashrc` or `~/.zshrc` for persistence.

## Troubleshooting

### "az: command not found"

Azure CLI not installed or not in PATH.

- Reinstall Azure CLI
- Check PATH: `echo $PATH`
- Restart shell

### "ERROR: az devops: 'devops' is not in the 'az' command group"

DevOps extension not installed.

```bash
az extension add --name azure-devops
```

### "Please run 'az login' to setup account"

Not logged in to Azure.

```bash
az login
```

### "TF401019: The Git repository with name or identifier does not exist"

Wrong organization or project.

- Verify org URL format: `https://dev.azure.com/ORG_NAME`
- Check project name (case-sensitive)
- Verify access permissions

### "Authentication failed"

Token expired or insufficient permissions.

```bash
# Re-login
az logout
az login

# Verify permissions in Azure DevOps web portal
```

## Security Best Practices

- Use service principals for automation
- Rotate credentials regularly
- Don't commit credentials to git
- Use Azure Key Vault for production
- Enable MFA on your Azure account

## See Also

- [Azure CLI Installation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure DevOps Extension](https://learn.microsoft.com/en-us/cli/azure/devops)
- [Service Principal Auth](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)
