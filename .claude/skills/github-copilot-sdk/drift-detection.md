# Drift Detection: GitHub Copilot SDK Versions

Guide for detecting SDK version changes, monitoring updates, and maintaining skill accuracy.

## What is Drift?

**Drift** occurs when this skill's documentation becomes outdated due to SDK updates:
- New features added to SDK
- API signatures changed
- Deprecated methods removed
- Breaking changes in major versions
- New languages supported

**Impact:** Skill provides incorrect guidance → failed code generation → wasted time

## Detection Strategy

### Three-Layer Monitoring

1. **Official releases** (authoritative source)
2. **Package registries** (actual distributions)
3. **Community signals** (real-world issues)

## Monitoring Sources

### 1. GitHub Releases (Primary Source)

**Monitor:**
- https://github.com/github/copilot-sdk/releases
- Release notes and changelogs
- Breaking change announcements

**Check frequency:** Weekly

**What to extract:**
- Version number (semver)
- Release date
- New features
- Breaking changes
- Deprecation notices

### 2. Package Registries (Distribution Points)

**Python (PyPI):**
```bash
# Check latest version
pip index versions github-copilot-sdk

# Compare with documented version
# Current skill documents: 1.x.x
```

**TypeScript (npm):**
```bash
# Check latest version
npm view @github/copilot-sdk version

# View all versions
npm view @github/copilot-sdk versions
```

**Go (pkg.go.dev):**
```bash
# Check latest version
go list -m -versions github.com/github/copilot-sdk-go

# Or check: https://pkg.go.dev/github.com/github/copilot-sdk-go
```

**.NET (NuGet):**
```bash
# Check latest version
dotnet package search GitHub.Copilot.SDK

# Or check: https://www.nuget.org/packages/GitHub.Copilot.SDK
```

**Check frequency:** Weekly (automated)

### 3. Community Signals (Early Warnings)

**Monitor:**
- GitHub Issues (bug reports, feature requests)
- Stack Overflow questions
- GitHub Discussions
- Social media mentions (Twitter, Reddit)

**Check frequency:** Bi-weekly

**Red flags:**
- Multiple issues about same problem
- "Not working with latest version" reports
- New feature requests becoming common
- Documentation complaints

## Automated Drift Detection Script

### CI-Ready Drift Detector

Save as `.github/workflows/skill-drift-check.yml`:

```yaml
name: SDK Drift Detection
on:
  schedule:
    - cron: '0 0 * * 1'  # Every Monday at midnight
  workflow_dispatch:

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check Python SDK version
        id: python-check
        run: |
          LATEST=$(pip index versions github-copilot-sdk 2>/dev/null | grep -oP 'github-copilot-sdk \(\K[^)]+' | head -1)
          DOCUMENTED=$(grep -oP 'github-copilot-sdk==\K[^\s]+' .claude/skills/github-copilot-sdk/reference.md | head -1)
          echo "latest=$LATEST" >> $GITHUB_OUTPUT
          echo "documented=$DOCUMENTED" >> $GITHUB_OUTPUT
          
      - name: Check TypeScript SDK version
        id: typescript-check
        run: |
          LATEST=$(npm view @github/copilot-sdk version)
          DOCUMENTED=$(grep -oP '@github/copilot-sdk@\K[^\s]+' .claude/skills/github-copilot-sdk/reference.md | head -1)
          echo "latest=$LATEST" >> $GITHUB_OUTPUT
          echo "documented=$DOCUMENTED" >> $GITHUB_OUTPUT
          
      - name: Check for drift
        run: |
          python3 << 'EOF'
          import os
          from packaging import version
          
          drift_detected = False
          
          # Python check
          py_latest = os.environ.get('PYTHON_LATEST', '0.0.0')
          py_doc = os.environ.get('PYTHON_DOCUMENTED', '0.0.0')
          if version.parse(py_latest) > version.parse(py_doc):
              print(f"⚠️  Python SDK drift: {py_doc} → {py_latest}")
              drift_detected = True
          
          # TypeScript check
          ts_latest = os.environ.get('TS_LATEST', '0.0.0')
          ts_doc = os.environ.get('TS_DOCUMENTED', '0.0.0')
          if version.parse(ts_latest) > version.parse(ts_doc):
              print(f"⚠️  TypeScript SDK drift: {ts_doc} → {ts_latest}")
              drift_detected = True
          
          if drift_detected:
              print("\n🔔 Skill update required!")
              exit(1)
          else:
              print("✅ No drift detected")
          EOF
        env:
          PYTHON_LATEST: ${{ steps.python-check.outputs.latest }}
          PYTHON_DOCUMENTED: ${{ steps.python-check.outputs.documented }}
          TS_LATEST: ${{ steps.typescript-check.outputs.latest }}
          TS_DOCUMENTED: ${{ steps.typescript-check.outputs.documented }}
          
      - name: Create issue on drift
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🔔 GitHub Copilot SDK Drift Detected',
              body: `Automated drift detection found version mismatches:\n\n` +
                    `- Python: ${{ steps.python-check.outputs.documented }} → ${{ steps.python-check.outputs.latest }}\n` +
                    `- TypeScript: ${{ steps.typescript-check.outputs.documented }} → ${{ steps.typescript-check.outputs.latest }}\n\n` +
                    `Please review and update the skill documentation.`,
              labels: ['skill-maintenance', 'drift-detected']
            })
```

### Local Drift Check Script

Save as `scripts/check-sdk-drift.py`:

```python
#!/usr/bin/env python3
"""
Local drift detection for GitHub Copilot SDK versions.
Run before committing skill changes.
"""

import json
import subprocess
import sys
from datetime import datetime
from packaging import version


def get_pypi_version(package: str) -> str:
    """Get latest version from PyPI."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", package],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Parse output: "package (1.2.3)"
        for line in result.stdout.split('\n'):
            if package in line:
                return line.split('(')[1].split(')')[0].strip()
    except Exception as e:
        print(f"❌ Failed to check PyPI: {e}")
    return "0.0.0"


def get_npm_version(package: str) -> str:
    """Get latest version from npm."""
    try:
        result = subprocess.run(
            ["npm", "view", package, "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ Failed to check npm: {e}")
    return "0.0.0"


def get_documented_version(file_path: str, pattern: str) -> str:
    """Extract version from documentation file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            # Simple pattern matching - enhance as needed
            import re
            match = re.search(pattern, content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"❌ Failed to read docs: {e}")
    return "0.0.0"


def check_github_releases(repo: str) -> dict:
    """Check GitHub releases via API."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://api.github.com/repos/{repo}/releases/latest"],
            capture_output=True,
            text=True,
            timeout=10
        )
        data = json.loads(result.stdout)
        return {
            "version": data.get("tag_name", "").lstrip('v'),
            "published_at": data.get("published_at", ""),
            "url": data.get("html_url", "")
        }
    except Exception as e:
        print(f"❌ Failed to check GitHub: {e}")
    return {}


def main():
    print("🔍 Checking GitHub Copilot SDK drift...\n")
    
    skill_dir = ".claude/skills/github-copilot-sdk"
    drift_found = False
    
    # Python SDK check
    print("📦 Python SDK (PyPI):")
    py_latest = get_pypi_version("github-copilot-sdk")
    py_documented = get_documented_version(
        f"{skill_dir}/reference.md",
        r"github-copilot-sdk==([0-9.]+)"
    )
    
    print(f"   Latest: {py_latest}")
    print(f"   Documented: {py_documented}")
    
    if version.parse(py_latest) > version.parse(py_documented):
        print("   ⚠️  DRIFT DETECTED")
        drift_found = True
    else:
        print("   ✅ Up to date")
    print()
    
    # TypeScript SDK check
    print("📦 TypeScript SDK (npm):")
    ts_latest = get_npm_version("@github/copilot-sdk")
    ts_documented = get_documented_version(
        f"{skill_dir}/reference.md",
        r"@github/copilot-sdk@([0-9.]+)"
    )
    
    print(f"   Latest: {ts_latest}")
    print(f"   Documented: {ts_documented}")
    
    if version.parse(ts_latest) > version.parse(ts_documented):
        print("   ⚠️  DRIFT DETECTED")
        drift_found = True
    else:
        print("   ✅ Up to date")
    print()
    
    # GitHub releases check
    print("📦 GitHub Releases:")
    release_info = check_github_releases("github/copilot-sdk")
    if release_info:
        print(f"   Latest release: {release_info['version']}")
        print(f"   Published: {release_info['published_at']}")
        print(f"   URL: {release_info['url']}")
    print()
    
    # Summary
    print("=" * 50)
    if drift_found:
        print("🔔 DRIFT DETECTED - Skill update required")
        print("\nNext steps:")
        print("1. Review release notes for breaking changes")
        print("2. Update reference.md with new versions")
        print("3. Update examples.md if APIs changed")
        print("4. Update patterns.md if best practices changed")
        print("5. Run validation tests")
        print("6. Update VALIDATION_REPORT.md")
        return 1
    else:
        print("✅ No drift detected - Skill is up to date")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable:
```bash
chmod +x scripts/check-sdk-drift.py
```

## Update Workflow

### When Drift is Detected

**1. Assess Impact (5 minutes)**
   - Read release notes
   - Identify breaking changes
   - Check if documented features affected

**2. Categorize Change**
   - **Patch (1.0.0 → 1.0.1):** Bug fixes only → Low priority
   - **Minor (1.0.0 → 1.1.0):** New features → Medium priority
   - **Major (1.0.0 → 2.0.0):** Breaking changes → High priority

**3. Update Documentation (varies)**

**For patch versions:**
- Update version numbers in reference.md
- Run validation tests
- Update VALIDATION_REPORT.md

**For minor versions:**
- Update version numbers
- Add new features to reference.md
- Add examples for new features to examples.md
- Update VALIDATION_REPORT.md

**For major versions:**
- Full skill review required
- Update all files for breaking changes
- Rewrite affected examples
- Update patterns if best practices changed
- Consider adding migration guide
- Full validation test suite

**4. Validate Changes**
```bash
# Run drift check
python3 scripts/check-sdk-drift.py

# Validate skill quality
python3 scripts/validate-skill.py github-copilot-sdk

# Test examples still work
# (manual or automated depending on setup)
```

**5. Document Update**
Update VALIDATION_REPORT.md:
```markdown
## Last Update
- Date: 2024-01-15
- SDK Version: 2.0.0
- Changed files: reference.md, examples.md, patterns.md
- Breaking changes: Yes
- Migration guide added: Yes
```

## Preventing Drift

### Proactive Measures

**1. Version pinning in examples:**
```python
# Bad - will break when SDK updates
pip install github-copilot-sdk

# Good - explicitly versioned
pip install github-copilot-sdk==1.2.3
```

**2. Regular review schedule:**
- Weekly: Check package registries
- Bi-weekly: Review GitHub issues/discussions
- Monthly: Full skill validation
- Quarterly: Deep review and improvement

**3. Automated alerts:**
- GitHub Actions workflow (above)
- Dependabot for skill dependencies
- RSS feed for GitHub releases

**4. Changelog monitoring:**
Create `.github/workflows/changelog-watch.yml`:
```yaml
name: Watch SDK Changelog
on:
  schedule:
    - cron: '0 0 * * *'  # Daily
    
jobs:
  check-changelog:
    runs-on: ubuntu-latest
    steps:
      - name: Check for new releases
        run: |
          # Fetch latest release
          # Compare with last known
          # Alert if different
```

## Emergency Drift Response

### When Skill is Suddenly Outdated

**Scenario:** Major SDK release with breaking changes, skill now generates broken code.

**Immediate actions (< 1 hour):**
1. Add warning to SKILL.md top:
   ```markdown
   > ⚠️ **WARNING:** SDK version 2.0.0 released with breaking changes.
   > This skill is being updated. Use version 1.x.x until updated.
   ```

2. Pin versions in all examples to last working version

3. Create GitHub issue tracking update progress

**Short-term (< 1 day):**
1. Review breaking changes in detail
2. Update reference.md with new APIs
3. Fix examples in examples.md
4. Test all code samples

**Complete resolution (< 1 week):**
1. Full skill validation
2. Update all documentation files
3. Add migration guide if needed
4. Remove warning banner
5. Publish update

## Metrics to Track

### Drift Health Score

Track in VALIDATION_REPORT.md:

```markdown
## Drift Metrics
- Days since last SDK release: 15
- Days since last skill update: 10
- Version delta: 0.1.0 (minor)
- Breaking changes pending: 0
- New features undocumented: 2
- **Health score: 85/100** (Good)
```

**Scoring:**
- 90-100: Excellent (< 1 week behind)
- 80-89: Good (< 2 weeks behind)
- 70-79: Fair (< 1 month behind)
- < 70: Poor (> 1 month behind or breaking changes)

## Conclusion

**Key takeaways:**
1. Automate drift detection with CI
2. Respond to major versions within 1 week
3. Regular maintenance prevents emergency fixes
4. Document all updates in VALIDATION_REPORT.md

**Quick command:**
```bash
# Run before committing skill changes
python3 scripts/check-sdk-drift.py && echo "✅ Skill is current"
```
