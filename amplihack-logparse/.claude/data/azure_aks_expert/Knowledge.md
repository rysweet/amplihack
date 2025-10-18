# Knowledge Graph: Azure Kubernetes Service (AKS) for Production Deployments

Generated: 2025-10-18 (Focused version for production workload deployment)

## Overview

This focused knowledge graph contains essential AKS concepts for deploying and managing production applications on Azure Kubernetes Service:
- AKS architecture and control plane
- Node pools and scaling strategies
- Networking models and ingress
- Identity and RBAC
- Storage and persistence
- Monitoring and observability
- Security best practices
- CI/CD integration
- Cost optimization

## Core Concepts

### 1. AKS Architecture and Control Plane

**Q: What is the AKS control plane and who manages it?**

A: The AKS control plane includes the Kubernetes API server, scheduler, controller manager, and etcd. Microsoft manages and maintains this for you at no cost - you only pay for worker nodes.

Key benefits:
- Managed upgrades and patches
- High availability built-in
- No need to manage master nodes
- SLA-backed uptime (99.95% with Availability Zones)

```bash
# View your cluster details
az aks show --resource-group myResourceGroup --name myAKSCluster

# Get credentials to interact with cluster
az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
```

**Q: What happens during AKS cluster creation?**

A: When you create an AKS cluster, Azure provisions:
1. Control plane (managed by Microsoft)
2. Node pool(s) with VMs running Kubernetes nodes
3. Virtual network and subnet (or uses existing)
4. Load balancer for external access
5. Managed identity for Azure resource access

```bash
# Create AKS cluster with best practices
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --node-count 3 \
  --enable-managed-identity \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --zones 1 2 3 \
  --network-plugin azure \
  --enable-addons monitoring
```

**Q: How do I upgrade my AKS cluster?**

A: AKS supports rolling upgrades with zero downtime:

```bash
# Check available versions
az aks get-upgrades --resource-group myResourceGroup --name myAKSCluster

# Upgrade control plane first
az aks upgrade \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --kubernetes-version 1.28.0

# Upgrade specific node pool
az aks nodepool upgrade \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name nodepool1 \
  --kubernetes-version 1.28.0
```

### 2. Node Pools and Scaling

**Q: What are node pools and when should I use multiple pools?**

A: Node pools are groups of nodes with identical VM configurations. Use multiple node pools for:
- Different workload types (CPU-intensive vs memory-intensive)
- GPU workloads requiring specific VM SKUs
- Windows and Linux containers in same cluster
- Cost optimization (mix spot instances with regular nodes)

```bash
# Add a new node pool for GPU workloads
az aks nodepool add \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name gpupool \
  --node-count 2 \
  --node-vm-size Standard_NC6s_v3 \
  --node-taints sku=gpu:NoSchedule \
  --labels workload=gpu

# Add spot instance node pool for cost savings
az aks nodepool add \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name spotpool \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1 \
  --node-count 3 \
  --labels pool=spot
```

**Q: How does cluster autoscaling work in AKS?**

A: AKS uses the Kubernetes Cluster Autoscaler to automatically scale nodes based on pod resource requests:

```bash
# Enable autoscaler on existing node pool
az aks nodepool update \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name nodepool1 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10
```

Deployment with Horizontal Pod Autoscaler:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:v1
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. Networking (CNI, Services, Ingress)

**Q: What's the difference between kubenet and Azure CNI networking?**

A:
- **Kubenet**: Nodes get Azure VNET IPs, pods get IPs from separate address space (10.244.0.0/16). Requires route tables. Simpler, conserves IP addresses.
- **Azure CNI**: Both nodes and pods get IPs from VNET. More IPs consumed but enables direct VNET integration, better for hybrid scenarios.

```bash
# Create cluster with Azure CNI (recommended for production)
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --network-plugin azure \
  --vnet-subnet-id /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Network/virtualNetworks/<vnet>/subnets/<subnet> \
  --service-cidr 10.2.0.0/24 \
  --dns-service-ip 10.2.0.10
```

**Q: How do I expose applications with Services and Ingress?**

A: Use different service types based on requirements:

```yaml
# ClusterIP - internal only
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
  - port: 8080
    targetPort: 8080
---
# LoadBalancer - external with Azure Load Balancer
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 8080
```

Ingress with NGINX for path-based routing:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - myapp.example.com
    secretName: myapp-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

Install NGINX Ingress Controller:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

### 4. Identity and Access (Managed Identities, RBAC)

**Q: How do AKS pods access Azure resources securely?**

A: Use Azure AD Workload Identity (modern approach) or AAD Pod Identity (legacy):

```bash
# Enable workload identity
az aks update \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --enable-oidc-issuer \
  --enable-workload-identity

# Create managed identity
az identity create \
  --name myAppIdentity \
  --resource-group myResourceGroup

# Get identity details
export USER_ASSIGNED_CLIENT_ID=$(az identity show \
  --name myAppIdentity \
  --resource-group myResourceGroup \
  --query clientId -o tsv)

# Create federated credential
az identity federated-credential create \
  --name myFederatedCredential \
  --identity-name myAppIdentity \
  --resource-group myResourceGroup \
  --issuer $(az aks show -n myAKSCluster -g myResourceGroup --query "oidcIssuerProfile.issuerUrl" -o tsv) \
  --subject system:serviceaccount:default:myapp-sa
```

Deploy with workload identity:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: myapp-sa
      containers:
      - name: myapp
        image: myapp:v1
        env:
        - name: AZURE_CLIENT_ID
          value: "${USER_ASSIGNED_CLIENT_ID}"
```

**Q: How do I configure Kubernetes RBAC for teams?**

A: Integrate AKS with Azure AD and use Kubernetes RBAC:

```bash
# Enable Azure AD integration
az aks update \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --enable-azure-rbac

# Assign Azure RBAC roles
az role assignment create \
  --assignee user@example.com \
  --role "Azure Kubernetes Service Cluster User Role" \
  --scope /subscriptions/<sub>/resourcegroups/myResourceGroup/providers/Microsoft.ContainerService/managedClusters/myAKSCluster
```

Create namespace-scoped roles:

```yaml
# Create namespace for team
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
---
# Role for developers
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: team-alpha
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "services", "jobs", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods/log", "pods/exec"]
  verbs: ["get", "list", "create"]
---
# Bind role to Azure AD group
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  namespace: team-alpha
  name: developer-binding
subjects:
- kind: Group
  name: "team-alpha-developers"
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

### 5. Storage (Persistent Volumes, Storage Classes)

**Q: How do I use persistent storage in AKS?**

A: AKS provides built-in storage classes for Azure Disk and Azure Files:

```bash
# View available storage classes
kubectl get storageclass

# Common storage classes:
# - default: Standard HDD Azure Disk
# - managed-premium: Premium SSD Azure Disk
# - azurefile: Azure Files (supports ReadWriteMany)
# - azurefile-premium: Premium Azure Files
```

Use persistent volumes:

```yaml
# PersistentVolumeClaim for database
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: managed-premium
  resources:
    requests:
      storage: 50Gi
---
# StatefulSet using PVC
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

**Q: When should I use Azure Disk vs Azure Files?**

A:
- **Azure Disk**: Single pod access (ReadWriteOnce), better performance, use for databases
- **Azure Files**: Multi-pod access (ReadWriteMany), shared storage, use for shared content or legacy apps

```yaml
# Azure Files for shared uploads
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-uploads
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: azurefile-premium
  resources:
    requests:
      storage: 100Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: web
        image: mywebapp:v1
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: shared-uploads
```

### 6. Monitoring and Logging (Azure Monitor, Container Insights)

**Q: How do I enable comprehensive monitoring in AKS?**

A: Use Azure Monitor Container Insights for full observability:

```bash
# Enable Container Insights
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons monitoring \
  --workspace-resource-id /subscriptions/<sub>/resourceGroups/myResourceGroup/providers/Microsoft.OperationalInsights/workspaces/myWorkspace

# View live logs
az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
kubectl logs -f deployment/myapp

# Stream logs to console
kubectl logs -f -l app=myapp --all-containers=true
```

Query logs with Azure Monitor:

```kusto
// Find errors in last hour
ContainerLog
| where TimeGenerated > ago(1h)
| where LogEntry contains "error" or LogEntry contains "exception"
| project TimeGenerated, Computer, ContainerID, LogEntry
| order by TimeGenerated desc

// Pod restart analysis
KubePodInventory
| where TimeGenerated > ago(24h)
| where Namespace == "production"
| summarize RestartCount=sum(PodRestartCount) by PodName, ContainerName
| where RestartCount > 0
| order by RestartCount desc

// High CPU pods
Perf
| where TimeGenerated > ago(1h)
| where ObjectName == "K8SContainer"
| where CounterName == "cpuUsageNanoCores"
| summarize AvgCPU=avg(CounterValue) by Computer, InstanceName
| where AvgCPU > 800000000  // 0.8 cores
| order by AvgCPU desc
```

**Q: How do I set up alerts for my AKS workloads?**

A: Create Azure Monitor alert rules:

```bash
# Alert on pod failures
az monitor metrics alert create \
  --name pod-failures-alert \
  --resource-group myResourceGroup \
  --scopes /subscriptions/<sub>/resourceGroups/myResourceGroup/providers/Microsoft.ContainerService/managedClusters/myAKSCluster \
  --condition "avg Pod Status == 0" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email user@example.com

# Alert on high node CPU
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource-group myResourceGroup \
  --scopes /subscriptions/<sub>/resourceGroups/myResourceGroup/providers/Microsoft.ContainerService/managedClusters/myAKSCluster \
  --condition "avg Percentage CPU > 85" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email ops@example.com
```

### 7. Security Best Practices

**Q: What are essential security configurations for production AKS?**

A: Implement defense-in-depth security:

```bash
# Enable Azure Policy for AKS
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons azure-policy

# Enable Defender for Containers
az security pricing create \
  --name Containers \
  --tier Standard

# Use private cluster (API server not publicly accessible)
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --enable-private-cluster \
  --private-dns-zone system
```

Network policies for pod isolation:

```yaml
# Deny all traffic by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
# Allow specific traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

**Q: How do I manage secrets securely in AKS?**

A: Use Azure Key Vault integration with CSI driver:

```bash
# Enable Key Vault CSI driver
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons azure-keyvault-secrets-provider

# Create Key Vault and add secret
az keyvault create --name myKeyVault --resource-group myResourceGroup
az keyvault secret set --vault-name myKeyVault --name database-password --value "SuperSecret123!"

# Grant AKS access to Key Vault
export CLUSTER_IDENTITY=$(az aks show -g myResourceGroup -n myAKSCluster --query identityProfile.kubeletidentity.clientId -o tsv)
az keyvault set-policy --name myKeyVault --object-id $CLUSTER_IDENTITY --secret-permissions get
```

Use secrets in pods:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: azure-keyvault
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    tenantId: "your-tenant-id"
    keyvaultName: "myKeyVault"
    objects: |
      array:
        - |
          objectName: database-password
          objectType: secret
          objectVersion: ""
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:v1
        volumeMounts:
        - name: secrets-store
          mountPath: "/mnt/secrets-store"
          readOnly: true
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-password-secret
              key: database-password
      volumes:
      - name: secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: "azure-keyvault"
```

### 8. CI/CD Integration

**Q: How do I set up CI/CD for AKS with GitHub Actions?**

A: Use GitHub Actions with Azure credentials:

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy to AKS

on:
  push:
    branches: [main]

env:
  AZURE_RESOURCE_GROUP: myResourceGroup
  CLUSTER_NAME: myAKSCluster
  CONTAINER_REGISTRY: myregistry.azurecr.io
  IMAGE_NAME: myapp

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Build and push image
      run: |
        az acr login --name myregistry
        docker build -t $CONTAINER_REGISTRY/$IMAGE_NAME:${{ github.sha }} .
        docker push $CONTAINER_REGISTRY/$IMAGE_NAME:${{ github.sha }}

    - name: Get AKS credentials
      run: |
        az aks get-credentials \
          --resource-group $AZURE_RESOURCE_GROUP \
          --name $CLUSTER_NAME \
          --overwrite-existing

    - name: Deploy to AKS
      run: |
        kubectl set image deployment/myapp \
          myapp=$CONTAINER_REGISTRY/$IMAGE_NAME:${{ github.sha }} \
          --namespace production

        kubectl rollout status deployment/myapp -n production
```

**Q: How do I implement blue-green deployments in AKS?**

A: Use multiple deployments with service selector switching:

```yaml
# Blue deployment (current)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: myapp
        image: myapp:v1.0
---
# Green deployment (new)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: green
  template:
    metadata:
      labels:
        app: myapp
        version: green
    spec:
      containers:
      - name: myapp
        image: myapp:v2.0
---
# Service initially points to blue
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
  namespace: production
spec:
  selector:
    app: myapp
    version: blue  # Switch to 'green' to cut over
  ports:
  - port: 80
    targetPort: 8080
```

Switch traffic:

```bash
# Verify green is healthy
kubectl get pods -l version=green -n production
kubectl logs -l version=green -n production

# Cut over to green
kubectl patch service myapp-service -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback if needed
kubectl patch service myapp-service -n production \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

### 9. Cost Optimization

**Q: How do I reduce AKS costs without sacrificing reliability?**

A: Apply these cost optimization strategies:

```bash
# Use spot instances for fault-tolerant workloads
az aks nodepool add \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name spotpool \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1 \
  --node-count 5 \
  --labels pool=spot \
  --node-taints kubernetes.azure.com/scalesetpriority=spot:NoSchedule

# Start/stop cluster during off-hours
az aks stop --resource-group myResourceGroup --name myAKSCluster
az aks start --resource-group myResourceGroup --name myAKSCluster

# Right-size node pools
az aks nodepool scale \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name nodepool1 \
  --node-count 2
```

Resource optimization:

```yaml
# Use pod disruption budgets for safe scaling
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
---
# Right-size resource requests/limits
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:v1
        resources:
          requests:
            cpu: 100m      # Start small
            memory: 128Mi
          limits:
            cpu: 500m      # Prevent runaway processes
            memory: 512Mi
      # Use spot nodes for batch jobs
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
      nodeSelector:
        pool: spot
```

**Q: How do I monitor and analyze AKS costs?**

A: Use Azure Cost Management and kubecost:

```bash
# Install kubecost for detailed cost breakdown
kubectl create namespace kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --set kubecostToken="your-token"

# Access kubecost dashboard
kubectl port-forward -n kubecost deployment/kubecost-cost-analyzer 9090:9090

# Query costs via Azure CLI
az consumption usage list \
  --start-date 2025-10-01 \
  --end-date 2025-10-31 \
  --resource-group myResourceGroup
```

Cost allocation labels:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    cost-center: engineering
    team: platform
    environment: production
spec:
  template:
    metadata:
      labels:
        cost-center: engineering
        team: platform
        environment: production
    spec:
      containers:
      - name: myapp
        image: myapp:v1
```

## Application to Production Deployments

For deploying production applications to AKS, these concepts enable:

1. **Architecture**: Understand managed control plane, plan for HA with zones
2. **Scaling**: Implement cluster and pod autoscaling for elasticity
3. **Networking**: Choose right CNI, expose apps with ingress, secure with network policies
4. **Identity**: Use workload identity for Azure resource access, RBAC for team access
5. **Storage**: Select appropriate storage classes, plan for persistent data
6. **Monitoring**: Enable Container Insights, query logs, set up alerts
7. **Security**: Private clusters, Key Vault integration, network policies, Azure Policy
8. **CI/CD**: Automate builds and deployments, implement blue-green releases
9. **Cost**: Use spot instances, right-size resources, monitor spending

## Key Takeaways for Implementation

- Use Azure CNI with managed identities for production
- Enable cluster autoscaler with appropriate min/max
- Implement network policies for zero-trust networking
- Store secrets in Azure Key Vault, not Kubernetes secrets
- Use Azure Monitor for centralized logging and metrics
- Set resource requests/limits on all containers
- Automate deployments with GitHub Actions or Azure DevOps
- Mix spot and regular nodes for cost optimization
- Tag resources for cost allocation and chargeback
