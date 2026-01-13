---
skill:
  name: azure-identity
  description: Azure identity - Entra ID, managed identities, MSAL
---

# Azure Identity

## Authentication Methods
| Method | Use Case |
|--------|----------|
| Managed Identity | Azure resources |
| Service Principal | CI/CD, automation |
| User credentials | Development |
| DefaultAzureCredential | Auto-selects best method |

## Quick Reference
```python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
```

```bash
# Create service principal
az ad sp create-for-rbac --name myapp --role contributor
```
