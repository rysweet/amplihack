# AZ-104: Microsoft Azure Administrator Certification Guide

Complete study guide for passing the AZ-104 Microsoft Azure Administrator certification exam.

## Exam Overview

**Exam Code:** AZ-104
**Title:** Microsoft Azure Administrator
**Duration:** 120 minutes
**Number of Questions:** 40-60
**Passing Score:** 700 (scale of 1000)
**Cost:** $165 USD
**Languages:** English, Japanese, Chinese (Simplified), Korean, German, French, Spanish, Portuguese (Brazil), Arabic (Saudi Arabia), Russian, Chinese (Traditional), Italian, Indonesian

**Renewal:** Required every year (free renewal assessment)

## Exam Skills Measured

### Domain 1: Manage Azure Identities and Governance (15-20%)

**Manage Azure Active Directory (Azure AD) objects**

- Create users and groups
- Manage licenses in Azure AD
- Create administrative units
- Manage user and group properties
- Manage device settings and device identity
- Perform bulk updates
- Manage guest accounts
- Configure self-service password reset (SSPR)

**Manage access control**

- Manage built-in Azure roles
- Assign roles at different scopes
- Interpret access assignments
- Create custom roles
- Manage access reviews

**Manage Azure subscriptions and governance**

- Configure and manage Azure Policy
- Configure resource locks
- Apply and manage tags on resources
- Manage resource groups
- Manage subscriptions
- Manage costs by using alerts, budgets, and recommendations
- Configure management groups

### Domain 2: Implement and Manage Storage (15-20%)

**Configure access to storage**

- Configure network access to storage accounts
- Create and configure storage accounts
- Generate shared access signature (SAS) tokens
- Manage access keys
- Configure Azure AD authentication for a storage account
- Configure storage account encryption

**Manage data in Azure storage accounts**

- Create import and export jobs
- Manage data by using Azure Storage Explorer and AzCopy
- Implement Azure Storage replication
- Configure blob object replication

**Configure Azure Files and Azure Blob Storage**

- Create an Azure file share
- Configure Azure Blob Storage
- Configure storage tiers
- Configure blob lifecycle management

### Domain 3: Deploy and Manage Azure Compute Resources (20-25%)

**Automate deployment of resources by using ARM templates or Bicep files**

- Interpret an ARM template or Bicep file
- Modify an existing ARM template
- Modify an existing Bicep file
- Deploy resources by using an ARM template or Bicep file
- Export a deployment as an ARM template or convert an ARM template to a Bicep file

**Create and configure virtual machines**

- Create a virtual machine
- Configure Azure Disk Encryption
- Move a VM to another resource group, subscription, or region
- Manage VM sizes
- Manage VM disks
- Deploy VMs to availability zones and availability sets
- Deploy and configure Azure Virtual Machine Scale Sets

**Provision and manage containers in the Azure portal**

- Create and manage an Azure container registry
- Provision a container by using Azure Container Instances
- Provision a container by using Azure Container Apps
- Manage sizing and scaling for containers, including Azure Container Instances and Azure Container Apps

**Create and configure Azure App Service**

- Provision an App Service plan
- Configure scaling for an App Service plan
- Create an App Service
- Configure certificates and TLS for an App Service
- Map an existing custom DNS name to an App Service
- Configure backup for an App Service
- Configure networking settings for an App Service
- Configure deployment slots for an App Service

### Domain 4: Configure and Manage Virtual Networking (25-30%)

**Configure virtual networks**

- Create and configure virtual networks and subnets
- Create and configure virtual network peering
- Configure public IP addresses
- Configure user-defined network routes
- Troubleshoot network connectivity

**Configure secure access to virtual networks**

- Create and configure network security groups (NSGs) and application security groups (ASGs)
- Evaluate effective security rules in NSGs
- Implement Azure Bastion
- Configure service endpoints for Azure platform as a service (PaaS)
- Configure private endpoints for Azure PaaS

**Configure name resolution**

- Configure Azure DNS
- Configure custom DNS settings
- Configure a private DNS zone

**Configure load balancing**

- Configure Azure Application Gateway
- Configure an internal or public load balancer
- Troubleshoot load balancing

### Domain 5: Monitor and Maintain Azure Resources (10-15%)

**Monitor resources by using Azure Monitor**

- Configure and interpret metrics
- Configure Azure Monitor Logs
- Query and analyze logs
- Set up alert rules, action groups, and alert processing rules
- Configure and manage Azure Monitor Application Insights

**Implement backup and recovery**

- Create an Azure Recovery Services vault
- Create an Azure Backup vault
- Create and configure a backup policy
- Perform backup and restore operations by using Azure Backup
- Configure Azure Site Recovery for Azure resources
- Perform a failover to a secondary region by using Site Recovery
- Configure and interpret reports and alerts for backups

## Study Approach

### Phase 1: Foundation (2-4 weeks)

**Week 1-2: Azure Fundamentals**

- Complete AZ-900 learning path if not already certified
- Understand cloud concepts and Azure basics
- Familiarize with Azure Portal

**Week 3-4: Identity and Governance**

- Study Azure AD (Entra ID) thoroughly
- Practice RBAC assignments
- Learn Azure Policy and management groups
- Hands-on: Create users, groups, assign roles

### Phase 2: Core Services (4-6 weeks)

**Week 5-6: Storage**

- Study all storage account types
- Practice with Azure Storage Explorer and AzCopy
- Learn blob lifecycle management
- Hands-on: Create storage accounts, configure access

**Week 7-8: Compute**

- Master VM creation and management
- Learn ARM templates and Bicep
- Understand containers (ACI, AKS basics, App Service)
- Hands-on: Deploy VMs, containers, App Services

**Week 9-10: Networking**

- Deep dive into VNets, subnets, NSGs
- Study load balancing (Azure LB, App Gateway)
- Learn DNS configuration
- Hands-on: Configure networking, implement security

### Phase 3: Advanced Topics (2-3 weeks)

**Week 11-12: Monitoring and Backup**

- Master Azure Monitor and Log Analytics
- Learn backup strategies
- Understand Site Recovery
- Hands-on: Configure monitoring, backups

**Week 13: Practice and Review**

- Complete practice exams
- Review weak areas
- Hands-on labs for all domains

## Key Resources

**Official Microsoft Learn Paths:**

- https://learn.microsoft.com/certifications/exams/az-104

**Practice Exams:**

- Microsoft Official Practice Assessment
- MeasureUp practice tests
- Whizlabs AZ-104 practice tests

**Hands-On Labs:**

- Microsoft Learn sandbox
- Free Azure trial ($200 credit)
- Azure Pass (if available through study groups)

**Books:**

- "Exam Ref AZ-104 Microsoft Azure Administrator" by Microsoft Press
- "Microsoft Azure Administrator Exam Guide AZ-104" by Packt

**Video Courses:**

- Microsoft Learn video content
- Pluralsight "Microsoft Azure Administrator" path
- A Cloud Guru AZ-104 course
- LinkedIn Learning AZ-104 prep

## Hands-On Lab Suggestions

### Identity Labs

```bash
# Lab 1: User and Group Management
- Create 10 users via CSV import
- Create security groups
- Assign users to groups
- Configure RBAC roles at different scopes

# Lab 2: Custom RBAC Roles
- Create custom role for VM operators
- Assign custom role
- Test permissions
- Modify role definition

# Lab 3: Azure Policy
- Create policy to require tags
- Assign policy to resource group
- Test policy enforcement
- Review compliance
```

### Storage Labs

```bash
# Lab 4: Storage Account Configuration
- Create storage accounts (Standard, Premium)
- Configure blob access tiers
- Implement lifecycle management
- Generate and use SAS tokens

# Lab 5: File Shares and Sync
- Create Azure File Share
- Mount file share on VM
- Configure Azure File Sync
- Test synchronization
```

### Compute Labs

```bash
# Lab 6: Virtual Machine Deployment
- Deploy VM from portal
- Deploy VM with ARM template
- Deploy VM with Bicep
- Configure VM extensions

# Lab 7: App Service Deployment
- Create App Service Plan
- Deploy web app
- Configure custom domain
- Implement deployment slots
- Perform slot swap

# Lab 8: Container Deployment
- Create container registry
- Build and push container image
- Deploy to Azure Container Instances
- Deploy to Azure Container Apps
```

### Networking Labs

```bash
# Lab 9: Virtual Network Configuration
- Create VNet with multiple subnets
- Configure NSG rules
- Implement VNet peering
- Configure UDRs

# Lab 10: Load Balancing
- Deploy Azure Load Balancer
- Configure backend pool
- Create health probes
- Test load distribution

# Lab 11: Application Gateway
- Deploy Application Gateway
- Configure backend pool with multiple VMs
- Implement path-based routing
- Configure WAF rules
```

### Monitoring Labs

```bash
# Lab 12: Azure Monitor
- Configure Log Analytics workspace
- Create diagnostic settings
- Write KQL queries
- Set up alert rules

# Lab 13: Backup and Recovery
- Create Recovery Services vault
- Configure VM backup
- Perform backup
- Restore VM from backup
```

## Exam Day Tips

**Before the Exam:**

1. Review all learning paths one final time
2. Take final practice exam
3. Get good sleep night before
4. Arrive 15 minutes early (or prepare testing space if online)

**During the Exam:**

1. Read questions carefully (watch for "NOT", "EXCEPT")
2. Mark difficult questions for review
3. Eliminate obviously wrong answers
4. Manage time (2 minutes per question on average)
5. Review all marked questions before submitting

**Question Types:**

- Multiple choice (single answer)
- Multiple choice (multiple answers)
- Drag and drop
- Dropdown selection
- Case studies (scenario-based)
- Labs (hands-on in Azure Portal)

**Common Traps:**

- Questions asking for "least administrative effort" → choose managed services
- Questions about "most cost-effective" → consider reserved instances, right-sizing
- Always choose solutions with high availability when not specified otherwise
- Security questions → choose least privilege, MFA, encryption

## Post-Exam

**If You Pass:**

- Digital badge available immediately
- Certificate available in 5-10 business days
- Update LinkedIn, resume
- Schedule renewal reminder (1 year)

**If You Don't Pass:**

- Review score report to identify weak areas
- Wait 24 hours before retaking
- No limit on retakes (but cost applies each time)
- Focus study on weak domains

## Renewal

**Annual Renewal:**

- Free renewal assessment on Microsoft Learn
- Complete 6 months after certification
- Must pass to maintain certification
- Focus on new features and updates

## Next Certifications

After AZ-104, consider:

**Expert Level:**

- AZ-305: Azure Solutions Architect Expert
- AZ-400: Azure DevOps Engineer Expert

**Specialty:**

- AZ-500: Azure Security Engineer Associate
- AZ-700: Azure Network Engineer Associate
- DP-900: Azure Data Fundamentals
- AI-900: Azure AI Fundamentals

## Practice Questions

### Sample Question 1

You need to ensure that all resources in a resource group are tagged with a cost center value. What should you implement?

A. Azure Policy
B. Resource lock
C. Azure Blueprints
D. Management group

**Answer: A**
Explanation: Azure Policy can enforce tag requirements.

### Sample Question 2

You have a VM running in Azure. You need to encrypt the VM disks. Which service should you use?

A. Azure Key Vault
B. Azure Disk Encryption
C. Azure Information Protection
D. Azure Security Center

**Answer: B**
Explanation: Azure Disk Encryption encrypts VM disks using BitLocker (Windows) or DM-Crypt (Linux).

### Sample Question 3

You need to allow your on-premises network to communicate with Azure VNet. The connection must be encrypted. What should you implement?

A. ExpressRoute
B. VNet Peering
C. VPN Gateway
D. Azure Firewall

**Answer: C**
Explanation: VPN Gateway provides encrypted connection between on-premises and Azure.

## Additional Practice Resources

**GitHub Repositories:**

- Azure Samples: https://github.com/Azure-Samples
- Bicep Examples: https://github.com/Azure/bicep
- ARM Templates: https://github.com/Azure/azure-quickstart-templates

**Community Study Groups:**

- Reddit: r/AzureCertification
- Microsoft Tech Community
- LinkedIn Azure study groups
- Discord Azure certification channels

## Related Documentation

- @microsoft-learn.md - Microsoft Learn resources
- @api-references.md - API and SDK docs
- @../docs/ - Amplihack Azure admin skill documentation
