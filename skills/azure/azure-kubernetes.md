---
skill:
  name: azure-kubernetes
  description: Azure Kubernetes Service - AKS deployment and management
---

# Azure Kubernetes Service (AKS)

## Key Concepts
- Node pools (system vs user)
- Cluster autoscaler
- Azure CNI vs Kubenet
- Managed identity integration

## Quick Reference

```bash
# Create AKS cluster
az aks create --name myaks --resource-group rg --node-count 3 --enable-managed-identity

# Get credentials
az aks get-credentials --name myaks --resource-group rg

# Scale node pool
az aks nodepool scale --cluster-name myaks --name nodepool1 --node-count 5 -g rg
```

## Production Checklist
- [ ] Enable Azure Policy
- [ ] Configure pod security policies
- [ ] Set up monitoring (Container Insights)
- [ ] Configure network policies
- [ ] Enable cluster autoscaler
