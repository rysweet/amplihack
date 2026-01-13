---
skill:
  name: azure-networking
  description: Azure networking - VNets, NSGs, Private Link
---

# Azure Networking

## Components
- **VNet**: Virtual network isolation
- **Subnet**: Network segmentation
- **NSG**: Network security groups (firewall rules)
- **Private Link**: Private endpoints for services

## Quick Reference
```bash
# Create VNet
az network vnet create --name myvnet --resource-group rg --address-prefix 10.0.0.0/16

# Create subnet
az network vnet subnet create --vnet-name myvnet --name mysubnet --address-prefix 10.0.1.0/24 -g rg
```
