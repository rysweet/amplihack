# Azure DevOps CLI Skill Test Scenarios

Validation scenarios for testing the Azure DevOps CLI skill quality, auto-activation, and content accuracy.

## Test Scenario 1: Auto-Activation on Keywords

### Purpose

Verify skill automatically activates on relevant keywords

### Test Cases

#### TC1.1: Pipeline Keywords

```
User Input: "How do I list all Azure DevOps pipelines?"
Expected: Skill auto-activates
Validation: Response includes `az pipelines list` command
```

#### TC1.2: Boards Keywords

```
User Input: "Create a user story in Azure Boards"
Expected: Skill auto-activates
Validation: Response includes `az boards work-item create` command
```

#### TC1.3: Repos Keywords

```
User Input: "Show me Azure Repos pull requests"
Expected: Skill auto-activates
Validation: Response includes `az repos pr list` command
```

#### TC1.4: Artifacts Keywords

```
User Input: "How do I publish to Azure Artifacts?"
Expected: Skill auto-activates
Validation: Response includes `az artifacts universal publish` command
```

#### TC1.5: General DevOps Keywords

```
User Input: "List Azure DevOps projects"
Expected: Skill auto-activates
Validation: Response includes `az devops project list` command
```

## Test Scenario 2: Quick Start Validation

### Purpose

Verify Quick Start section enables immediate usage

### Test Cases

#### TC2.1: Installation

```
Test: Follow installation steps
Steps:
  1. Run: az extension add --name azure-devops
  2. Verify: az devops --version
Expected: Extension installed successfully
```

#### TC2.2: Authentication

```
Test: Authenticate with Azure DevOps
Steps:
  1. Run: az login
  2. Verify: az account show
Expected: Successfully authenticated
```

#### TC2.3: Configuration

```
Test: Set default organization and project
Steps:
  1. Run: az devops configure --defaults organization=https://dev.azure.com/myorg project=myproject
  2. Verify: az devops configure --list
Expected: Defaults configured correctly
```

#### TC2.4: Verification

```
Test: Verify setup works
Steps:
  1. Run: az devops project list
Expected: Projects listed without errors
```

## Test Scenario 3: Essential Commands Accuracy

### Purpose

Verify all essential commands are accurate and work

### Test Cases

#### TC3.1: DevOps Commands

```
Test Commands:
  - az devops project list
  - az devops project show --project MyProject
  - az devops user list
  - az devops team list --project MyProject

Validation: Each command returns expected data without errors
```

#### TC3.2: Pipeline Commands

```
Test Commands:
  - az pipelines list
  - az pipelines show --name "MyPipeline"
  - az pipelines run --name "MyPipeline"
  - az pipelines runs list
  - az pipelines runs show --id RUN_ID

Validation: Each command works with proper authentication
```

#### TC3.3: Boards Commands

```
Test Commands:
  - az boards query --wiql "SELECT [System.Id] FROM WorkItems"
  - az boards work-item create --type "Task" --title "Test"
  - az boards work-item show --id WORK_ITEM_ID
  - az boards work-item update --id WORK_ITEM_ID --state "Active"
  - az boards iteration project list

Validation: Work items can be created and queried
```

#### TC3.4: Repos Commands

```
Test Commands:
  - az repos list
  - az repos show --repository myrepo
  - az repos pr list --status active
  - az repos pr show --id PR_ID

Validation: Repository operations work correctly
```

#### TC3.5: Artifacts Commands

```
Test Commands:
  - az artifacts feed list
  - az artifacts universal list --feed myfeed
  - az artifacts universal publish --feed myfeed --name test --version 1.0.0 --path ./test
  - az artifacts universal download --feed myfeed --name test --version 1.0.0 --path ./download

Validation: Package operations succeed
```

## Test Scenario 4: Common Workflows Validation

### Purpose

Verify all 10+ common workflows are practical and work

### Test Cases

#### TC4.1: CI/CD Pipeline Automation

```
Workflow: Create pipeline, run it, and monitor
Commands:
  1. az pipelines create --name "Test-Pipeline" --repository myrepo --yml-path azure-pipelines.yml
  2. az pipelines run --name "Test-Pipeline"
  3. az pipelines runs show --id RUN_ID

Expected: Pipeline created, runs, and status retrieved
```

#### TC4.2: Pull Request Review Automation

```
Workflow: List PRs, show details, update status
Commands:
  1. az repos pr list --status active
  2. az repos pr show --id PR_ID
  3. az repos pr set-vote --id PR_ID --vote approve

Expected: PR workflow completes successfully
```

#### TC4.3: Work Item Batch Creation

```
Workflow: Create multiple work items
Script:
  for title in "Feature A" "Feature B"; do
    az boards work-item create --type "User Story" --title "$title"
  done

Expected: Multiple work items created
```

#### TC4.4: Pipeline Status Dashboard

```
Workflow: Get recent pipeline runs
Command:
  az pipelines runs list --top 10 --query "[].{Name:pipeline.name, Status:status}" --output table

Expected: Dashboard data displayed
```

#### TC4.5: Repository Clone Automation

```
Workflow: List and clone all repos
Script:
  az repos list --query "[].{Name:name, URL:remoteUrl}" --output tsv | while read name url; do
    echo "Would clone $name from $url"
  done

Expected: All repos identified for cloning
```

## Test Scenario 5: Troubleshooting Section

### Purpose

Verify troubleshooting guidance resolves common issues

### Test Cases

#### TC5.1: Authentication Failures

```
Problem: Command fails with auth error
Solution Steps:
  1. az account clear
  2. az login
  3. Retry command

Expected: Authentication restored
```

#### TC5.2: Default Configuration Issues

```
Problem: Command requires --organization and --project
Solution Steps:
  1. az devops configure --defaults organization=URL project=NAME
  2. Retry command without flags

Expected: Defaults work correctly
```

#### TC5.3: Extension Update

```
Problem: Old extension version
Solution Steps:
  1. az extension update --name azure-devops
  2. az extension show --name azure-devops

Expected: Extension updated successfully
```

## Test Scenario 6: Advanced Patterns

### Purpose

Verify advanced patterns work correctly

### Test Cases

#### TC6.1: REST API Access

```
Test: Direct REST API call
Command:
  az devops invoke --area build --resource builds --route-parameters project=MyProject --api-version 6.0 --http-method GET

Expected: API response returned
```

#### TC6.2: JMESPath Queries

```
Test: Complex query filtering
Command:
  az pipelines runs list --query "[?result=='failed'].{Pipeline:pipeline.name, Branch:sourceBranch}"

Expected: Filtered results returned
```

#### TC6.3: Shell Aliases

```
Test: Create and use alias
Commands:
  1. alias azdo-pipelines="az pipelines list --output table"
  2. azdo-pipelines

Expected: Alias works as shortcut
```

## Test Scenario 7: Token Efficiency

### Purpose

Verify core skill stays under 2000 tokens

### Test Cases

#### TC7.1: Token Count

```
Test: Measure skill.md token count
Method: Use token counter tool
Expected: Core skill.md < 2000 tokens
```

#### TC7.2: Progressive Disclosure

```
Test: Verify extended content is separate
Check:
  - Core content in skill.md
  - Extended content in examples/
  - References from skill.md to examples/

Expected: Clear separation maintained
```

## Test Scenario 8: Philosophy Compliance

### Purpose

Verify skill follows amplihack philosophy

### Test Cases

#### TC8.1: Ruthless Simplicity

```
Check: Core skill focuses on 80/20 rule
Validation:
  - Only essential commands in core
  - 5 most common commands per group
  - No unnecessary complexity

Expected: Simplicity maintained
```

#### TC8.2: Zero-BS Implementation

```
Check: All commands are tested and work
Validation:
  - No TODOs or placeholders
  - All examples are complete
  - Commands include proper error handling

Expected: Every command works
```

#### TC8.3: Self-Contained Module

```
Check: No external dependencies
Validation:
  - Only requires Azure CLI + extension
  - No additional tools needed
  - Clear setup instructions

Expected: Completely self-contained
```

## Test Scenario 9: Extended Content Quality

### Purpose

Verify extended content provides comprehensive coverage

### Test Cases

#### TC9.1: Complete Command References

```
Check: Each command group has complete reference
Files to verify:
  - examples/pipelines-reference.md
  - examples/boards-reference.md
  - examples/repos-reference.md
  - examples/artifacts-reference.md

Expected: All commands documented with examples
```

#### TC9.2: Advanced Workflow Guides

```
Check: Workflow guides are practical
Files to verify:
  - examples/workflows/ci-cd-automation.md
  - examples/workflows/release-management.md
  - examples/workflows/team-collaboration.md

Expected: Real-world automation patterns
```

## Test Scenario 10: Integration Testing

### Purpose

Verify skill works end-to-end in real scenarios

### Test Cases

#### TC10.1: New User Onboarding

```
Scenario: New user follows skill to get started
Steps:
  1. Install Azure DevOps extension
  2. Authenticate
  3. Configure defaults
  4. Run first command

Expected: User successfully completes setup
```

#### TC10.2: Daily Developer Workflow

```
Scenario: Developer uses skill for daily tasks
Tasks:
  1. List active PRs
  2. Run pipeline
  3. Check work items
  4. Review build status

Expected: All daily tasks completed using skill guidance
```

#### TC10.3: CI/CD Automation

```
Scenario: Automate deployment pipeline
Steps:
  1. Create pipeline
  2. Set up variables
  3. Run pipeline
  4. Monitor status

Expected: Complete CI/CD workflow automated
```

## Success Criteria

### Skill Quality Metrics

**Auto-Activation**:

- ✓ Activates on all 5 command group keywords
- ✓ Activates on specific operations (pipelines, PRs, work items)
- ✓ No false negatives (activates when it should)

**Content Accuracy**:

- ✓ All essential commands work without errors
- ✓ All code examples are syntactically correct
- ✓ All workflows are practical and tested

**Token Efficiency**:

- ✓ Core skill < 2000 tokens
- ✓ Extended content in separate files
- ✓ Progressive disclosure works

**Philosophy Compliance**:

- ✓ Ruthless simplicity (80/20 focus)
- ✓ Zero-BS (no placeholders)
- ✓ Self-contained (no external deps)
- ✓ Regeneratable (clear structure)

**User Experience**:

- ✓ Quick Start enables immediate usage
- ✓ Essential commands cover daily tasks
- ✓ Common workflows solve real problems
- ✓ Troubleshooting resolves issues
- ✓ Extended content provides depth

## Manual Testing Checklist

Before marking skill as complete:

- [ ] Run all Quick Start commands
- [ ] Test at least 3 commands from each group
- [ ] Execute 5 common workflows
- [ ] Verify troubleshooting steps resolve issues
- [ ] Test auto-activation with various phrases
- [ ] Count tokens in skill.md (< 2000)
- [ ] Review extended content for completeness
- [ ] Check all code examples for syntax errors
- [ ] Validate YAML frontmatter
- [ ] Test explicit skill invocation

## Automated Testing (Future)

Potential automation opportunities:

1. **Command Syntax Validation**: Parse all commands and validate syntax
2. **Link Checking**: Verify all internal references work
3. **Token Counting**: Automate token budget enforcement
4. **Example Execution**: Run code examples in sandbox
5. **YAML Validation**: Validate frontmatter schema

## Notes

- Tests assume Azure DevOps organization and project are configured
- Some tests require actual Azure DevOps resources
- Authentication must be configured before running tests
- Extended content tests are manual reviews for quality
- Philosophy compliance is subjective but follows clear criteria

## References

- [Azure DevOps CLI Testing Guide](https://learn.microsoft.com/en-us/cli/azure/devops)
- [amplihack Philosophy](../../.claude/context/PHILOSOPHY.md)
- [amplihack Patterns](../../.claude/context/PATTERNS.md)
