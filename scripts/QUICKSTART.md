# Quick Start - GitHub Pages Link Validator

## Installation

```bash
# Install dependencies
pip install requests beautifulsoup4
```

## Basic Usage

```bash
# Validate your GitHub Pages site
cd scripts
python validate_gh_pages_links.py --site-url https://rysweet.github.io/amplihack/
```

## What It Does

1. **Crawls** your entire GitHub Pages site recursively
2. **Tests** every link it finds (internal and external)
3. **Reports** broken links with location and error details
4. **Exits** with code 1 if broken links found (CI-ready)

## Output

You'll get:

- **Console output**: Human-readable summary
- **JSON file**: `broken_links.json` with complete results

## Example Output

```
GitHub Pages Link Validation Report
============================================================
Scan Date: 2025-12-12T19:30:00Z

Summary:
  Total pages crawled: 42
  Total links checked: 328
  Broken links: 0
  Warnings: 2

✓ All links are valid!

Results saved to broken_links.json
```

## Common Options

```bash
# Increase timeout for slow sites
python validate_gh_pages_links.py --site-url https://example.com --timeout 30

# Limit crawl depth
python validate_gh_pages_links.py --site-url https://example.com --max-depth 5

# Custom output file
python validate_gh_pages_links.py --site-url https://example.com --output my_results.json
```

## CI Integration

The script returns:

- **Exit code 0**: All links valid
- **Exit code 1**: Broken links found

Perfect for GitHub Actions or other CI systems!

## Need Help?

See [README_gh_pages_validator.md](README_gh_pages_validator.md) for complete documentation.
