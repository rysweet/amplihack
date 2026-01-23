# Check Broken Links

Automated link checker for documentation sites and markdown files.

## Purpose

The check-broken-links tool validates all links in documentation to ensure they're accessible and functional. It catches broken internal links, dead external URLs, and malformed references before they frustrate users.

**Why this tool exists:**

- Documentation links rot over time as sites move or disappear
- Broken links damage trust and waste user time
- Manual link checking doesn't scale across large documentation sites
- CI integration catches broken links before they reach production

## Prerequisites

**Required:**

- Node.js (version 14+)
- npm (usually comes with Node.js)
- linkinator package (installed automatically)

**Check prerequisites:**

```bash
node --version    # Should show v14 or higher
npm --version     # Should show 6.0 or higher
```

**Install Node.js if missing:**

- macOS: `brew install node`
- Ubuntu/Debian: `sudo apt install nodejs npm`
- Other platforms: https://nodejs.org/

## Installation

The tool is part of amplihack scenarios. No separate installation needed.

**Verify tool is available:**

```bash
make list-scenarios | grep check-broken-links
```

## Usage

### Quick Start

**Check a documentation site:**

```bash
python .claude/scenarios/check-broken-links/link_checker.py https://rysweet.github.io/amplihack/
```

**Check local markdown files:**

```bash
python .claude/scenarios/check-broken-links/link_checker.py ./docs/
```

### Via Python CLI (Recommended)

**Basic usage:**

```bash
python .claude/scenarios/check-broken-links/link_checker.py <url-or-path>
```

**With options:**

```bash
python .claude/scenarios/check-broken-links/link_checker.py https://example.com --timeout 10000 --recurse
```

**Common options:**

- `--timeout <ms>` - Request timeout in milliseconds (default: 5000)
- `--recurse` - Follow links recursively
- `--skip <pattern>` - Skip URLs matching pattern
- `--format <json|csv|pretty>` - Output format (default: pretty)

### Via Python API

**Check a website:**

```python
from claude.scenarios.check_broken_links.link_checker import check_site

report = check_site(
    url="https://rysweet.github.io/amplihack/",
    timeout=5000
)

print(f"Total links: {report.total_links}")
print(f"Broken links: {report.broken_count}")
print(f"Status: {'✓ PASS' if report.is_healthy else '✗ FAIL'}")
```

**Check local files:**

```python
from pathlib import Path
from claude.scenarios.check_broken_links.link_checker import check_local

report = check_local(Path("./docs"))

for broken_link in report.broken_links:
    print(f"{broken_link.source_file}:{broken_link.line_number}")
    print(f"  → {broken_link.url} ({broken_link.status_code})")
```

**Categorize link failures:**

```python
from claude.scenarios.check_broken_links.link_checker import categorize_links

categories = categorize_links(report)

print(f"404 Not Found: {len(categories['404'])}")
print(f"Timeouts: {len(categories['timeout'])}")
print(f"DNS failures: {len(categories['dns_error'])}")
```

## Output Format

**Pretty format (default):**

```
Link Check Report
=================
Target: https://rysweet.github.io/amplihack/
Status: ✓ PASS

Summary:
  Total links checked: 247
  Successful: 245 (99.2%)
  Broken: 2 (0.8%)
  Warnings: 0

Broken Links:
  1. https://github.com/org/deleted-repo
     Status: 404 Not Found
     Found in: docs/references.md:42

  2. https://slow-api.example.com/endpoint
     Status: Timeout (5000ms)
     Found in: docs/integrations.md:18
```

**JSON format:**

```json
{
  "target": "https://rysweet.github.io/amplihack/",
  "timestamp": "2025-12-18T10:30:00Z",
  "total_links": 247,
  "successful": 245,
  "broken": 2,
  "warnings": 0,
  "is_healthy": false,
  "broken_links": [
    {
      "url": "https://github.com/org/deleted-repo",
      "status_code": 404,
      "status_text": "Not Found",
      "source_file": "docs/references.md",
      "line_number": 42
    }
  ]
}
```

## Exit Codes

The tool returns standard exit codes for scripting:

- `0` - All links valid (or warnings only)
- `1` - Broken links found
- `2` - Tool error (missing prerequisites, invalid target)

**Use in CI:**

```bash
#!/bin/bash
python .claude/scenarios/check-broken-links/link_checker.py https://example.com
if [ $? -ne 0 ]; then
    echo "Documentation has broken links - failing build"
    exit 1
fi
```

## Integration with amplihack Workflow

**Step 9: Verify Documentation Links (DEFAULT_WORKFLOW)**

Before finalizing PRs, check documentation:

```bash
# Check GitHub Pages deployment
python .claude/scenarios/check-broken-links/link_checker.py https://rysweet.github.io/amplihack/

# Check local docs before commit
python .claude/scenarios/check-broken-links/link_checker.py ./docs/
```

**Pre-commit hook:**

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -q "^docs/"; then
    echo "Checking documentation links..."
    python .claude/scenarios/check-broken-links/link_checker.py ./docs/
fi
```

## Troubleshooting

### "linkinator command not found"

**Problem:** npm package not installed globally.

**Solution:**

```bash
npm install -g linkinator
```

Or let amplihack install it automatically on first run.

### "Connection timeout" errors

**Problem:** Remote site is slow or blocking automated requests.

**Solution:** Increase timeout:

```bash
python .claude/scenarios/check-broken-links/link_checker.py https://slow-site.com --timeout 10000
```

### False positives for valid links

**Problem:** Site blocks automated crawlers or requires authentication.

**Solution:** Skip problematic domains:

```bash
python .claude/scenarios/check-broken-links/link_checker.py https://example.com --skip "internal-auth.example.com/*"
```

### Too many warnings about redirects

**Problem:** Links use HTTP instead of HTTPS, causing redirects.

**Solution:** Update documentation to use HTTPS directly. The tool flags redirects as warnings to encourage canonical URLs.

## Common Use Cases

### Check before deployment

```bash
# Validate all docs before pushing to production
python .claude/scenarios/check-broken-links/link_checker.py ./docs/
git add docs/
git commit -m "fix: Update broken documentation links"
```

### Verify external references

```bash
# Check only external links (not internal site navigation)
python .claude/scenarios/check-broken-links/link_checker.py https://example.com --skip "example.com/*"
```

### Generate CI report

```bash
# JSON output for parsing in CI systems
python .claude/scenarios/check-broken-links/link_checker.py ./docs/ --format json > link-report.json
```

## Philosophy Alignment

**Ruthless Simplicity:**

- Delegates to linkinator (battle-tested npm package)
- Thin Python wrapper for amplihack integration
- No reinventing link checking logic

**Zero-BS Implementation:**

- Real link checking from day one (no stubs)
- Direct Python CLI integration
- Runnable examples that execute successfully

**Brick Philosophy:**

- Self-contained module with clear public API
- Standard interface for both CLI and Python usage
- Regeneratable from specification

## Next Steps

1. **Run initial check:** `python .claude/scenarios/check-broken-links/link_checker.py ./docs/`
2. **Fix broken links:** Update URLs in documentation files
3. **Add to CI:** Include link checking in GitHub Actions
4. **Regular audits:** Run monthly to catch link rot

## References

- linkinator documentation: https://github.com/JustinBeckwith/linkinator
- amplihack scenarios pattern: `~/.amplihack/.claude/scenarios/README.md`
- Eight Rules of Documentation: `~/.amplihack/.claude/context/PHILOSOPHY.md`
