# Azure Kubernetes Service (AKS) Expert Knowledge Base

This document contains comprehensive Q&A covering production AKS deployments, from cluster creation to monitoring and troubleshooting.

## Concept 1: AKS Architecture & Control Plane

### Q: What is the Azure managed control plane and how does it benefit me?

**A:** Azure manages the Kubernetes control plane (API server, etcd, scheduler, controller manager) for you. Benefits:

- Azure handles control plane upgrades, patches, and high availability
- You only pay for worker nodes, not control plane
- 99.95% SLA available with uptime SLA tier
- Automatic health monitoring and recovery

**Example:** Create AKS cluster with uptime SLA:

```bash
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --tier standard \
  --node-count 3 \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5 \
  --generate-ssh-keys
```

### Q: How do I upgrade my AKS cluster safely?

**A:** AKS upgrades involve both control plane and node pools. Best practice:

1. Check available versions: `az aks get-upgrades --resource-group myRG --name myAKS`
2. Upgrade control plane first: `az aks upgrade --resource-group myRG --name myAKS --kubernetes-version 1.28.3 --control-plane-only`
3. Upgrade node pools individually: `az aks nodepool upgrade --resource-group myRG --cluster-name myAKS --name nodepool1 --kubernetes-version 1.28.3`

**Production tip:** Use surge upgrades to minimize downtime:

```bash
az aks nodepool update \
  --resource-group myRG \
  --cluster-name myAKS \
  --name nodepool1 \
  --max-surge 33%
```

## Concept 2: Node Pools & Scaling

### Q: What are node pools and when should I use multiple node pools?

**A:** Node pools are groups of nodes with identical VM configurations. Use multiple node pools for:

- Different workload types (CPU-intensive vs memory-intensive)
- Mixing spot and regular instances
- Isolating system workloads from application workloads
- Different OS types (Linux and Windows)

**Example:** Add GPU node pool for ML workloads:

```bash
az aks nodepool add \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name gpupool \
  --node-count 1 \
  --node-vm-size Standard_NC6s_v3 \
  --node-taints sku=gpu:NoSchedule
```

### Q: How do I configure autoscaling for my AKS cluster?

**A:** AKS supports two levels of autoscaling:

1. **Cluster Autoscaler** (node-level): Adds/removes nodes based on pending pods
2. **Horizontal Pod Autoscaler (HPA)**: Scales pods based on CPU/memory/custom metrics

**Enable cluster autoscaler:**

```bash
az aks update \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 10
```

**Configure HPA for application:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Q: How can I use spot instances to reduce costs?

**A:** Azure Spot VMs offer up to 90% cost savings for fault-tolerant workloads. Create spot node pool:

```bash
az aks nodepool add \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name spotpool \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1 \
  --enable-cluster-autoscaler \
  --min-count 0 \
  --max-count 5 \
  --node-taints kubernetes.azure.com/scalesetpriority=spot:NoSchedule
```

**Deploy workload to spot nodes:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  replicas: 3
  template:
    spec:
      tolerations:
        - key: "kubernetes.azure.com/scalesetpriority"
          operator: "Equal"
          value: "spot"
          effect: "NoSchedule"
      nodeSelector:
        kubernetes.azure.com/scalesetpriority: spot
```

## Concept 3: Networking

### Q: Should I use Azure CNI or kubenet for my AKS cluster?

**A:** Choose based on your requirements:

**Azure CNI** (Recommended for production):

- Pods get IP addresses from VNet subnet
- Direct connectivity from VNet to pods
- Better performance, no NAT overhead
- Requires more IP addresses (plan subnet size carefully)

**kubenet** (Simpler, fewer IPs):

- Pods use private IP range
- NAT translation for external traffic
- Suitable for smaller clusters
- Limitations with Azure network policies

**Create cluster with Azure CNI:**

```bash
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --network-plugin azure \
  --vnet-subnet-id /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet} \
  --service-cidr 10.0.0.0/16 \
  --dns-service-ip 10.0.0.10
```

### Q: How do I set up HTTPS ingress with Let's Encrypt certificates?

**A:** Complete workflow for production HTTPS ingress:

**Step 1: Install NGINX Ingress Controller:**

```bash
# Add Helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install NGINX ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-nginx \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

**Step 2: Install cert-manager for Let's Encrypt:**

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

**Step 3: Deploy application with HTTPS ingress:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: webapp-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - myapp.example.com
      secretName: webapp-tls
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: webapp-service
                port:
                  number: 80
```

### Q: How do I implement network policies for pod-to-pod security?

**A:** Network policies control traffic between pods. Example: Allow only frontend to access backend:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

## Concept 4: Identity & Access Management

### Q: How do I integrate Azure Key Vault with AKS for secrets management?

**A:** Use Azure Key Vault CSI Driver for seamless secrets access:

**Step 1: Enable Azure Key Vault provider:**

```bash
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons azure-keyvault-secrets-provider
```

**Step 2: Configure workload identity:**

```bash
# Enable workload identity on cluster
az aks update \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --enable-oidc-issuer \
  --enable-workload-identity

# Get OIDC issuer URL
OIDC_ISSUER=$(az aks show --resource-group myResourceGroup --name myAKSCluster --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create managed identity
az identity create \
  --resource-group myResourceGroup \
  --name myAKSIdentity

# Grant Key Vault access
az keyvault set-policy \
  --name myKeyVault \
  --object-id $(az identity show --resource-group myResourceGroup --name myAKSIdentity --query principalId -o tsv) \
  --secret-permissions get list
```

**Step 3: Create SecretProviderClass:**

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: azure-keyvault-secrets
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    clientID: ${MANAGED_IDENTITY_CLIENT_ID}
    keyvaultName: myKeyVault
    objects: |
      array:
        - |
          objectName: database-password
          objectType: secret
          objectVersion: ""
    tenantId: ${TENANT_ID}
```

**Step 4: Mount secrets in pod:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: webapp
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: workload-identity-sa
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: secrets-store
          mountPath: "/mnt/secrets"
          readOnly: true
      env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-password
              key: password
  volumes:
    - name: secrets-store
      csi:
        driver: secrets-store.csi.k8s.io
        readOnly: true
        volumeAttributes:
          secretProviderClass: azure-keyvault-secrets
```

### Q: How do I configure RBAC for least-privilege access?

**A:** Implement RBAC at cluster and namespace levels:

**Cluster-level read-only access:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: read-only
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "deployments", "configmaps"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-only-binding
subjects:
  - kind: Group
    name: "developers@example.com"
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: read-only
  apiGroup: rbac.authorization.k8s.io
```

**Namespace-specific deployment access:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer
  namespace: production
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployer-binding
  namespace: production
subjects:
  - kind: User
    name: "ci-pipeline@example.com"
roleRef:
  kind: Role
  name: deployer
  apiGroup: rbac.authorization.k8s.io
```

## Concept 5: Storage & Persistence

### Q: Should I use Azure Disk or Azure Files for persistent storage?

**A:** Choose based on access pattern:

**Azure Disk (ReadWriteOnce):**

- Best for databases, single-pod applications
- High performance, lower latency
- Only one pod can mount at a time

**Azure Files (ReadWriteMany):**

- Best for shared file storage across multiple pods
- Supports SMB and NFS protocols
- Slightly higher latency

**Storage class for Azure Disk (Premium SSD):**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: managed-premium-retain
provisioner: disk.csi.azure.com
parameters:
  storageaccounttype: Premium_LRS
  kind: Managed
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

**StatefulSet with persistent volume:**

```yaml
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
  volumeClaimTemplates:
    - metadata:
        name: postgres-storage
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: managed-premium-retain
        resources:
          requests:
            storage: 100Gi
```

## Concept 6: Monitoring & Logging

### Q: How do I enable Azure Monitor Container Insights for my AKS cluster?

**A:** Container Insights provides comprehensive cluster and workload monitoring:

**Enable Container Insights:**

```bash
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons monitoring \
  --workspace-resource-id /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{workspace}
```

**Query pod CPU usage with KQL:**

```kql
Perf
| where ObjectName == "K8SContainer" and CounterName == "cpuUsageNanoCores"
| where TimeGenerated > ago(1h)
| summarize AvgCPU = avg(CounterValue) by bin(TimeGenerated, 5m), InstanceName
| render timechart
```

**Query pod restart count:**

```kql
KubePodInventory
| where TimeGenerated > ago(24h)
| where PodStatus == "Running"
| summarize RestartCount = max(PodRestartCount) by Name, Namespace
| where RestartCount > 5
| order by RestartCount desc
```

**Query logs from specific namespace:**

```kql
ContainerLog
| where TimeGenerated > ago(1h)
| where Namespace == "production"
| where LogEntry contains "error"
| project TimeGenerated, Computer, ContainerID, LogEntry
| order by TimeGenerated desc
```

### Q: How do I set up alerts for critical metrics?

**A:** Create action groups and metric alerts:

**CPU threshold alert:**

```bash
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource-group myResourceGroup \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/myAKSCluster \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action /subscriptions/{sub-id}/resourceGroups/{rg}/providers/microsoft.insights/actionGroups/ops-team
```

**Pod failure alert with KQL:**

```kql
KubePodInventory
| where TimeGenerated > ago(5m)
| where PodStatus == "Failed"
| summarize FailedPods = count() by Namespace
| where FailedPods > 3
```

## Concept 7: Security

### Q: How do I deploy a private AKS cluster?

**A:** Private clusters use private endpoint for control plane access:

```bash
az aks create \
  --resource-group myResourceGroup \
  --name myPrivateAKSCluster \
  --enable-private-cluster \
  --private-dns-zone system \
  --network-plugin azure \
  --vnet-subnet-id /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}
```

**Access private cluster:**

- Use Azure Bastion or VPN to connect to VNet
- Use `az aks command invoke` for CLI access without VPN:

```bash
az aks command invoke \
  --resource-group myResourceGroup \
  --name myPrivateAKSCluster \
  --command "kubectl get pods -A"
```

### Q: How do I implement Pod Security Standards?

**A:** Use Azure Policy or built-in Pod Security admission:

**Enable Azure Policy add-on:**

```bash
az aks enable-addons \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --addons azure-policy
```

**Enforce restricted security with Pod Security admission:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Example restricted pod spec:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-webapp
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      resources:
        limits:
          cpu: "1"
          memory: "512Mi"
        requests:
          cpu: "100m"
          memory: "128Mi"
```

## Concept 8: CI/CD Integration

### Q: How do I set up GitHub Actions to deploy to AKS?

**A:** Complete GitHub Actions workflow for AKS deployment:

```yaml
name: Deploy to AKS
on:
  push:
    branches: [main]

env:
  ACR_REGISTRY: myregistry.azurecr.io
  IMAGE_NAME: myapp
  AKS_RESOURCE_GROUP: myResourceGroup
  AKS_CLUSTER: myAKSCluster
  NAMESPACE: production

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push image to ACR
        run: |
          az acr build \
            --registry ${ACR_REGISTRY} \
            --image ${IMAGE_NAME}:${{ github.sha }} \
            --image ${IMAGE_NAME}:latest \
            --file Dockerfile .

      - name: Get AKS credentials
        run: |
          az aks get-credentials \
            --resource-group ${AKS_RESOURCE_GROUP} \
            --name ${AKS_CLUSTER} \
            --overwrite-existing

      - name: Deploy to AKS
        run: |
          kubectl set image deployment/myapp \
            myapp=${ACR_REGISTRY}/${IMAGE_NAME}:${{ github.sha }} \
            -n ${NAMESPACE}

          kubectl rollout status deployment/myapp -n ${NAMESPACE}

      - name: Verify deployment
        run: |
          kubectl get pods -n ${NAMESPACE}
          kubectl get svc -n ${NAMESPACE}
```

### Q: How do I implement blue-green deployments?

**A:** Use separate deployments and switch traffic via service selector:

**Blue deployment (current):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webapp
      version: blue
  template:
    metadata:
      labels:
        app: webapp
        version: blue
    spec:
      containers:
        - name: webapp
          image: myapp:v1.0
```

**Green deployment (new):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webapp
      version: green
  template:
    metadata:
      labels:
        app: webapp
        version: green
    spec:
      containers:
        - name: webapp
          image: myapp:v2.0
```

**Service (initially pointing to blue):**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webapp-service
spec:
  selector:
    app: webapp
    version: blue # Switch to 'green' after validation
  ports:
    - port: 80
      targetPort: 8080
```

**Switch traffic to green:**

```bash
kubectl patch service webapp-service -p '{"spec":{"selector":{"version":"green"}}}'
```

## Concept 9: Cost Optimization

### Q: What are the best practices for reducing AKS costs?

**A:** Comprehensive cost optimization strategy:

**1. Right-size node pools:**

```bash
# Monitor actual resource usage
kubectl top nodes
kubectl top pods --all-namespaces

# Resize node pool to appropriate VM size
az aks nodepool update \
  --resource-group myResourceGroup \
  --cluster-name myAKSCluster \
  --name nodepool1 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10
```

**2. Use spot instances for batch workloads:**
See Concept 2 for spot instance configuration.

**3. Implement resource quotas per namespace:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: development
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "5"
```

**4. Set pod resource limits:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: production
spec:
  limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      type: Container
```

**5. Schedule node shutdowns for dev/test environments:**

```bash
# Stop AKS cluster (keeps configuration, stops compute costs)
az aks stop --resource-group myResourceGroup --name myDevAKSCluster

# Start when needed
az aks start --resource-group myResourceGroup --name myDevAKSCluster
```

### Q: How do I monitor and analyze AKS costs?

**A:** Use Azure Cost Management and custom metrics:

**Query cost by node pool:**

```bash
az consumption usage list \
  --start-date 2025-10-01 \
  --end-date 2025-10-18 \
  --query "[?contains(instanceName, 'aks-nodepool')]"
```

**Set budget alerts:**

```bash
az consumption budget create \
  --resource-group myResourceGroup \
  --budget-name aks-monthly-budget \
  --amount 5000 \
  --time-grain Monthly \
  --start-date 2025-10-01 \
  --end-date 2026-10-01 \
  --notifications Actual_GreaterThan_90_Percent="{\"enabled\":true,\"operator\":\"GreaterThan\",\"threshold\":90,\"contactEmails\":[\"ops@example.com\"]}"
```

**Identify unused resources:**

```bash
# Find pods with low CPU usage
kubectl top pods --all-namespaces | awk '$3 < 10 {print $0}'

# Find persistent volumes not bound to pods
kubectl get pv | grep Available
```

---

## Quick Reference Commands

### Cluster Management

```bash
# Create cluster
az aks create --resource-group myRG --name myAKS --node-count 3

# Get credentials
az aks get-credentials --resource-group myRG --name myAKS

# Scale cluster
az aks scale --resource-group myRG --name myAKS --node-count 5

# Upgrade cluster
az aks upgrade --resource-group myRG --name myAKS --kubernetes-version 1.28.3
```

### Debugging

```bash
# Check pod status
kubectl get pods -A

# View pod logs
kubectl logs <pod-name> -n <namespace>

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Port forward for local testing
kubectl port-forward <pod-name> 8080:80 -n <namespace>
```

### Troubleshooting

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# View cluster events
kubectl get events --sort-by='.lastTimestamp' -A

# Check resource usage
kubectl top nodes
kubectl top pods -A

# View control plane logs
az aks show --resource-group myRG --name myAKS --query "apiServerAccessProfile"
```

---

**Knowledge Base Version:** 1.0.0
**Last Updated:** 2025-10-18
**Covers:** AKS production deployments, networking, security, monitoring, cost optimization
