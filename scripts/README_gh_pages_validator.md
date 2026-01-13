# GitHub Pages Link Validator

Automated link validation tool fer GitHub Pages sites. Crawls yer deployed site, tests all links, and reports broken ones.

## Purpose

This tool validates all links on a deployed GitHub Pages site by:

1. Crawling the entire site starting from base URL
2. Following all internal links recursively
3. Testing both internal and external links
4. Generating comprehensive reports of broken links
5. Providing CI-ready exit codes

## Usage

```bash
# Basic usage - validate entire site
python scripts/validate_gh_pages_links.py --site-url https://rysweet.github.io/amplihack/

# Save results to specific file
python scripts/validate_gh_pages_links.py --site-url https://example.github.io/project/ --output results.json

# Increase timeout for slow sites
python scripts/validate_gh_pages_links.py --site-url https://example.com --timeout 30

# Maximum depth limit (default: unlimited)
python scripts/validate_gh_pages_links.py --site-url https://example.com --max-depth 5
```

## Output

The tool generates two types of output:

### 1. JSON Report (`broken_links.json`)

```json
{
  "summary": {
    "total_pages": 42,
    "total_links": 328,
    "broken_links": 3,
    "warnings": 7,
    "scan_date": "2025-12-12T19:30:00Z"
  },
  "broken_links": [
    {
      "page_url": "https://example.com/docs/guide.html",
      "link_url": "https://example.com/missing-page",
      "link_text": "Missing Page",
      "error": "404 Not Found",
      "severity": "error"
    }
  ],
  "warnings": [...]
}
```

### 2. Human-Readable Summary (stdout)

```
GitHub Pages Link Validation Report
=====================================
Scan Date: 2025-12-12 19:30:00 UTC
Base URL: https://rysweet.github.io/amplihack/

Summary:
  Total pages crawled: 42
  Total links checked: 328
  Broken links: 3
  Warnings: 7

Broken Links (Errors):
----------------------
1. Page: /docs/guide.html
   Link: https://example.com/missing-page (Missing Page)
   Error: 404 Not Found

Warnings:
---------
1. Page: /docs/api.html
   Link: https://external-site.com/moved
   Warning: Redirects to https://external-site.com/new-location
```

## Exit Codes

- **0**: All links valid
- **1**: Broken links found (errors only)

Warnings do not cause non-zero exit code.

## CI Integration

```yaml
# .github/workflows/validate-links.yml
name: Validate GitHub Pages Links

on:
  schedule:
    - cron: "0 0 * * 0" # Weekly on Sundays
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4

      - name: Validate links
        run: |
          python scripts/validate_gh_pages_links.py \
            --site-url https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/

      - name: Upload results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: broken-links-report
          path: broken_links.json
```

## Features

- **Recursive crawling**: Follows all internal links automatically
- **Infinite loop protection**: Tracks visited URLs to avoid cycles
- **Rate limiting**: Respects servers with configurable delays
- **Timeout handling**: Gracefully handles slow or unresponsive links
- **Error categorization**: Separates errors from warnings by severity
- **External link validation**: Tests external URLs with proper HTTP requests
- **Anchor validation**: Validates fragment identifiers (#section-name)
- **CI-ready**: Proper exit codes and structured output

## Error Types

| Status    | Severity | Description                         |
| --------- | -------- | ----------------------------------- |
| 404       | Error    | Page not found                      |
| 500       | Error    | Server error                        |
| Timeout   | Warning  | Request timed out                   |
| 301/302   | Warning  | Redirect detected                   |
| 403       | Warning  | Access forbidden (may require auth) |
| SSL Error | Warning  | Certificate issue                   |

## Configuration

Options can be set via command-line arguments:

- `--site-url URL`: Base URL to start crawling (required)
- `--output FILE`: Output JSON file (default: `broken_links.json`)
- `--timeout SECONDS`: Request timeout in seconds (default: 10)
- `--max-depth N`: Maximum crawl depth (default: unlimited)
- `--rate-limit SECONDS`: Delay between requests (default: 0.5)
- `--user-agent STRING`: Custom user agent string

## Philosophy

This tool follows amplihack principles:

- **Zero-BS Implementation**: No stubs, every function works
- **Ruthless Simplicity**: Direct approach without over-engineering
- **Working Code Only**: Fully functional from the start
- **CI-First Design**: Built for automation, not just manual use
- **Clear Error Messages**: Human-readable output for quick fixes

## Example Fix Workflow

When broken links are found:

1. Review the JSON report to identify specific issues
2. For 404 errors: Fix the link or restore the missing page
3. For redirects: Update link to final destination
4. For timeouts: Verify external site is operational
5. Re-run validator to confirm fixes

## Dependencies

- `requests`: HTTP client for testing links
- `beautifulsoup4`: HTML parsing for link extraction

Install with:

```bash
pip install requests beautifulsoup4
```

## Limitations

- Does not execute JavaScript (crawls static HTML only)
- Does not test authentication-protected pages
- Does not validate file downloads (PDFs, images beyond existence)
- Does not check for SEO or accessibility issues

## Future Enhancements

Potential improvements (not currently implemented):

- JavaScript rendering support via Playwright
- Parallel link checking for faster validation
- Historical tracking of link health over time
- Integration with GitHub Issues for automatic bug filing
- Support for sitemap.xml parsing
