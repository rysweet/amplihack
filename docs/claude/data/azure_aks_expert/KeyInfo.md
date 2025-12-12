# Azure AKS Expert - Key Information Summary

## Executive Summary

Azure Kubernetes Service (AKS) provides managed Kubernetes with Azure-native integration. This knowledge base covers production-ready deployments with focus on:

- Enterprise-grade networking and security
- Cost optimization strategies
- Monitoring and operational excellence
- CI/CD integration patterns

## Core Concepts at a Glance

### 1. Managed Control Plane

- Azure handles control plane (API server, etcd, scheduler)
- 99.95% SLA with uptime tier
- Automatic upgrades and patches
- No control plane costs

### 2. Node Pools & Scaling

- Multiple node pools for workload isolation
- Cluster autoscaler for automatic node scaling
- HPA for pod-level autoscaling
- Spot instances for up to 90% cost savings

### 3. Networking

- Azure CNI for VNet-integrated networking
- NGINX ingress with Let's Encrypt for HTTPS
- Network policies for pod-to-pod security
- Private clusters for control plane isolation

### 4. Identity & Access

- Workload identity for Azure service access (Key Vault, Storage)
- RBAC for least-privilege access control
- Azure AD integration for user authentication
- Managed identities (no service principal keys)

### 5. Storage

- Azure Disk for high-performance block storage
- Azure Files for shared file storage
- Dynamic provisioning with storage classes
- StatefulSets for stateful applications

### 6. Monitoring

- Container Insights for comprehensive observability
- KQL queries for log analysis
- Metric alerts for proactive monitoring
- Integration with Azure dashboards

### 7. Security

- Private clusters for production workloads
- Key Vault CSI driver for secrets
- Pod Security Standards enforcement
- Azure Policy for compliance

### 8. CI/CD

- GitHub Actions for automated deployments
- Blue-green deployment strategies
- Container registry integration (ACR)
- Automated rollbacks on failure

### 9. Cost Optimization

- Right-size node pools based on metrics
- Spot instances for batch workloads
- Resource quotas and limits
- Cluster start/stop for dev environments

## Learning Path

### For DevOps Engineers (First AKS Deployment)

1. Read Concept 1 (Architecture) to understand managed control plane
2. Read Concept 3 (Networking) to choose CNI model
3. Read Concept 6 (Monitoring) to enable Container Insights
4. Deploy sample application with HTTPS ingress

### For Platform Engineers (Production Hardening)

1. Read Concept 7 (Security) for private clusters and Key Vault
2. Read Concept 4 (Identity) for workload identity setup
3. Read Concept 2 (Scaling) for autoscaling configuration
4. Read Concept 9 (Cost) for optimization strategies

### For SREs (Troubleshooting)

1. Read Concept 6 (Monitoring) for KQL queries
2. Use Quick Reference for diagnostic commands
3. Read relevant concept based on symptom (networking, storage, scaling)
4. Apply systematic debugging approach

## Common Production Patterns

### Pattern 1: Production Web Application

- Private AKS cluster with Azure CNI
- NGINX ingress with Let's Encrypt
- Workload identity for Key Vault secrets
- HPA for pod autoscaling
- Container Insights monitoring

### Pattern 2: Cost-Optimized Dev/Test

- Public cluster with kubenet
- Spot instance node pools
- Cluster autoscaler (min=0 for test environments)
- Resource quotas per namespace
- Schedule cluster start/stop

### Pattern 3: High-Security Workload

- Private cluster with private endpoint
- Azure AD integration with RBAC
- Network policies between namespaces
- Pod Security Standards enforcement
- Azure Policy for compliance scanning

### Pattern 4: Stateful Application (Database)

- Dedicated node pool with Premium SSD
- StatefulSet with persistent volumes
- Azure Disk storage class
- Backup strategy with snapshots
- Topology-aware volume binding

## Quick Command Reference

### Cluster Operations

```bash
# Create cluster
az aks create --resource-group myRG --name myAKS --node-count 3

# Get credentials
az aks get-credentials --resource-group myRG --name myAKS

# Enable monitoring
az aks enable-addons --resource-group myRG --name myAKS --addons monitoring
```

### Debugging

```bash
# Check all pods
kubectl get pods -A

# View logs
kubectl logs <pod> -n <namespace>

# Describe for events
kubectl describe pod <pod> -n <namespace>
```

### Scaling

```bash
# Manual scale
az aks scale --resource-group myRG --name myAKS --node-count 5

# Enable autoscaler
az aks update --resource-group myRG --name myAKS --enable-cluster-autoscaler --min-count 1 --max-count 10
```

## Success Metrics

You'll know you're using AKS effectively when:

- Clusters use private endpoints and workload identity (no keys in pods)
- Monitoring and alerts are configured before deploying applications
- Resource limits are set on all pods
- Cost trends are tracked and optimized monthly
- CI/CD pipelines deploy reliably with automated validation

## Next Steps

1. Review Knowledge.md for detailed Q&A and examples
2. Consult HowToUseTheseFiles.md for scenario-specific guidance
3. Start with your use case (first deployment, hardening, troubleshooting, optimization)
4. Reference specific concepts as needed

---

**Version:** 1.0.0
**Last Updated:** 2025-10-18
