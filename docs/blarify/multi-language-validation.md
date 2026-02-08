# Multi-Language Validation

Automated validation script for testing Blarify indexing across all supported languages.

## What It Does

`scripts/validate_blarify_languages.py` validates Blarify's indexing capabilities across Python, JavaScript, TypeScript, Go, Rust, C#, and C by testing against real-world open-source repositories.

## Purpose

Ensures Blarify correctly:

- Parses code in all supported languages
- Extracts functions, classes, and relationships
- Handles real-world complexity (not toy examples)
- Maintains consistent quality across language updates

## Running Validation

### Basic Usage

```bash
python scripts/validate_blarify_languages.py
```

Expected output:

```
═══════════════════════════════════════════════════════════
Blarify Multi-Language Validation
═══════════════════════════════════════════════════════════

[1/7] Python (Flask repository)
  ✓ Repository cloned: 150 files
  ✓ Indexing complete: 3.2s
  ✓ Found 45 classes
  ✓ Found 320 functions
  ✓ Zero errors
  PASS

[2/7] JavaScript (React repository)
  ✓ Repository cloned: 280 files
  ✓ Indexing complete: 4.1s
  ✓ Found 85 classes
  ✓ Found 520 functions
  ✓ Zero errors
  PASS

[3/7] TypeScript (TypeScript compiler)
  ✓ Repository cloned: 1,200 files
  ✓ Indexing complete: 12.5s
  ✓ Found 450 classes
  ✓ Found 2,850 functions
  ✓ Zero errors
  PASS

[4/7] Go (Go standard library)
  ✓ Repository cloned: 850 files
  ✓ Indexing complete: 8.3s
  ✓ Found 180 classes (structs)
  ✓ Found 1,650 functions
  ✓ Zero errors
  PASS

[5/7] Rust (Rust compiler)
  ✓ Repository cloned: 3,200 files
  ✓ Indexing complete: 22.1s
  ✓ Found 920 classes (structs/enums)
  ✓ Found 4,100 functions
  ✓ Zero errors
  PASS

[6/7] C# (.NET runtime)
  ✓ Repository cloned: 2,100 files
  ✓ Indexing complete: 15.8s
  ✓ Found 680 classes
  ✓ Found 3,200 functions
  ✓ Zero errors
  PASS

[7/7] C (Linux kernel - drivers/)
  ✓ Repository cloned: 5,400 files
  ✓ Indexing complete: 38.6s
  ✓ Found 1,240 structs
  ✓ Found 8,920 functions
  ✓ Zero errors
  PASS

═══════════════════════════════════════════════════════════
Summary: 7/7 languages PASSED
Total time: 2 minutes 45 seconds

All language validations successful! ✓
═══════════════════════════════════════════════════════════
```

### Options

```bash
# Validate specific language
python scripts/validate_blarify_languages.py --language python

# Verbose output (show all details)
python scripts/validate_blarify_languages.py --verbose

# Skip repository cloning (use existing clones)
python scripts/validate_blarify_languages.py --skip-clone

# Custom output format
python scripts/validate_blarify_languages.py --format json > results.json

# Parallel validation (faster)
python scripts/validate_blarify_languages.py --parallel --workers 4
```

## Language Support Matrix

The validation script tests against these real-world repositories:

| Language   | Repository              | Files | Functions | Classes | Complexity |
| ---------- | ----------------------- | ----- | --------- | ------- | ---------- |
| Python     | pallets/flask           | 150   | 320       | 45      | Medium     |
| JavaScript | facebook/react          | 280   | 520       | 85      | Medium     |
| TypeScript | microsoft/TypeScript    | 1200  | 2850      | 450     | High       |
| Go         | golang/go (stdlib)      | 850   | 1650      | 180     | High       |
| Rust       | rust-lang/rust          | 3200  | 4100      | 920     | Very High  |
| C#         | dotnet/runtime          | 2100  | 3200      | 680     | High       |
| C          | torvalds/linux (subset) | 5400  | 8920      | 1240    | Very High  |

**Repository Selection Criteria:**

- Active maintenance (commits within last 6 months)
- Production quality code
- Diverse coding patterns
- Real-world complexity
- Permissive license (MIT/Apache/GPL)

## Validation Results

### Success Criteria

For each language, validation passes when:

1. **Repository clones successfully** - Network and git operations work
2. **Indexing completes without crashes** - Blarify runs to completion
3. **Minimum code elements found**:
   - Functions: At least 50% of expected count
   - Classes: At least 50% of expected count
4. **Zero critical errors** - No parsing failures on valid syntax
5. **Reasonable performance** - Completes within 3x expected time

### Failure Modes

Validation fails when:

| Failure Type     | Meaning                              | Action                       |
| ---------------- | ------------------------------------ | ---------------------------- |
| Clone failed     | Network issue or repo moved          | Check connectivity, repo URL |
| Indexing timeout | Taking too long (>5 minutes)         | Check system resources       |
| Parse errors     | Can't understand code syntax         | Update parser for language   |
| Low coverage     | Found <50% of expected code elements | Investigate extraction logic |
| Crash            | Blarify terminated unexpectedly      | Debug with --verbose         |

## Interpreting Results

### Per-Language Results

Each language test produces a `ValidationResult`:

```json
{
  "language": "python",
  "success": true,
  "duration_seconds": 3.2,
  "files_indexed": 150,
  "functions_found": 320,
  "classes_found": 45,
  "errors": [],
  "warnings": ["File decorators.py: Complex decorator pattern not fully resolved"],
  "performance_rating": "excellent"
}
```

**Performance Ratings:**

- **Excellent**: Completed in <80% of expected time
- **Good**: Completed in 80-120% of expected time
- **Acceptable**: Completed in 120-200% of expected time
- **Slow**: Completed in 200-300% of expected time
- **Timeout**: Did not complete in 300% of expected time

### Common Warnings

**Non-critical warnings** (test still passes):

```
Warning: Complex generics not fully resolved in TypeScript
Warning: Macro expansions skipped in Rust code
Warning: Conditional compilation ignored in C code
```

These indicate known limitations that don't affect basic functionality.

**Critical errors** (test fails):

```
Error: Syntax error in file main.py line 42
Error: Indexing crashed with segmentation fault
Error: Unable to parse any files in repository
```

These require investigation and fixes.

## Failure Interpretation by Language

### Python Failures

**Common Issues:**

- `SyntaxError`: Usually async/await or match statements (Python 3.10+)
- Low function count: May be missing class methods or decorators
- High error count: Check for dynamic imports or metaclass usage

**Example Diagnostic:**

```bash
python scripts/validate_blarify_languages.py --language python --verbose
```

### TypeScript Failures

**Common Issues:**

- Generic type resolution failures
- Declaration files (.d.ts) not processed
- JSX/TSX syntax errors

**Check TypeScript parser version:**

```bash
blarify --version
# Should show: TypeScript parser v5.0+
```

### Rust Failures

**Common Issues:**

- Macro expansion not handled
- Lifetime annotations confuse parser
- Trait implementations not linked correctly

**Rust requires SCIP:**

```bash
# Install Rust SCIP indexer
cargo install scip-rust
```

### Go Failures

**Common Issues:**

- Embedded interfaces not resolved
- Go generics (1.18+) not supported
- Build tags cause conditional compilation

**Use Go module mode:**

```bash
export GO111MODULE=on
python scripts/validate_blarify_languages.py --language go
```

## Test Repositories

### Local Repository Cache

Validated repositories are cloned to:

```
/tmp/blarify-validation/
├── python-flask/
├── javascript-react/
├── typescript-compiler/
├── go-stdlib/
├── rust-compiler/
├── csharp-runtime/
└── c-linux/
```

Cache persists between runs to speed up validation.

### Custom Repository Testing

Test against your own repository:

```python
from scripts.validate_blarify_languages import validate_repository

result = validate_repository(
    language="python",
    repo_url="https://github.com/myorg/myrepo",
    expected_files=100,
    expected_functions=500,
    expected_classes=50,
)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds}s")
```

## When to Run Validation

Run validation:

1. **Before releases** - Ensure all languages still work
2. **After dependency upgrades** - Parser library updates may break support
3. **When adding language support** - Validate new language works
4. **After major refactoring** - Ensure indexing logic still correct
5. **On language version updates** - New syntax may need parser updates

### Pre-Release Checklist

```bash
# Full validation suite
python scripts/validate_blarify_languages.py --verbose

# Check validation passed
echo $?  # Should be 0

# Generate validation report
python scripts/validate_blarify_languages.py --format json > validation-report.json

# Store report with release
cp validation-report.json releases/v0.9.1/validation.json
```

## CI/CD Integration

Add validation to your CI pipeline:

```yaml
# .github/workflows/validate-blarify.yml
name: Validate Blarify Languages

on:
  pull_request:
    paths:
      - "blarify/**"
      - "scripts/validate_blarify_languages.py"
  schedule:
    - cron: "0 0 * * 0" # Weekly

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install blarify
          npm install -g @sourcegraph/scip-python

      - name: Run validation
        run: |
          python scripts/validate_blarify_languages.py --verbose

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: validation-results
          path: validation-report.json
```

## Performance Benchmarking

Compare indexing performance across languages:

```bash
python scripts/validate_blarify_languages.py --benchmark
```

Output:

```
═══════════════════════════════════════════════════════════
Performance Benchmark
═══════════════════════════════════════════════════════════

Files per second:
  Python:     47 files/sec
  JavaScript: 68 files/sec
  TypeScript: 96 files/sec (with SCIP)
  Go:         102 files/sec
  Rust:       145 files/sec (with SCIP)
  C#:         133 files/sec
  C:          140 files/sec

Functions per second:
  Python:     100 functions/sec
  JavaScript: 127 functions/sec
  TypeScript: 228 functions/sec
  Go:         199 functions/sec
  Rust:       186 functions/sec
  C#:         203 functions/sec
  C:          231 functions/sec

Memory usage (peak):
  Python:     120 MB
  JavaScript: 180 MB
  TypeScript: 450 MB
  Go:         250 MB
  Rust:       680 MB
  C#:         420 MB
  C:          850 MB
═══════════════════════════════════════════════════════════
```

## Troubleshooting

### All Languages Fail

**Check Blarify installation:**

```bash
python -c "import blarify; print(blarify.__version__)"
```

Should output version >= 0.5.0.

**Check SCIP availability:**

```bash
which scip-python scip-typescript scip-rust
```

Missing SCIP causes fallback to slower parsers but shouldn't cause failures.

### Timeout Issues

**Increase timeout:**

```bash
python scripts/validate_blarify_languages.py --timeout 600
```

Default timeout is 300 seconds (5 minutes) per language.

### Network Errors Cloning Repos

**Use local repositories:**

```bash
# Clone repositories manually
git clone https://github.com/pallets/flask /tmp/blarify-validation/python-flask
git clone https://github.com/facebook/react /tmp/blarify-validation/javascript-react

# Run validation with existing repos
python scripts/validate_blarify_languages.py --skip-clone
```

### Inconsistent Results

Validation results may vary due to:

- Repository updates (new commits)
- System resource availability
- Network latency
- SCIP installation differences

**Pin repository versions:**

```python
# In scripts/validate_blarify_languages.py
REAL_WORLD_REPOS = {
    "python": {
        "url": "https://github.com/pallets/flask",
        "commit": "a1b2c3d4",  # Pin to specific commit
        # ...
    }
}
```

### Missing Expected Results

If validation finds fewer functions/classes than expected:

**Check file filtering:**

```bash
# See what files are being indexed
python scripts/validate_blarify_languages.py --language python --verbose | grep "Processing:"
```

**Check for parsing errors:**

```bash
# See detailed error messages
python scripts/validate_blarify_languages.py --language python --verbose | grep "Error:"
```

**Compare with manual indexing:**

```bash
# Index manually and inspect
blarify analyze /tmp/blarify-validation/python-flask --output manual.json
cat manual.json | jq '.functions | length'
```

## See Also

- [Background Indexing Prompt](./background-indexing.md) - Automatic indexing on startup
- [Blarify Quickstart](../blarify_quickstart.md) - Getting started guide
- [Blarify Architecture](../blarify_architecture.md) - How Blarify works internally
