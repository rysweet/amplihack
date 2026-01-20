# How to Use the Azure AKS Expert Knowledge Base

## Overview

This knowledge base provides comprehensive guidance for Azure Kubernetes Service (AKS) deployments. The files are organized to support different learning styles and use cases.

## File Structure

### Knowledge.md (Primary Reference)

**Purpose:** Detailed Q&A format covering 9 core AKS concepts
**Best for:**

- Deep understanding of specific topics
- Finding Azure CLI commands and YAML examples
- Troubleshooting specific issues
  **Structure:**
- Concept 1: AKS Architecture & Control Plane
- Concept 2: Node Pools & Scaling
- Concept 3: Networking
- Concept 4: Identity & Access Management
- Concept 5: Storage & Persistence
- Concept 6: Monitoring & Logging
- Concept 7: Security
- Concept 8: CI/CD Integration
- Concept 9: Cost Optimization

### KeyInfo.md (Quick Reference)

**Purpose:** Executive summary and quick command reference
**Best for:**

- Getting started quickly
- Understanding high-level concepts
- Finding common command patterns
- Identifying learning path for your role

### HowToUseTheseFiles.md (This File)

**Purpose:** Scenario-based guidance and decision trees
**Best for:**

- Navigating the knowledge base effectively
- Finding the right information for your situation
- Understanding when to use each concept

## Usage Scenarios

### Scenario 1: First AKS Deployment

**Goal:** Deploy your first application to AKS

**Start here:**

1. Read KeyInfo.md "Learning Path for DevOps Engineers"
2. Review Knowledge.md Concept 1 (Architecture) - understand managed control plane
3. Review Knowledge.md Concept 3 (Networking) - decide on CNI model
4. Follow step-by-step in Concept 3 for HTTPS ingress setup
5. Review Knowledge.md Concept 6 (Monitoring) - enable Container Insights

**Expected outcome:**

- AKS cluster created with appropriate settings
- Application deployed with HTTPS access
- Monitoring enabled for troubleshooting

**Time estimate:** 2-4 hours

**Common mistakes to avoid:**

- Choosing kubenet for production (use Azure CNI)
- Skipping monitoring setup (enable before deploying apps)
- Not planning subnet size for Azure CNI (calculate IP requirements)

### Scenario 2: Production Hardening

**Goal:** Secure existing AKS cluster for production workloads

**Start here:**

1. Review KeyInfo.md "Common Production Patterns" - Pattern 1
2. Review Knowledge.md Concept 7 (Security) - private cluster configuration
3. Review Knowledge.md Concept 4 (Identity) - workload identity for Key Vault
4. Review Knowledge.md Concept 3 (Networking) - network policies
5. Review Knowledge.md Concept 7 (Security) - Pod Security Standards

**Expected outcome:**

- Private cluster with no public control plane access
- Workload identity configured (no service principal keys)
- Network policies limiting pod-to-pod traffic
- Secrets stored in Azure Key Vault
- Pod Security Standards enforced

**Time estimate:** 4-8 hours

**Common mistakes to avoid:**

- Converting public cluster to private (requires recreation)
- Using service principals instead of workload identity
- Not testing Key Vault access before deploying apps

### Scenario 3: Troubleshooting Issues

**Goal:** Diagnose and fix production issues

**Start here:**

1. Identify problem category (networking, storage, scaling, authentication)
2. Use Quick Reference Commands in Knowledge.md for diagnostics
3. Review relevant concept based on symptom

**Decision tree:**

**Pods not starting?**

- Check: `kubectl describe pod <pod-name>`
- Common causes: Image pull errors, resource limits, node capacity
- See: Concept 2 (Scaling) for resource issues

**Networking issues?**

- Check: `kubectl get svc`, `kubectl get endpoints`
- Common causes: Service selector mismatch, network policy blocking
- See: Concept 3 (Networking) for troubleshooting

**Authentication failures?**

- Check: `kubectl logs <pod-name>` for Azure SDK errors
- Common causes: Workload identity misconfiguration, RBAC permissions
- See: Concept 4 (Identity) for Key Vault/Azure access issues

**Storage mount failures?**

- Check: `kubectl describe pvc <pvc-name>`
- Common causes: Storage class not found, quota exceeded, zone mismatch
- See: Concept 5 (Storage) for persistent volume issues

**High costs?**

- Check: Azure Cost Management portal
- Common causes: Over-provisioned nodes, no autoscaling, Premium resources unused
- See: Concept 9 (Cost Optimization) for reduction strategies

**Expected outcome:**

- Root cause identified
- Fix applied with understanding of why it happened
- Preventive measures implemented

**Time estimate:** 30 minutes - 4 hours (depending on complexity)

### Scenario 4: Cost Optimization

**Goal:** Reduce AKS costs without impacting performance

**Start here:**

1. Review KeyInfo.md "Common Production Patterns" - Pattern 2
2. Review Knowledge.md Concept 9 (Cost Optimization) - all subsections
3. Analyze current usage with `kubectl top nodes` and `kubectl top pods`
4. Implement appropriate cost reduction strategies

**Decision tree:**

**Dev/test environment?**

- Use spot instances for non-critical workloads
- Enable cluster autoscaler with min=0 for test
- Schedule cluster start/stop during off-hours
- See: Concept 2 (Scaling) for spot node pools

**Production environment?**

- Right-size node pools based on actual usage
- Enable cluster autoscaler to scale down idle nodes
- Use spot instances for batch/fault-tolerant workloads only
- Implement resource quotas to prevent over-allocation
- See: Concept 9 for comprehensive strategy

**Expected outcome:**

- 30-50% cost reduction for dev/test environments
- 10-30% cost reduction for production without performance impact
- Resource usage aligns with actual needs

**Time estimate:** 2-4 hours initial setup, ongoing monitoring

**Common mistakes to avoid:**

- Using spot instances for stateful workloads
- Not setting resource limits (over-allocation)
- Stopping production clusters to save costs

### Scenario 5: CI/CD Integration

**Goal:** Automate deployments to AKS

**Start here:**

1. Review Knowledge.md Concept 8 (CI/CD Integration)
2. Follow GitHub Actions workflow example
3. Implement blue-green deployment for zero-downtime

**Expected outcome:**

- Automated build and push to Azure Container Registry
- Automated deployment to AKS on git push
- Rollback capability on deployment failure
- Deployment verification in pipeline

**Time estimate:** 2-4 hours

**Common mistakes to avoid:**

- Not using workload identity for GitHub Actions
- Deploying directly to production without staging
- No automated verification step

### Scenario 6: Implementing Autoscaling

**Goal:** Configure automatic scaling based on load

**Start here:**

1. Review Knowledge.md Concept 2 (Node Pools & Scaling)
2. Decide on scaling strategy (node-level vs pod-level)
3. Implement both cluster autoscaler (nodes) and HPA (pods)

**Decision tree:**

**Predictable traffic patterns?**

- Use scheduled scaling with HPA
- Set appropriate min/max replicas
- Configure based on time of day

**Unpredictable/bursty traffic?**

- Enable cluster autoscaler for node scaling
- Configure HPA for pod scaling
- Set appropriate thresholds (70-80% CPU)

**Expected outcome:**

- Application scales automatically based on load
- Nodes are added/removed based on pod demand
- Cost savings during low-traffic periods

**Time estimate:** 1-2 hours

**Common mistakes to avoid:**

- Setting HPA without cluster autoscaler (pods pending)
- Too aggressive scaling (thrashing)
- Not testing scale-down behavior

## Role-Based Usage Patterns

### DevOps Engineer (Deploying Applications)

**Primary concepts:** 1 (Architecture), 3 (Networking), 6 (Monitoring), 8 (CI/CD)
**Workflow:** Create cluster → Deploy app → Set up monitoring → Automate deployments

### Platform Engineer (Managing Infrastructure)

**Primary concepts:** 1 (Architecture), 2 (Scaling), 4 (Identity), 7 (Security), 9 (Cost)
**Workflow:** Design cluster → Implement security → Configure scaling → Optimize costs

### SRE (Operations & Troubleshooting)

**Primary concepts:** 6 (Monitoring), 3 (Networking), 5 (Storage), 2 (Scaling)
**Workflow:** Set up observability → Troubleshoot issues → Performance tuning → Capacity planning

### Security Engineer (Hardening & Compliance)

**Primary concepts:** 7 (Security), 4 (Identity), 3 (Networking)
**Workflow:** Implement private cluster → Configure RBAC → Apply policies → Audit compliance

## Decision Matrices

### Choosing Networking Model

| Requirement                 | Use Azure CNI | Use kubenet |
| --------------------------- | ------------- | ----------- |
| Production workload         | ✓             |             |
| VNet integration needed     | ✓             |             |
| Network policies with Azure | ✓             |             |
| Limited IP addresses        |               | ✓           |
| Dev/test environment        |               | ✓           |

### Choosing Storage Type

| Use Case                   | Use Azure Disk | Use Azure Files |
| -------------------------- | -------------- | --------------- |
| Database                   | ✓              |                 |
| Single-pod app             | ✓              |                 |
| High performance needed    | ✓              |                 |
| Shared storage across pods |                | ✓               |
| Legacy apps needing SMB    |                | ✓               |

### Choosing Node Pool Strategy

| Workload Type     | Node Pool Strategy                         |
| ----------------- | ------------------------------------------ |
| System components | Dedicated system node pool with taints     |
| Web applications  | General-purpose node pool with autoscaling |
| ML/AI workloads   | GPU node pool with appropriate SKU         |
| Batch jobs        | Spot instance node pool with autoscaling   |
| Databases         | Premium SSD node pool without spot         |

## Common Pitfalls to Avoid

1. **Not planning IP address space for Azure CNI**
   - Impact: Cluster creation fails or scaling limited
   - Solution: Calculate IPs needed: (max nodes × max pods per node) + cluster IPs
   - See: Concept 3 (Networking)

2. **Using service principals instead of workload identity**
   - Impact: Security risk (keys in secrets), rotation overhead
   - Solution: Migrate to workload identity with OIDC
   - See: Concept 4 (Identity)

3. **Deploying without resource limits**
   - Impact: Pod scheduling issues, cost overruns, noisy neighbors
   - Solution: Set resource requests and limits on all pods
   - See: Concept 9 (Cost Optimization)

4. **Not enabling monitoring before deploying apps**
   - Impact: No visibility when issues occur
   - Solution: Enable Container Insights during cluster creation
   - See: Concept 6 (Monitoring)

5. **Over-provisioning node pools**
   - Impact: Unnecessary costs
   - Solution: Use cluster autoscaler, start small and scale up
   - See: Concept 2 (Scaling)

6. **Using public clusters for production**
   - Impact: Security exposure, compliance issues
   - Solution: Use private clusters with private endpoint
   - See: Concept 7 (Security)

## Integration Points

### With Azure Services

- **Azure Container Registry:** Image storage, vulnerability scanning
- **Azure Key Vault:** Secrets, certificates, keys management
- **Azure Monitor:** Centralized logging and metrics
- **Azure Active Directory:** User authentication and RBAC
- **Azure Policy:** Compliance enforcement and governance
- **Azure DevOps/GitHub Actions:** CI/CD pipelines

### With Kubernetes Ecosystem

- **NGINX Ingress:** HTTP/HTTPS traffic routing
- **cert-manager:** Automated certificate management
- **Prometheus/Grafana:** Advanced metrics and visualization
- **Helm:** Package management
- **Kustomize:** Configuration management

## Success Checklist

Use this checklist to validate your AKS deployment:

### Basic Deployment

- [ ] Cluster created with appropriate VM size and count
- [ ] kubectl credentials configured
- [ ] Application deployed successfully
- [ ] Service accessible (LoadBalancer or Ingress)
- [ ] Basic monitoring enabled

### Production-Ready

- [ ] Private cluster with private endpoint
- [ ] Azure CNI networking
- [ ] Workload identity configured (no service principal keys)
- [ ] Key Vault integration for secrets
- [ ] RBAC policies implemented (least privilege)
- [ ] Network policies restricting pod-to-pod traffic
- [ ] Container Insights enabled with alerts
- [ ] Resource limits set on all pods
- [ ] Backup strategy defined
- [ ] CI/CD pipeline with automated rollbacks
- [ ] Cost monitoring and alerts configured
- [ ] Pod Security Standards enforced
- [ ] Cluster autoscaler enabled
- [ ] HPA configured for applications

## Getting Help

If you can't find what you need in this knowledge base:

1. Check the specific concept in Knowledge.md for detailed examples
2. Review Azure AKS documentation for latest features
3. Search Azure community forums for similar issues
4. Consult the agent with specific questions about your scenario

## Knowledge Base Maintenance

This knowledge base is current as of 2025-10-18 and covers:

- AKS API version: 2023-10-01
- Kubernetes versions: 1.27-1.29
- Azure CLI version: 2.53+

---

**Version:** 1.0.0
**Last Updated:** 2025-10-18
**Next Review:** 2026-01-18
