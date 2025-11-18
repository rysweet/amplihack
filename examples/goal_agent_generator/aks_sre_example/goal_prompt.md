# Goal: Azure Kubernetes Service SRE Agent

Autonomous Site Reliability Engineering agent for Azure Kubernetes Service (AKS) clusters. Monitors cluster health, detects issues, and performs automated remediation following SRE best practices.

## Constraints

**Technical:**

- Must work with Azure CLI and kubectl
- Should complete health checks within 5 minutes
- Must follow least-privilege access patterns
- Should handle multiple AKS clusters

**Operational:**

- Must not disrupt running workloads
- Should create detailed incident reports
- Must escalate critical issues to humans
- Should follow Azure Well-Architected Framework

**Performance:**

- Health check cycle: < 5 minutes
- Issue detection latency: < 1 minute
- Remediation time: < 10 minutes for common issues

## Success Criteria

**Monitoring:**

- Checks pod health (CrashLoopBackOff, OOMKilled, ImagePullBackOff)
- Monitors node status (NotReady, DiskPressure, MemoryPressure)
- Validates ingress/service configurations
- Tracks resource quotas and limits

**Detection:**

- Identifies failing deployments
- Detects resource exhaustion
- Finds misconfigurations
- Discovers security issues (exposed secrets, overprivileged pods)

**Remediation:**

- Restarts crashed pods (with backoff)
- Scales deployments based on metrics
- Applies configuration fixes
- Updates resource limits

**Reporting:**

- Creates structured incident reports
- Logs all actions taken
- Generates recommendations
- Tracks SLO/SLI metrics

## Context

This SRE agent will run continuously monitoring AKS clusters for common reliability issues. It should:

1. **Detect** problems early (before user impact)
2. **Remediate** common issues automatically (pod restarts, scaling)
3. **Escalate** complex issues to human SREs with detailed context
4. **Learn** from patterns (track recurring issues)
5. **Report** on cluster health and SRE actions

**Example Scenarios:**

- Pod crash loop → Analyze logs → Restart with backoff → Report if persists
- Node pressure → Check resource usage → Scale node pool → Alert if continues
- Failed deployment → Check image/config → Suggest fixes → Create incident
- Certificate expiry → Detect < 7 days → Renew or alert → Document

**Integration Points:**

- Azure CLI (`az aks get-credentials`, `az aks nodepool scale`)
- kubectl (`kubectl get pods`, `kubectl describe`, `kubectl logs`)
- Azure Monitor (query metrics)
- GitHub Issues (create incidents)
- PagerDuty/Slack (critical alerts)

**SRE Principles:**

- Embrace risk (accept some failures)
- Service level objectives (99.9% uptime target)
- Eliminate toil (automate repetitive tasks)
- Monitor everything
- Gradual rollout of changes
