# Claude Agent SDK Skill - Drift Detection & Updates

## Drift Detection Strategy

The Agent SDK skill maintains accuracy by detecting when source documentation changes and needs to be re-synced.

### Core Concept

**Drift** occurs when:

1. Source documentation is updated (new features, API changes, deprecated methods)
2. Skill content becomes stale
3. Claude may provide outdated guidance

**Detection Mechanism:**

- Content hashing (SHA-256) of source URLs
- Version tracking in `.metadata/versions.json`
- Automated checking via `scripts/check_drift.py`
- Manual update workflow when drift detected

### Update Frequency

**Recommended Schedule:**

- **Weekly**: Automated drift detection checks
- **Monthly**: Manual review even if no drift detected
- **On-demand**: When SDK releases new versions
- **User-reported**: When inconsistencies found

### Content Hash Tracking

Each source URL has a content hash that changes when source content changes:

```json
{
  "url": "https://docs.claude.com/en/docs/agent-sdk/overview",
  "content_hash": "a7b3c4d5e6f7...",
  "last_checked": "2025-11-15T10:30:00Z",
  "last_changed": "2025-11-01T14:20:00Z"
}
```

**Hash Generation:**

```python
import hashlib
import requests

def generate_content_hash(url: str) -> str:
    """Generate SHA-256 hash of URL content."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    content = response.text.encode('utf-8')
    return hashlib.sha256(content).hexdigest()
```

### Change Detection

**Drift is detected when:**

- Current content hash != stored content hash
- Source URL returns 404 (moved or deleted)
- Fetch fails repeatedly (source unavailable)

**Response Actions:**

1. **Minor drift** (small doc updates): Update affected sections
2. **Major drift** (API changes): Full skill regeneration
3. **Source unavailable**: Mark source as deprecated, seek alternatives

## Detection Implementation

### check_drift.py Script

Location: `~/.amplihack/.claude/skills/agent-sdk/scripts/check_drift.py`

**Core Functionality:**

```python
#!/usr/bin/env python3
"""
Drift detection script for Claude Agent SDK skill.

Checks if source documentation has changed since last sync.
"""

import json
import hashlib
import requests
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def load_metadata(metadata_path: Path) -> dict:
    """Load version metadata."""
    if not metadata_path.exists():
        return {
            "skill_version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "sources": []
        }
    return json.loads(metadata_path.read_text())


def save_metadata(metadata_path: Path, metadata: dict):
    """Save version metadata."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2))


def fetch_content(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch content from URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def generate_hash(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def check_source_drift(source: dict) -> dict:
    """Check if a single source has drifted."""
    url = source["url"]
    stored_hash = source.get("content_hash", "")

    print(f"Checking: {url}")
    content = fetch_content(url)

    if content is None:
        return {
            "url": url,
            "status": "error",
            "message": "Failed to fetch content",
            "drift_detected": False
        }

    current_hash = generate_hash(content)
    has_drifted = current_hash != stored_hash

    return {
        "url": url,
        "status": "ok",
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "drift_detected": has_drifted,
        "last_checked": datetime.now().isoformat()
    }


def check_all_drift(metadata_path: Path) -> Dict[str, any]:
    """Check drift for all sources."""
    metadata = load_metadata(metadata_path)
    sources = metadata.get("sources", [])

    if not sources:
        return {
            "status": "warning",
            "message": "No sources configured",
            "drift_count": 0,
            "results": []
        }

    results = []
    drift_count = 0

    for source in sources:
        result = check_source_drift(source)
        results.append(result)
        if result["drift_detected"]:
            drift_count += 1

    return {
        "status": "drift_detected" if drift_count > 0 else "ok",
        "message": f"{drift_count} of {len(sources)} sources have drifted",
        "drift_count": drift_count,
        "total_sources": len(sources),
        "results": results,
        "checked_at": datetime.now().isoformat()
    }


def update_metadata_hashes(metadata_path: Path, drift_results: dict):
    """Update metadata with new content hashes."""
    metadata = load_metadata(metadata_path)

    for result in drift_results["results"]:
        if result["status"] == "ok":
            # Find and update source
            for source in metadata["sources"]:
                if source["url"] == result["url"]:
                    source["content_hash"] = result["current_hash"]
                    source["last_checked"] = result["last_checked"]
                    if result["drift_detected"]:
                        source["last_changed"] = result["last_checked"]

    metadata["last_updated"] = datetime.now().isoformat()
    save_metadata(metadata_path, metadata)


def main():
    """Main CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check for drift in Claude Agent SDK skill sources"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(__file__).parent.parent / ".metadata" / "versions.json",
        help="Path to versions.json metadata file"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update metadata with new hashes after checking"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Check drift
    results = check_all_drift(args.metadata)

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Drift Detection Report - {results['checked_at']}")
        print(f"{'='*60}\n")

        for result in results["results"]:
            status_symbol = "✓" if not result["drift_detected"] else "⚠"
            print(f"{status_symbol} {result['url']}")
            if result["drift_detected"]:
                print(f"  Drift detected: hash changed")
                print(f"  Stored:  {result.get('stored_hash', 'N/A')[:16]}...")
                print(f"  Current: {result.get('current_hash', 'N/A')[:16]}...")
            print()

        print(f"{'='*60}")
        print(f"Summary: {results['message']}")
        print(f"{'='*60}\n")

    # Update metadata if requested
    if args.update:
        update_metadata_hashes(args.metadata, results)
        print("Metadata updated with current hashes.")

    # Exit code: 0 if no drift, 1 if drift detected
    sys.exit(0 if results["drift_count"] == 0 else 1)


if __name__ == "__main__":
    main()
```

### Usage Examples

**Check for drift:**

```bash
python scripts/check_drift.py
```

**Check and update metadata:**

```bash
python scripts/check_drift.py --update
```

**JSON output for automation:**

```bash
python scripts/check_drift.py --json
```

**Custom metadata location:**

```bash
python scripts/check_drift.py --metadata /path/to/versions.json
```

## Update Workflow

### 6-Step Update Process

When drift is detected, follow this systematic workflow:

**Step 1: Verify Drift**

```bash
cd .claude/skills/agent-sdk
python scripts/check_drift.py
```

Review which sources have changed and assess impact.

**Step 2: Fetch Updated Content**

```bash
# For each drifted source, fetch new content
curl https://docs.claude.com/en/docs/agent-sdk/overview > /tmp/new_content.html
```

Or use WebFetch in Claude Code:

```
Use WebFetch to fetch the updated content from each drifted URL
```

**Step 3: Analyze Changes**
Compare old and new content to understand:

- What changed? (new features, deprecated APIs, examples)
- Impact level? (minor docs update vs major API change)
- Which skill files need updates? (SKILL.md, reference.md, examples.md, patterns.md)

**Step 4: Update Skill Files**
Update affected files with new information:

- SKILL.md: Update overview, quick start if API changed
- reference.md: Update API reference, add new features
- examples.md: Update examples, add new patterns
- patterns.md: Update best practices if patterns changed

**Step 5: Validate Updates**
Run self-validation checks:

```bash
# Check token counts
wc -w *.md

# Validate markdown syntax
markdownlint *.md

# Test code examples (if possible)
python -m doctest examples.md
```

**Step 6: Update Metadata**

```bash
# Update metadata with new hashes
python scripts/check_drift.py --update

# Update version number in SKILL.md frontmatter
# Increment patch for minor changes (1.0.0 -> 1.0.1)
# Increment minor for new features (1.0.0 -> 1.1.0)
# Increment major for breaking changes (1.0.0 -> 2.0.0)
```

### Validation Checklist

After updates, verify:

- [ ] All source URLs still accessible
- [ ] Content hashes updated in versions.json
- [ ] Version number incremented appropriately
- [ ] Token counts within budgets (SKILL.md < 5000 tokens)
- [ ] All internal links work
- [ ] Code examples syntactically valid
- [ ] No contradictions between files
- [ ] Frontmatter YAML valid

## Self-Validation

### Completeness Checks

**Source Coverage:**

```python
def validate_source_coverage(skill_content: str, sources: List[str]) -> bool:
    """Verify all sources are referenced in skill."""
    for source in sources:
        domain = extract_domain(source)
        if domain not in skill_content:
            print(f"Warning: Source {source} not referenced")
            return False
    return True
```

**Required Sections:**

```python
REQUIRED_SECTIONS = {
    "SKILL.md": [
        "Overview",
        "Quick Start",
        "Core Concepts Reference",
        "Common Patterns",
        "Navigation Guide"
    ],
    "reference.md": [
        "Architecture",
        "Setup & Configuration",
        "Tools System",
        "Permissions & Security",
        "Hooks Reference",
        "Skills System"
    ],
    "examples.md": [
        "Basic Agent Examples",
        "Tool Implementations",
        "Hook Implementations",
        "Advanced Patterns"
    ],
    "patterns.md": [
        "Agent Loop Patterns",
        "Context Management",
        "Tool Design",
        "Security Patterns",
        "Performance",
        "Anti-Patterns"
    ]
}

def validate_sections(file_path: Path, required: List[str]) -> bool:
    """Check all required sections present."""
    content = file_path.read_text()
    for section in required:
        if f"## {section}" not in content and f"### {section}" not in content:
            print(f"Missing section in {file_path.name}: {section}")
            return False
    return True
```

### Token Validation

**Token Budget Enforcement:**

```python
def count_tokens_approximate(text: str) -> int:
    """Approximate token count (words * 1.3)."""
    return int(len(text.split()) * 1.3)

def validate_token_budget(file_path: Path, max_tokens: int) -> bool:
    """Check file doesn't exceed token budget."""
    content = file_path.read_text()
    tokens = count_tokens_approximate(content)

    if tokens > max_tokens:
        print(f"{file_path.name} exceeds budget: {tokens} > {max_tokens}")
        return False

    print(f"{file_path.name}: {tokens}/{max_tokens} tokens")
    return True

# Budgets from frontmatter
BUDGETS = {
    "SKILL.md": 4500,
    "reference.md": 6000,
    "examples.md": 4000,
    "patterns.md": 3500,
    "drift-detection.md": 2000
}
```

### Link Verification

**Internal Links:**

```python
def validate_internal_links(skill_dir: Path) -> bool:
    """Verify all internal markdown links exist."""
    import re

    for md_file in skill_dir.glob("*.md"):
        content = md_file.read_text()
        links = re.findall(r'\[.*?\]\((.*?\.md.*?)\)', content)

        for link in links:
            # Remove anchors
            target = link.split('#')[0]
            if target and not (skill_dir / target).exists():
                print(f"Broken link in {md_file.name}: {link}")
                return False

    return True
```

### Example Validation

**Code Syntax:**

````python
def validate_code_examples(file_path: Path) -> bool:
    """Extract and validate Python code blocks."""
    import ast
    import re

    content = file_path.read_text()
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)

    for i, code in enumerate(code_blocks):
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"Syntax error in {file_path.name} code block {i+1}: {e}")
            return False

    return True
````

## Continuous Improvement

### Feedback Loop

**User Feedback Integration:**

1. Monitor usage patterns (which files accessed most)
2. Track questions about Agent SDK (skill gaps)
3. Collect error reports (inaccurate info)
4. Update skill based on feedback

**Metrics to Track:**

- Skill activation frequency
- Which supporting files accessed
- User satisfaction (implicit from continued use)
- Drift detection frequency

### Version History

Maintain changelog of skill updates:

```markdown
## Version History

### 1.0.0 (2025-11-15)

- Initial skill creation
- Comprehensive coverage of 5 source URLs
- Drift detection mechanism implemented

### 1.0.1 (Future)

- Minor doc updates
- Bug fixes in examples
- Performance improvements

### 1.1.0 (Future)

- New Agent SDK features added
- Additional patterns
- Extended examples
```

### Future Enhancements

**Planned Improvements:**

1. Automated weekly drift detection via CI/CD
2. Smart diff analysis (show exactly what changed)
3. Automated partial updates for minor drifts
4. Integration with Anthropic SDK changelog
5. Community contribution process for patterns
