# GitHub Web UI Walkthrough - Branch Protection

This guide provides step-by-step instructions for configuring GitHub branch protection using the web interface.

## Method 2: GitHub UI Walkthrough

### Navigate to Branch Protection Settings

1. **Open your repository** in a web browser: `https://github.com/{owner}/{repo}`

2. **Navigate to Settings**:
   - Click **Settings** tab (requires admin access)
   - If you don't see Settings, you lack admin permissions

3. **Access Branch Protection**:
   - In left sidebar, click **Branches** (under "Code and automation")
   - Find **Branch protection rules** section
   - Click **Add branch protection rule** button

4. **Specify Branch Name**:
   - In "Branch name pattern" field, enter: `main`
   - This creates a rule specifically for the `main` branch

### Configure Protection Settings

#### Setting 1: Require Pull Request Before Merging

5. **Enable PR requirement**:
   - ✅ Check **Require a pull request before merging**
   - This forces all changes through PR workflow

6. **Configure review requirements**:
   - ✅ Check **Require approvals**
   - Set **Required number of approvals before merging**: `1`
   - ⬜ Leave **Dismiss stale pull request approvals** unchecked (optional)
   - ⬜ Leave **Require review from Code Owners** unchecked (unless you use CODEOWNERS)
   - ⬜ Leave **Require approval of the most recent reviewable push** unchecked

#### Setting 2: Require Status Checks to Pass

7. **Enable status checks**:
   - ✅ Check **Require status checks to pass before merging**
   - A search box appears: "Search for status checks in the last week for this repository"

8. **Select status checks**:
   - ⬜ Leave **Require branches to be up to date before merging** unchecked (unless you want strict mode)
   - In the search box, type your CI check name (e.g., `CI / Validate Code`)
   - Click the check name when it appears to add it
   - Repeat for additional checks (e.g., `Version Check / Check Version Bump`)

   **If no checks appear**: Your workflows haven't run yet. Run your CI at least once, then return to add checks.

#### Setting 3: Additional Protections

9. **Prevent force pushes**:
   - Scroll to **Rules applied to everyone including administrators**
   - ✅ Check **Do not allow force pushes**
   - This prevents history rewriting on main

10. **Prevent deletion**:
    - ✅ Check **Do not allow deletions**
    - This prevents accidental branch deletion

11. **Enforce for administrators** (optional):
    - ⬜ Leave **Do not allow bypassing the above settings** unchecked
    - Recommended: Leave unchecked so admins can handle emergencies
    - If checked, even repository admins must follow all rules

### Save Configuration

12. **Review your settings**:
    - Scroll through the form to verify all checkboxes
    - Ensure status checks are listed under "Status checks that are required"

13. **Save protection rule**:
    - Click **Create** button at bottom of page
    - GitHub applies the rules immediately

### Verify in UI

14. **Confirm protection active**:
    - Go to **Code** tab
    - Look for branch dropdown above file list
    - You should see a small shield icon 🛡️ next to `main`
    - Hover over shield to see "Branch is protected"

15. **View protection details**:
    - Return to **Settings > Branches**
    - Your `main` rule now appears under "Branch protection rules"
    - Click **Edit** to review settings anytime

