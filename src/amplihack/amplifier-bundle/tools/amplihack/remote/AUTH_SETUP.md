# Azure Service Principal Authentication Setup

Complete guide for setting up Azure Service Principal authentication for remote execution.

## Quick Start

```python
from claude.tools.amplihack.remote.auth import get_azure_auth

# Get authenticated credential
credential, subscription_id, resource_group = get_azure_auth(debug=True)

# Use with Azure SDK
from azure.mgmt.compute import ComputeManagementClient
compute_client = ComputeManagementClient(credential, subscription_id)
```

## Setup Steps

### 1. Create Service Principal

```bash
# Create SP with Contributor role on subscription
az ad sp create-for-rbac \
  --name "amplihack-remote-exec" \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Output will look like:
# {
#   "appId": "f297fcb0-...",           # AZURE_CLIENT_ID
#   "displayName": "amplihack-remote-exec",
#   "password": "4Jq8Q~...",            # AZURE_CLIENT_SECRET
#   "tenant": "3cd87a41-..."            # AZURE_TENANT_ID
# }
```

### 2. Get Subscription ID

```bash
az account show --query id -o tsv
# Output: 9b00bc5e-9abc-45de-9958-02a9d9277b16
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
AZURE_TENANT_ID=your-tenant-id-from-step-2
AZURE_CLIENT_ID=your-client-id-from-step-2
AZURE_CLIENT_SECRET=your-client-secret-from-step-2
AZURE_SUBSCRIPTION_ID=your-subscription-id
```

### 4. Test Authentication

```bash
cd .claude/tools/amplihack/remote
python3 test_auth.py
```

Or test with a real API call:

```python
from claude.tools.amplihack.remote.auth import get_azure_auth
from azure.mgmt.resource import ResourceManagementClient

credential, sub_id, _ = get_azure_auth()
client = ResourceManagementClient(credential, sub_id)

# List resource groups
for rg in client.resource_groups.list():
    print(f"  - {rg.name} ({rg.location})")
```

## Architecture

### Files Created

```
.
├── .env                              # Credentials (git-ignored)
├── .env.example                      # Template with instructions
└── .claude/tools/amplihack/remote/
    ├── auth.py                       # Authentication module
    ├── test_auth.py                  # Test suite
    └── AUTH_SETUP.md                 # This file
```

### Module Structure

```python
# Core classes
AzureCredentials         # Dataclass for credential storage
AzureAuthenticator       # Main authentication handler

# Convenience function
get_azure_auth()         # One-line authentication
```

### Credential Search Order

1. Explicit env_file parameter
2. Environment variables (already set)
3. `.env` in current directory
4. `.env` in project root

### Debug Mode

Enable debug logging to troubleshoot authentication:

```python
credential, sub_id, rg = get_azure_auth(debug=True)

# Output:
# [DEBUG] Found .env file: /path/to/.env
# [DEBUG] Loading environment from: /path/to/.env
# [DEBUG] Tenant ID: ✓
# [DEBUG] Client ID: ✓
# [DEBUG] Client Secret: ✓
# [DEBUG] Subscription ID: ✓
# [DEBUG] Resource Group: (not set)
# [DEBUG] Creating ClientSecretCredential
```

## Security Best Practices

### Git Protection

The `.gitignore` already covers:

- `.env` and all `.env*` files
- `*.local` files
- `**/credentials.json` files

Verify with:

```bash
git check-ignore -v .env
# Output: .gitignore:10:.env	.env
```

### Secret Management

1. **Never commit credentials** - `.env` is in `.gitignore`
2. **Rotate regularly** - Change secrets every 90 days
3. **Minimum permissions** - Use Contributor on specific resource group only
4. **Backup encrypted** - If backing up `.env`, encrypt it first
5. **Revoke unused** - Delete Service Principals when no longer needed

### Production Deployment

For production, use Azure Managed Identity instead of Service Principals:

```python
from azure.identity import DefaultAzureCredential

# Automatically uses Managed Identity when running on Azure
credential = DefaultAzureCredential()
```

## Integration with Remote Execution

The auth module is designed to work seamlessly with the remote execution system:

```python
from claude.tools.amplihack.remote.auth import get_azure_auth
from claude.tools.amplihack.remote.executor import RemoteExecutor

# Authenticate
credential, sub_id, rg = get_azure_auth()

# Execute remotely
executor = RemoteExecutor(
    credential=credential,
    subscription_id=sub_id,
    resource_group=rg or "default-rg"
)

result = executor.run_command("python3 --version")
print(result.stdout)
```

## Troubleshooting

### Missing Credentials

```
ValueError: Missing required credentials: tenant_id, client_id
```

**Solution**: Ensure `.env` file exists and contains all required variables.

### Authentication Failed

```
ClientAuthenticationError: Authentication failed
```

**Solutions**:

1. Verify credentials are correct (check Azure Portal)
2. Ensure Service Principal hasn't expired
3. Check Service Principal has Contributor role
4. Verify subscription ID is correct

### Module Not Found

```
ModuleNotFoundError: No module named 'azure'
```

**Solution**: Install Azure SDK:

```bash
uv pip install azure-identity azure-mgmt-compute azure-mgmt-network azure-mgmt-resource
```

### .env Not Found

```
# Debug output shows: "No .env file found"
```

**Solutions**:

1. Create `.env` from template: `cp .env.example .env`
2. Run from project root directory
3. Pass explicit path: `get_azure_auth(env_file=Path("/path/to/.env"))`

## Testing

### Unit Tests

```bash
cd .claude/tools/amplihack/remote
python3 test_auth.py
```

### Integration Test

```bash
python3 << 'EOF'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / '.claude'))
from tools.amplihack.remote.auth import get_azure_auth
from azure.mgmt.resource import ResourceManagementClient

credential, sub_id, _ = get_azure_auth(debug=True)
client = ResourceManagementClient(credential, sub_id)
rgs = list(client.resource_groups.list())
print(f"✓ Successfully authenticated! Found {len(rgs)} resource groups.")
EOF
```

## Reference

### Environment Variables

| Variable                | Required | Description                      |
| ----------------------- | -------- | -------------------------------- |
| `AZURE_TENANT_ID`       | Yes      | Azure AD tenant (directory) ID   |
| `AZURE_CLIENT_ID`       | Yes      | Service Principal application ID |
| `AZURE_CLIENT_SECRET`   | Yes      | Service Principal secret value   |
| `AZURE_SUBSCRIPTION_ID` | Yes      | Target Azure subscription ID     |
| `AZURE_RESOURCE_GROUP`  | No       | Default resource group name      |

### API Documentation

- **AzureCredentials**: Dataclass holding credentials
  - `tenant_id: str` - Tenant ID
  - `client_id: str` - Client ID
  - `client_secret: str` - Client secret
  - `subscription_id: str` - Subscription ID
  - `resource_group: Optional[str]` - Resource group

- **AzureAuthenticator**: Main authentication class
  - `__init__(env_file, debug)` - Initialize authenticator
  - `get_credentials()` - Get credentials object
  - `get_credential()` - Get Azure SDK credential
  - `get_subscription_id()` - Get subscription ID
  - `get_resource_group()` - Get resource group name

- **get_azure_auth(env_file, debug)**: Convenience function
  - Returns: `(credential, subscription_id, resource_group)`

## Next Steps

1. ✓ Authentication module implemented
2. ✓ Tests passing
3. ✓ Documentation complete
4. → Integrate with `executor.py`
5. → Integrate with `orchestrator.py`
6. → End-to-end remote execution testing
