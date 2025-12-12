# Azure Administration Skill

Comprehensive Azure administration capabilities for Claude Code, covering identity management, resource orchestration, CLI tooling, and DevOps automation.

## Overview

This skill enables Claude Code to assist with:

- **Identity & Access Management**: User provisioning, RBAC, service principals, managed identities
- **Resource Management**: Subscriptions, resource groups, ARM templates, Bicep deployments
- **CLI & Tooling**: az CLI patterns, azd workflows, JMESPath queries
- **MCP Integration**: Azure MCP server for AI-powered Azure operations
- **DevOps Automation**: CI/CD pipelines, infrastructure as code, deployment strategies
- **Cost & Governance**: Budget management, policy enforcement, compliance

## Prerequisites

### Required

1. **Azure Subscription**: Active Azure subscription with appropriate permissions
2. **Azure CLI**: Installed and authenticated
   ```bash
   # Install (macOS)
   brew install azure-cli

   # Install (Linux)
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

   # Verify
   az --version
   az login
   ```

3. **Permissions**: Minimum required permissions depend on operations:
   - **User management**: User Administrator or Global Administrator
   - **RBAC assignments**: Owner or User Access Administrator
   - **Resource management**: Contributor or higher
   - **Read-only operations**: Reader role sufficient

### Optional (Enhanced Capabilities)

1. **Azure Developer CLI (azd)**:
   ```bash
   # Install (macOS)
   brew tap azure/azd && brew install azd

   # Install (Linux)
   curl -fsSL https://aka.ms/install-azd.sh | bash

   # Verify
   azd version
   ```

2. **Azure MCP Server** (for AI-powered workflows):
   ```bash
   # Install globally
   npm install -g @modelcontextprotocol/server-azure

   # Configure in Claude Code MCP settings (~/.config/claude-code/mcp.json)
   {
     "mcpServers": {
       "azure": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-azure"],
         "env": {
           "AZURE_SUBSCRIPTION_ID": "your-subscription-id"
         }
       }
     }
   }
   ```

3. **Bicep CLI** (for infrastructure as code):
   ```bash
   # Bicep is included with Azure CLI 2.20.0+
   az bicep install
   az bicep version
   ```

4. **Azure PowerShell** (Windows environments):
   ```powershell
   Install-Module -Name Az -Repository PSGallery -Force
   Connect-AzAccount
   ```

## Installation

1. **Verify Azure CLI authentication**:
   ```bash
   az login
   az account show
   ```

2. **Set default subscription** (if you have multiple):
   ```bash
   az account set --subscription "My Subscription Name"
   ```

3. **Test access**:
   ```bash
   # List resource groups
   az group list --output table

   # Check current user
   az ad signed-in-user show
   ```

4. **Optional: Install Azure MCP** (see Optional section above)

5. **Skill is ready**: Claude Code will auto-activate this skill when you use Azure-related keywords in your requests.

## Quick Start

### Basic Operations

**List resources:**
```
Show me all VMs in my subscription
```

**Create resource group:**
```
Create a resource group named 'my-app-rg' in East US
```

**Deploy infrastructure:**
```
Deploy the Bicep template in ./infra/main.bicep to resource group 'my-app-rg'
```

### Identity Management

**Create user:**
```
Create a new Entra ID user named Jane Doe with email jane@contoso.com
```

**Assign RBAC role:**
```
Give jane@contoso.com Reader access to resource group 'my-app-rg'
```

**Create service principal:**
```
Create a service principal with Contributor role for my CI/CD pipeline
```

### DevOps Workflows

**Setup environment:**
```
Use azd to create a new development environment for a Node.js app
```

**Run deployment:**
```
Deploy my application to Azure using the existing Bicep templates
```

## File Structure

```
azure-admin/
├── SKILL.md                          # Main skill content (auto-loaded)
├── README.md                         # This file
├── tools/                            # Helper scripts
│   ├── bulk-operations.sh           # Batch user/resource operations
│   ├── cost-report.sh               # Generate cost reports
│   └── compliance-check.sh          # Verify policy compliance
├── docs/                             # Deep-dive documentation
│   ├── user-management.md           # Identity and user operations
│   ├── role-assignments.md          # RBAC patterns and custom roles
│   ├── resource-management.md       # Resource lifecycle and advanced patterns
│   ├── mcp-integration.md           # Azure MCP tools and workflows
│   ├── cli-patterns.md              # Advanced CLI scripting and queries
│   ├── devops-automation.md         # CI/CD and GitOps patterns
│   ├── cost-optimization.md         # Cost management and optimization
│   └── troubleshooting.md           # Common issues and solutions
├── examples/                         # Concrete workflow examples
│   ├── bulk-user-onboarding.md      # Automated user provisioning
│   ├── environment-setup.md         # Complete environment deployment
│   ├── role-audit.md                # RBAC compliance auditing
│   └── mcp-workflow.md              # AI-powered Azure operations
└── references/                       # External learning resources
    ├── microsoft-learn.md           # Official learning paths
    ├── az-104-guide.md              # AZ-104 certification guide
    └── api-references.md            # API and SDK documentation
```

## Common Use Cases

### Scenario 1: New Team Member Onboarding

```
I need to onboard 10 new engineers to our Azure environment. They should:
- Have Entra ID accounts
- Be added to the 'Engineering' security group
- Get Contributor access to the 'dev-*' resource groups
- Have MFA enabled

Use the template in examples/bulk-user-onboarding.md
```

### Scenario 2: Environment Provisioning

```
Setup a new production environment for our web application with:
- Resource group in East US 2
- App Service Plan (P1v3)
- Azure SQL Database (S1 tier)
- Application Insights
- Key Vault for secrets
- All resources properly tagged

Use azd and Bicep templates from examples/environment-setup.md
```

### Scenario 3: Cost Optimization Audit

```
Analyze our current Azure spending and provide recommendations:
- Identify idle resources
- Check for oversized VMs
- Find untagged resources
- Calculate reserved instance savings opportunities
- Generate cost report for management

Reference docs/cost-optimization.md for patterns
```

### Scenario 4: RBAC Compliance Review

```
Audit all role assignments in our subscription:
- List users with Owner or Contributor roles
- Find role assignments that haven't been reviewed in 90+ days
- Identify service principals with excessive permissions
- Generate compliance report

Use examples/role-audit.md workflow
```

## Troubleshooting

### Authentication Issues

**Problem**: `az login` fails or credentials expired

**Solution**:
```bash
# Clear cached credentials
az logout
az account clear

# Re-authenticate
az login --use-device-code

# Verify
az account show
```

### Permission Denied Errors

**Problem**: "Insufficient privileges" or "Forbidden" errors

**Solution**:
```bash
# Check your current role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv)

# Verify subscription context
az account show

# Request proper access from subscription administrator
```

### MCP Server Not Working

**Problem**: Azure MCP tools not available in Claude Code

**Solution**:
1. Verify Node.js 18+ installed: `node --version`
2. Reinstall MCP server: `npm install -g @modelcontextprotocol/server-azure`
3. Check MCP configuration in `~/.config/claude-code/mcp.json`
4. Restart Claude Code
5. Test: Ask "List my Azure resource groups"

### Resource Not Found

**Problem**: Can't find expected Azure resources

**Solution**:
```bash
# Verify subscription context
az account show

# List all subscriptions
az account list --output table

# Switch to correct subscription
az account set --subscription "My Subscription"

# Search across all subscriptions
az resource list --name "myResourceName"
```

## Learning Path

1. **Start Here**: Read SKILL.md for overview and quick reference
2. **Core Operations**: Study docs/user-management.md and docs/resource-management.md
3. **Security**: Review docs/role-assignments.md for RBAC patterns
4. **Automation**: Explore docs/devops-automation.md and examples/
5. **Advanced**: MCP integration (docs/mcp-integration.md) and custom solutions
6. **Certification**: Follow references/az-104-guide.md for AZ-104 preparation

## Support and Resources

### Official Microsoft Resources
- Azure Documentation: https://docs.microsoft.com/azure
- Azure CLI Reference: https://docs.microsoft.com/cli/azure
- Microsoft Learn: https://learn.microsoft.com/azure
- Azure Updates: https://azure.microsoft.com/updates

### Community Resources
- Azure Tech Community: https://techcommunity.microsoft.com/azure
- Stack Overflow: https://stackoverflow.com/questions/tagged/azure
- GitHub Issues: https://github.com/Azure/azure-cli/issues

### Skill-Specific Resources
- See references/ directory for curated learning paths
- Check examples/ for real-world workflow templates
- Review docs/ for deep technical content

## Contributing

To enhance this skill:

1. **Add new patterns**: Update relevant docs/ files
2. **Share examples**: Create new workflow examples in examples/
3. **Update references**: Keep reference materials current
4. **Report issues**: Document problems in docs/troubleshooting.md

## Version History

- **1.0.0** (2025-01-22): Initial release with comprehensive Azure administration coverage

## License

This skill is part of the amplihack framework and follows the same license terms.
