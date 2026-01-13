---
skill:
  name: azure-functions
  description: Azure Functions - serverless compute
---

# Azure Functions

## Trigger Types
| Trigger | Use Case |
|---------|----------|
| HTTP | REST APIs |
| Timer | Scheduled jobs |
| Blob | File processing |
| Queue | Message processing |
| Event Grid | Event-driven |

## Quick Reference

```bash
# Create function app
az functionapp create --name myfunc --resource-group rg --storage-account mystorage --consumption-plan-location eastus --runtime python

# Deploy
func azure functionapp publish myfunc
```

## Best Practices
- Use Durable Functions for orchestration
- Configure proper timeout values
- Use managed identity
- Monitor with Application Insights
