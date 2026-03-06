# Platform Bridge - Troubleshooting Guide

Solutions to common problems when usin' the platform bridge.

## Platform Detection Issues

### Problem: "Could not detect platform from git remotes"

**Symptoms**:

```python
PlatformDetectionError: Could not detect platform from git remotes
```

**Cause**: Repository has no remotes, or remote URLs don't match GitHub/Azure DevOps patterns.

**Solutions**:

1. **Check if ye have remotes**:

   ```bash
   git remote -v
   ```

   If empty, add a remote:

   ```bash
   git remote add origin https://github.com/owner/repo.git
   # OR
   git remote add origin https://dev.azure.com/org/project/_git/repo
   ```

2. **Verify remote URL format**:
   - GitHub: Must contain `github.com`
   - Azure DevOps: Must contain `dev.azure.com` or `visualstudio.com`

   ```bash
   # GitHub format (correct)
   https://github.com/owner/repo.git
   git@github.com:owner/repo.git

   # Azure DevOps format (correct)
   https://dev.azure.com/org/project/_git/repo
   https://org.visualstudio.com/project/_git/repo
   ```

3. **Check if origin exists**:

   ```bash
   git remote show origin
   ```

   If origin doesn't exist but other remotes do:

   ```bash
   # Rename existing remote to origin
   git remote rename upstream origin
   ```

---

### Problem: "Wrong platform detected"

**Symptoms**: Bridge detects GitHub when ye have an Azure DevOps repo, or vice versa.

**Cause**: Multiple remotes configured, and bridge picks the wrong one.

**Solution**:

1. **Check all remotes**:

   ```bash
   git remote -v
   ```

   Output might show:

   ```
   origin    https://github.com/mirror/repo.git (fetch)
   upstream  https://dev.azure.com/real/repo/_git/main (fetch)
   ```

2. **Fix the origin remote**:

   ```bash
   # Remove incorrect origin
   git remote remove origin

   # Add correct origin
   git remote add origin https://dev.azure.com/real/repo/_git/main
   ```

3. **Verify detection**:

   ```python
   from claude.tools.platform_bridge import detect_platform, Platform

   platform = detect_platform()
   print(f"Detected: {platform}")
   # Should now show Platform.AZDO
   ```

---

## CLI Tool Issues

### Problem: "GitHub CLI not found"

**Symptoms**:

```python
CLIToolMissingError: GitHub CLI not found. Install with: brew install gh
```

**Cause**: GitHub CLI (gh) not be installed.

**Solutions by Platform**:

1. **macOS**:

   ```bash
   brew install gh
   ```

2. **Ubuntu/Debian**:

   ```bash
   sudo apt update
   sudo apt install gh
   ```

3. **Windows**:

   ```powershell
   winget install GitHub.cli
   ```

4. **Verify installation**:
   ```bash
   gh --version
   # Should output: gh version 2.x.x
   ```

---

### Problem: "Azure CLI not found"

**Symptoms**:

```python
CLIToolMissingError: Azure CLI not found. Install with: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**Cause**: Azure CLI (az) not be installed.

**Solutions by Platform**:

1. **macOS**:

   ```bash
   brew install azure-cli
   ```

2. **Ubuntu/Debian**:

   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

3. **Windows**:

   ```powershell
   winget install Microsoft.AzureCLI
   ```

4. **Verify installation**:
   ```bash
   az --version
   # Should output: azure-cli 2.x.x
   ```

---

## Authentication Issues

### Problem: "GitHub CLI not authenticated"

**Symptoms**:

```bash
gh: To get started with GitHub CLI, please run: gh auth login
```

**Cause**: GitHub CLI not authenticated with GitHub account.

**Solution**:

1. **Run authentication**:

   ```bash
   gh auth login
   ```

2. **Choose authentication method**:
   - Select "GitHub.com"
   - Choose "HTTPS" protocol
   - Choose "Login with a web browser"
   - Follow browser prompts

3. **Verify authentication**:

   ```bash
   gh auth status
   ```

   Should show:

   ```
   ✓ Logged in to github.com as username
   ```

---

### Problem: "Azure CLI not authenticated"

**Symptoms**:

```bash
Please run 'az login' to setup account.
```

**Cause**: Azure CLI not authenticated with Azure account.

**Solution**:

1. **Run authentication**:

   ```bash
   az login
   ```

2. **Follow browser prompts**:
   - Browser opens automatically
   - Sign in with Azure/Microsoft account
   - Grant permissions

3. **Verify authentication**:

   ```bash
   az account show
   ```

   Should show account details:

   ```json
   {
     "name": "Your Subscription",
     "user": {
       "name": "user@domain.com"
     }
   }
   ```

---

### Problem: "Token expired"

**Symptoms**:

```bash
gh: HTTP 401: Bad credentials
```

or

```bash
az: Token has expired
```

**Cause**: Authentication tokens expired (GitHub OAuth tokens last ~30 days, Azure tokens last ~90 days).

**Solution**:

1. **Refresh GitHub token**:

   ```bash
   gh auth refresh
   ```

2. **Refresh Azure token**:

   ```bash
   az account get-access-token --query accessToken
   ```

   If still expired:

   ```bash
   az logout
   az login
   ```

---

## Operation Failures

### Problem: "Branch not found"

**Symptoms**:

```python
BranchNotFoundError: Branch 'feat/test' doesn't exist
```

**Cause**: Tryin' to create PR from branch that doesn't exist on remote.

**Solution**:

1. **Check local branches**:

   ```bash
   git branch
   ```

2. **Push branch to remote**:

   ```bash
   git push -u origin feat/test
   ```

3. **Then create PR**:
   ```python
   pr = bridge.create_draft_pr(
       title="Test",
       body="Body",
       source_branch="feat/test",
       target_branch="main"
   )
   ```

---

### Problem: "PR not found"

**Symptoms**:

```python
PRNotFoundError: PR #999 doesn't exist
```

**Cause**: PR number doesn't exist in the repository.

**Solution**:

1. **List all PRs**:

   ```bash
   # GitHub
   gh pr list

   # Azure DevOps
   az repos pr list
   ```

2. **Use correct PR number**:
   ```python
   # Use actual PR number from list
   bridge.mark_pr_ready(pr_number=123)  # Correct number
   ```

---

### Problem: "Permission denied"

**Symptoms**:

```bash
gh: HTTP 403: Forbidden
```

or

```bash
az: AuthorizationFailed
```

**Cause**: Authenticated user doesn't have permission fer the operation.

**Solutions**:

1. **Check repository access**:
   - GitHub: Need write access to create issues/PRs
   - Azure DevOps: Need "Contribute" permission

2. **Verify permissions**:

   ```bash
   # GitHub - Check if ye can create issue
   gh issue list

   # Azure DevOps - Check permissions
   az repos show --repository repo-name
   ```

3. **Request access**:
   - Contact repository owner
   - Request "Write" access (GitHub) or "Contribute" (Azure DevOps)

---

## Performance Issues

### Problem: "CI status check takes too long"

**Symptoms**: `check_ci_status()` hangs or times out.

**Cause**: Large number of CI checks, or CI system be slow.

**Solution**:

1. **Increase timeout** (if needed):

   ```python
   # Default timeout be 60 seconds fer CI checks
   # If yer CI be slower, wait longer before checkin'
   import time
   time.sleep(120)  # Wait 2 minutes
   status = bridge.check_ci_status(pr_number=123)
   ```

2. **Poll instead of block**:

   ```python
   import time

   def wait_for_ci(bridge, pr_number, max_wait=600):
       """Poll CI status every 30 seconds"""
       start_time = time.time()

       while time.time() - start_time < max_wait:
           status = bridge.check_ci_status(pr_number=pr_number)

           if status['pending'] == 0:
               return status  # All checks complete

           print(f"Waitin' on {status['pending']} checks...")
           time.sleep(30)

       raise TimeoutError("CI checks didn't complete in time")
   ```

---

### Problem: "Operation times out"

**Symptoms**:

```python
subprocess.TimeoutExpired: Command timed out after 30 seconds
```

**Cause**: Network slow, or operation takes longer than expected.

**Solution**:

This be controlled internally by the bridge, but if ye frequently see timeouts:

1. **Check network connection**:

   ```bash
   ping github.com
   # OR
   ping dev.azure.com
   ```

2. **Check CLI tool directly**:

   ```bash
   # GitHub - Test gh directly
   time gh issue list

   # Azure DevOps - Test az directly
   time az repos pr list
   ```

3. **If consistently slow**:
   - Check VPN/proxy settings
   - Try different network
   - Contact platform support (GitHub/Azure)

---

## Edge Cases

### Problem: "Multiple remotes, unclear which to use"

**Symptoms**: Have both GitHub and Azure DevOps remotes, bridge picks wrong one.

**Solution**:

Bridge prioritizes `origin`, so:

```bash
# Set correct remote as origin
git remote remove origin  # Remove current origin
git remote add origin <correct-url>  # Add correct one

# Keep other remote with different name
git remote add mirror <other-url>
```

---

### Problem: "Working in monorepo with multiple projects"

**Symptoms**: Monorepo has both GitHub and Azure DevOps projects.

**Solution**:

Create separate bridge instances fer each project:

```python
# Project A: GitHub
bridge_a = PlatformBridge("/path/to/monorepo/project-a")

# Project B: Azure DevOps
bridge_b = PlatformBridge("/path/to/monorepo/project-b")

# Each project can have different git config
```

---

### Problem: "Using SSH URLs instead of HTTPS"

**Symptoms**: Git remote uses SSH format like `git@github.com:owner/repo.git`

**This works!** Bridge handles both SSH and HTTPS URLs:

```bash
# Both formats work
git remote add origin git@github.com:owner/repo.git  # SSH
git remote add origin https://github.com/owner/repo.git  # HTTPS
```

---

## Debugging

### Enable Debug Output

Set environment variable fer more detailed output:

```bash
export PLATFORM_BRIDGE_DEBUG=1
```

Then run yer code:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()  # Will print debug info
```

Debug output shows:

- Detected platform
- Git commands executed
- CLI commands run
- Subprocess output

### Check CLI Tool Logs

**GitHub CLI logs**:

```bash
# See what gh commands be run
export GH_DEBUG=api

# Then run yer code
```

**Azure CLI logs**:

```bash
# Enable Azure CLI logging
az config set core.logging_enable=true

# Check logs
cat ~/.azure/logs/az.log
```

---

## Getting Help

If ye still be havin' trouble:

1. **Check existing issues**:
   - [GitHub Issues](https://github.com/amplihack/amplihack/issues)

2. **Gather information**:

   ```bash
   # Platform info
   uname -a

   # CLI versions
   gh --version
   az --version

   # Git info
   git remote -v
   git --version
   ```

3. **Create issue with**:
   - Problem description
   - Error messages (full text)
   - Steps to reproduce
   - System information (from above)

---

## See Also

- [Platform Bridge Overview](../platform-bridge/README.md) - Feature documentation
- [API Reference](../reference/platform-bridge-api.md) - Complete API
- [How-To Guides](../howto/platform-bridge-workflows.md) - Common workflows
- [Security Guide](../security/platform-bridge-security.md) - Security practices
