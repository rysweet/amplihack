# How to Create Your Own Log Analysis Tool

This guide shows you how to create custom log analysis tools following the trace log analyzer pattern.

## Overview

The trace log analyzer demonstrates a reusable pattern for analyzing structured logs to extract insights. You can adapt this pattern for:

- Application logs
- Web server logs
- Database query logs
- Error logs
- Performance metrics
- Any structured log data

## Core Pattern

### 1. Analyzer Class Structure

```python
class MyLogAnalyzer:
    """Analyzes [type] logs for [purpose]."""

    def __init__(self):
        """Initialize with configuration."""
        self.patterns = []  # Define what to look for
        self.filters = []   # Define what to skip

    def parse_log_file(self, file_path: Path) -> List[Dict]:
        """Parse log file and return structured entries."""
        pass

    def extract_data(self, entries: List[Dict]) -> List[Any]:
        """Extract relevant data from entries."""
        pass

    def categorize(self, data: Any) -> List[str]:
        """Categorize data into meaningful buckets."""
        pass

    def analyze(self, log_dir: Path, options: dict) -> Dict[str, Any]:
        """Main analysis orchestration."""
        pass

    def generate_report(self, analysis: Dict, output_path: Path):
        """Generate output report."""
        pass
```

### 2. Main Entry Point

```python
def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(description='Analyze [type] logs')
    parser.add_argument('log_dir', help='Log directory')
    parser.add_argument('--output', '-o', help='Output path')
    parser.add_argument('--sample-size', '-n', type=int, default=10)

    args = parser.parse_args()

    analyzer = MyLogAnalyzer()
    analysis = analyzer.analyze(Path(args.log_dir), vars(args))
    analyzer.generate_report(analysis, Path(args.output))

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Step-by-Step Guide

### Step 1: Define Your Analysis Goals

Ask yourself:

1. What insights do I want to extract?
2. What patterns am I looking for?
3. Who will use this analysis?
4. What actions should the report enable?

**Example for trace logs:**

- Goal: Understand user preferences
- Patterns: Request categories, task verbs, decision patterns
- Users: PM Architect agent, developers
- Actions: Calibrate agent behavior, update preferences

### Step 2: Understand Your Log Format

Examine sample logs to understand structure:

```python
# For JSON logs
with open('sample.json', 'r') as f:
    sample = json.load(f)
    print(json.dumps(sample, indent=2))

# For JSONL logs
with open('sample.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        print(json.dumps(entry, indent=2))
        break

# For plain text logs
with open('sample.log', 'r') as f:
    for i, line in enumerate(f):
        print(f"{i}: {line}")
        if i >= 10:
            break
```

Document the structure:

```
Entry format:
{
  "timestamp": "2025-11-22T14:30:45Z",
  "level": "INFO",
  "field1": "value1",
  "nested": {
    "field2": "value2"
  }
}
```

### Step 3: Create the Parser

Robust parsing handles errors gracefully:

```python
def parse_log_file(self, file_path: Path) -> List[Dict]:
    """Parse log file with error handling."""
    entries = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse based on format (JSON, JSONL, regex, etc.)
                    entry = json.loads(line)  # For JSONL
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping line {line_num}: {e}",
                          file=sys.stderr)
                    continue

    except Exception as e:
        print(f"Error reading {file_path.name}: {e}", file=sys.stderr)

    return entries
```

### Step 4: Extract Relevant Data

Filter and extract what matters:

```python
def extract_data(self, entries: List[Dict]) -> List[Any]:
    """Extract relevant data from entries."""
    extracted = []

    for entry in entries:
        try:
            # Access nested fields safely
            data = entry.get('field1', {})

            # Apply filters
            if self.should_skip(data):
                continue

            # Extract specific fields
            relevant = {
                'timestamp': entry.get('timestamp'),
                'value': data.get('value'),
                'category': data.get('category')
            }

            extracted.append(relevant)

        except Exception:
            # Skip malformed entries
            continue

    return extracted
```

### Step 5: Categorize and Analyze

Group data into meaningful categories:

```python
def categorize(self, data: Any) -> List[str]:
    """Categorize data into buckets."""
    categories = []

    # Pattern matching
    if 'error' in str(data).lower():
        categories.append('error')
    if 'warning' in str(data).lower():
        categories.append('warning')

    # Threshold-based
    if data.get('duration', 0) > 1000:
        categories.append('slow')

    # Regex patterns
    if re.search(r'user_id: \d+', str(data)):
        categories.append('user_action')

    return categories if categories else ['other']

def analyze(self, log_dir: Path, options: dict) -> Dict[str, Any]:
    """Main analysis logic."""
    # Collect files
    log_files = sorted(
        log_dir.glob("*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )[:options.get('sample_size', 10)]

    # Process each file
    all_data = []
    category_counts = Counter()

    for log_file in log_files:
        entries = self.parse_log_file(log_file)
        data = self.extract_data(entries)

        for item in data:
            categories = self.categorize(item)
            for cat in categories:
                category_counts[cat] += 1

        all_data.extend(data)

    # Generate insights
    return {
        'total_entries': len(all_data),
        'categories': category_counts,
        'files_processed': len(log_files),
        # Add more analysis results
    }
```

### Step 6: Generate Report

Create actionable output:

```python
def generate_report(self, analysis: Dict, output_path: Path):
    """Generate markdown report."""
    with open(output_path, 'w') as f:
        f.write(f"# {self.report_title}\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total Entries**: {analysis['total_entries']}\n")
        f.write(f"- **Files Processed**: {analysis['files_processed']}\n\n")

        # Categories
        f.write("## Categories\n\n")
        for category, count in analysis['categories'].most_common():
            pct = (count / analysis['total_entries']) * 100
            f.write(f"- **{category}**: {count} ({pct:.1f}%)\n")
        f.write("\n")

        # Insights
        f.write("## Key Insights\n\n")
        # Generate insights based on thresholds
        if analysis['categories'].get('error', 0) > 100:
            f.write("- High error rate detected\n")

        # Recommendations
        f.write("## Recommendations\n\n")
        f.write("Based on analysis:\n\n")
        f.write("1. [Action item 1]\n")
        f.write("2. [Action item 2]\n")
```

## Example: Web Server Log Analyzer

Complete example for analyzing web server logs:

```python
#!/usr/bin/env python3
"""Analyze web server logs for traffic patterns."""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List


class WebLogAnalyzer:
    """Analyzes web server logs."""

    def __init__(self):
        # Common log format regex
        self.log_pattern = re.compile(
            r'(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\] '
            r'"(?P<method>\w+) (?P<path>[^\s]+) HTTP/[\d.]+" '
            r'(?P<status>\d+) (?P<size>\d+)'
        )

    def parse_log_file(self, file_path: Path) -> List[Dict]:
        """Parse Apache/Nginx common log format."""
        entries = []

        with open(file_path, 'r') as f:
            for line in f:
                match = self.log_pattern.match(line)
                if match:
                    entries.append(match.groupdict())

        return entries

    def analyze(self, log_dir: Path, options: dict) -> Dict:
        """Analyze web logs."""
        log_files = list(log_dir.glob("*.log"))

        all_entries = []
        for log_file in log_files:
            all_entries.extend(self.parse_log_file(log_file))

        # Analysis
        status_codes = Counter(e['status'] for e in all_entries)
        methods = Counter(e['method'] for e in all_entries)
        paths = Counter(e['path'] for e in all_entries)

        # Top IPs
        ips = Counter(e['ip'] for e in all_entries)

        # Error analysis
        errors = [e for e in all_entries if int(e['status']) >= 400]
        error_paths = Counter(e['path'] for e in errors)

        return {
            'total_requests': len(all_entries),
            'status_codes': status_codes,
            'methods': methods,
            'top_paths': paths.most_common(20),
            'top_ips': ips.most_common(10),
            'error_count': len(errors),
            'error_paths': error_paths.most_common(10),
        }

    def generate_report(self, analysis: Dict, output_path: Path):
        """Generate web traffic report."""
        with open(output_path, 'w') as f:
            f.write("# Web Server Log Analysis\n\n")

            f.write(f"**Total Requests**: {analysis['total_requests']}\n")
            f.write(f"**Errors**: {analysis['error_count']}\n\n")

            f.write("## Status Codes\n\n")
            for status, count in analysis['status_codes'].most_common():
                f.write(f"- {status}: {count}\n")

            f.write("\n## Top Paths\n\n")
            for path, count in analysis['top_paths']:
                f.write(f"- {path}: {count} requests\n")

            f.write("\n## Error Paths\n\n")
            for path, count in analysis['error_paths']:
                f.write(f"- {path}: {count} errors\n")


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('log_dir')
    parser.add_argument('--output', default='web_analysis.md')
    args = parser.parse_args()

    analyzer = WebLogAnalyzer()
    analysis = analyzer.analyze(Path(args.log_dir), vars(args))
    analyzer.generate_report(analysis, Path(args.output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Testing Your Analyzer

Create a test suite:

```python
# tests/test_analyzer.py
import pytest
from pathlib import Path
from your_tool import YourAnalyzer


def test_parse_valid_log(tmp_path):
    """Test parsing valid log entries."""
    log_file = tmp_path / "test.log"
    log_file.write_text('{"level": "INFO", "message": "test"}\n')

    analyzer = YourAnalyzer()
    entries = analyzer.parse_log_file(log_file)

    assert len(entries) == 1
    assert entries[0]['level'] == 'INFO'


def test_parse_malformed_log(tmp_path):
    """Test handling of malformed entries."""
    log_file = tmp_path / "test.log"
    log_file.write_text('invalid json\n{"valid": "entry"}\n')

    analyzer = YourAnalyzer()
    entries = analyzer.parse_log_file(log_file)

    # Should skip invalid and parse valid
    assert len(entries) == 1


def test_categorization():
    """Test categorization logic."""
    analyzer = YourAnalyzer()

    error_data = {'level': 'ERROR', 'message': 'failed'}
    categories = analyzer.categorize(error_data)

    assert 'error' in categories


def test_report_generation(tmp_path):
    """Test report output."""
    output = tmp_path / "report.md"
    analysis = {
        'total_entries': 100,
        'categories': Counter({'info': 80, 'error': 20})
    }

    analyzer = YourAnalyzer()
    analyzer.generate_report(analysis, output)

    assert output.exists()
    content = output.read_text()
    assert '100' in content
```

## Integration with Amplihack

### Add Makefile Target

```makefile
analyze-my-logs:
	@python .claude/scenarios/analyze-my-logs/tool.py $(TARGET) $(OPTIONS)
```

### Create Comprehensive Documentation

Follow the template:

1. **README.md** - Usage and examples
2. **HOW_TO_CREATE_YOUR_OWN.md** - This file
3. **tests/** - Test suite
4. **examples/** - Sample usage

### Philosophy Compliance

Ensure your tool follows amplihack principles:

- **Ruthless Simplicity**: One purpose, clearly defined
- **Zero-BS**: No placeholders or incomplete features
- **Modular Design**: Clear inputs and outputs
- **Immediate Value**: Works on first use

## Common Patterns

### Pattern 1: Time-Series Analysis

```python
def analyze_time_series(self, entries: List[Dict]) -> Dict:
    """Analyze patterns over time."""
    by_hour = defaultdict(list)

    for entry in entries:
        timestamp = entry.get('timestamp')
        hour = self.parse_timestamp(timestamp).hour
        by_hour[hour].append(entry)

    return {
        'hourly_distribution': {
            hour: len(entries)
            for hour, entries in by_hour.items()
        }
    }
```

### Pattern 2: Anomaly Detection

```python
def detect_anomalies(self, values: List[float]) -> List[int]:
    """Detect outliers using simple threshold."""
    mean = sum(values) / len(values)
    std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
    threshold = mean + 3 * std

    return [i for i, v in enumerate(values) if v > threshold]
```

### Pattern 3: Correlation Analysis

```python
def find_correlations(self, data: List[Dict]) -> Dict:
    """Find correlated patterns."""
    correlations = defaultdict(Counter)

    for entry in data:
        primary = entry.get('primary_field')
        secondary = entry.get('secondary_field')
        correlations[primary][secondary] += 1

    return correlations
```

## Tips and Best Practices

1. **Start Small**: Begin with simple parsing and basic counts
2. **Handle Errors**: Logs are messy - expect and handle errors
3. **Sample Wisely**: Analyze recent files first, most relevant
4. **Make It Fast**: Use generators for large files
5. **Test Thoroughly**: Test with real, messy log data
6. **Document Well**: Users need to understand the output
7. **Iterate**: Start with MVP, add features based on use

## Graduation Checklist

Before moving from `ai_working/` to `scenarios/`:

- [ ] Tool has clear, single purpose
- [ ] Comprehensive README.md created
- [ ] HOW_TO_CREATE_YOUR_OWN.md written
- [ ] Test suite with >60% coverage
- [ ] Makefile target added
- [ ] Used successfully 2-3 times
- [ ] No breaking changes for 1+ week
- [ ] Follows amplihack philosophy
- [ ] Documentation includes examples
- [ ] Error handling is robust

## Resources

- Trace log analyzer: `~/.amplihack/.claude/scenarios/analyze-trace-logs/tool.py`
- Codebase analyzer: `~/.amplihack/.claude/scenarios/analyze-codebase/tool.py`
- Scenarios pattern: `~/.amplihack/.claude/scenarios/README.md`
- Testing patterns: `pytest` documentation

---

_Remember: The best analyzer is one that provides actionable insights quickly and reliably._
