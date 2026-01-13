---
skill:
  name: azure-storage
  description: Azure Storage - blobs, files, queues, tables
---

# Azure Storage

## Service Types
- **Blob**: Unstructured data (files, images)
- **Files**: SMB file shares
- **Queue**: Message queuing
- **Table**: NoSQL key-value

## Quick Reference
```bash
# Create storage account
az storage account create --name mystorage --resource-group rg --sku Standard_LRS

# Upload blob
az storage blob upload --account-name mystorage --container-name mycontainer --file local.txt --name remote.txt
```
