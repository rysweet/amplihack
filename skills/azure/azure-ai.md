---
skill:
  name: azure-ai
  description: Azure AI services - Cognitive Services, Azure OpenAI, AI Search
---

# Azure AI Services

## Services Overview

| Service | Use Case |
|---------|----------|
| Azure OpenAI | GPT models, embeddings, DALL-E |
| Cognitive Services | Vision, Speech, Language, Decision |
| Azure AI Search | Vector search, semantic ranking |
| Azure ML | Custom model training/deployment |

## Quick Reference

```bash
# Deploy Azure OpenAI
az cognitiveservices account create --name myopenai --resource-group rg --kind OpenAI --sku S0 --location eastus

# Create AI Search
az search service create --name mysearch --resource-group rg --sku basic
```

## Best Practices
- Use managed identity for auth
- Implement retry with exponential backoff
- Monitor token usage and costs
- Use content filtering for production
