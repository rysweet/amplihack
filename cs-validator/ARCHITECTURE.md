# C# Post-Edit Validation Tool - Architecture

This document describes the design and implementation details of the C# validation tool.

## System Overview

The C# validator is a modular validation pipeline designed for speed and extensibility. It coordinates multiple independent validation checks and aggregates results into a unified report.

### Design Goals

1. **Performance**: Complete validation in <5 seconds for typical edits
2. **Accuracy**: Catch 100% of compiler errors, 95%+ of syntax errors
3. **Usability**: Clear, actionable error messages
4. **Extensibility**: Easy to add new validation checks
5. **Integration**: Seamless Claude Code stop hook integration

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   cs-validator.sh                       │
│              (Main Orchestrator)                        │
│                                                         │
│  • Parse CLI arguments                                  │
│  • Load configuration                                   │
│  • Detect modified files                                │
│  • Coordinate validation pipeline                       │
│  • Aggregate results                                    │
│  • Report errors                                        │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    │             │             │             │
    ▼             ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Syntax  │  │  Build  │  │Analyzer │  │ Format  │
│  Check  │  │  Check  │  │  Check  │  │  Check  │
│ (L1)    │  │  (L2)   │  │  (L3)   │  │  (L4)   │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
    │             │             │             │
    │             │             └─────┬───────┘
    │             │                   │
    │             │              (Parallel)
    │             │                   │
    │             ▼                   ▼
    │        ┌─────────────────────────────┐
    │        │     dotnet CLI              │
    │        │  • dotnet build             │
    │        │  • dotnet format            │
    │        └─────────────────────────────┘
    │
    ▼
┌──────────────────────────┐
│   Python AST Parser      │
│ • Syntax validation      │
│ • Pattern matching       │
└──────────────────────────┘
```

## Component Details

### 1. Main Orchestrator (cs-validator.sh)

**Purpose**: Coordinate the validation pipeline and aggregate results.

**Responsibilities**:

- Parse command-line arguments
- Load and validate configuration
- Detect modified C# files using git
- Execute validation checks in order
- Handle timeouts and errors
- Aggregate results into JSON
- Return appropriate exit code

**Key Functions**:

```bash
run_check() {
    # Run a validation check with timeout
    # Parameters: check_name, check_script, files...
    # Returns: 0 on success, non-zero on failure
}

update_result() {
    # Update results JSON with check outcome
    # Parameters: check_name, passed, duration, errors
}
```

**Data Flow**:

1. Load configuration from `~/.amplihack/.claude/config/cs-validator.json`
2. Get modified files from `git diff`
3. Initialize results JSON structure
4. Run checks sequentially (Level 1-2) or parallel (Level 3-4)
5. Update results after each check
6. Report final status

**Exit Codes**:

- `0`: All checks passed
- `1`: Validation failed
- `2`: Configuration error
- `3`: Timeout
- `4`: Missing dependency

### 2. Syntax Check (csharp-syntax-check.py)

**Purpose**: Fast syntax validation using Python parsing.

**Implementation Strategy**:

- Remove strings and comments to avoid false positives
- Check balanced delimiters (braces, parentheses, brackets)
- Pattern matching for common syntax errors
- Validate basic structure (namespace, class declarations)

**Key Functions**:

```python
validate_balanced_delimiters(content, filepath)
    # Check for balanced {}, (), []
    # Returns: list of errors

validate_common_patterns(content, filepath)
    # Check for malformed if/catch/for/while
    # Check for unclosed strings
    # Returns: list of errors

validate_namespace_class_structure(content, filepath)
    # Validate namespace and type declarations
    # Returns: list of errors
```

**Performance**:

- Target: <100ms per file
- Achieved: ~50ms for typical files

**Limitations**:

- Simplified parsing (not full C# parser)
- May miss complex syntax errors
- No semantic validation

### 3. Build Check (build-check.sh)

**Purpose**: Incremental compilation of modified projects.

**Algorithm**:

1. For each modified file, find the containing .csproj
2. Deduplicate projects
3. Build each project with `--no-restore`
4. Capture and parse build output
5. Extract error messages

**Key Features**:

- Only builds affected projects
- Uses `--no-restore` for speed
- Parses error codes (CS####)
- Provides clear error messages with line numbers

**Build Command**:

```bash
dotnet build "$project" \
    --no-restore \
    --nologo \
    --verbosity quiet \
    -p:TreatWarningsAsErrors=false \
    -p:GenerateFullPaths=true
```

**Performance**:

- Target: 2-4 seconds per project
- Achieved: 2-3 seconds for typical projects

### 4. Analyzer Check (analyzer-check.sh)

**Purpose**: Run Roslyn analyzers for code quality.

**Implementation**:

- Uses `dotnet build` with analyzer flags
- Configurable severity threshold
- Filters violations by severity
- Categorizes errors by analyzer (SA, CA, IDE)

**Build Command**:

```bash
dotnet build "$project" \
    --no-restore \
    --nologo \
    --verbosity quiet \
    -p:RunAnalyzers=true \
    -p:EnforceCodeStyleInBuild=true \
    -p:GenerateFullPaths=true
```

**Severity Thresholds**:

- `Error`: Only fail on errors (recommended)
- `Warning`: Fail on warnings and errors
- `Info`: Fail on all analyzer messages

**Performance**:

- Target: 1-3 seconds
- Achieved: 1-2 seconds for typical projects

### 5. Format Check (format-check.sh)

**Purpose**: Verify code formatting compliance.

**Implementation**:

- Uses `dotnet format --verify-no-changes`
- Checks only modified files
- Provides auto-fix instructions
- Works with solution or project files

**Format Command**:

```bash
dotnet format "$target" \
    --verify-no-changes \
    --verbosity quiet \
    --no-restore \
    --include $modified_files
```

**Performance**:

- Target: <1 second
- Achieved: ~500ms

## Data Structures

### Configuration JSON

```json
{
  "enabled": boolean,
  "validationLevel": 1-4,
  "analyzerSeverityThreshold": "Error"|"Warning"|"Info",
  "skipProjects": [glob patterns],
  "timeoutSeconds": number,
  "parallel": boolean,
  "cacheEnabled": boolean,
  "reporting": {
    "format": "json"|"text",
    "verbose": boolean,
    "outputFile": string
  }
}
```

### Results JSON

```json
{
  "timestamp": "ISO8601",
  "passed": boolean,
  "validationLevel": number,
  "executionTimeMs": number,
  "checks": [
    {
      "name": string,
      "passed": boolean,
      "durationMs": number,
      "errors": number
    }
  ],
  "summary": {
    "totalErrors": number,
    "totalWarnings": number,
    "filesChecked": number,
    "projectsBuilt": number
  }
}
```

## Execution Flow

### Sequential Flow (Levels 1-2)

```
1. Parse arguments
2. Load configuration
3. Detect modified files
   ├─ If none → exit 0
   └─ If some → continue
4. Run syntax check
   ├─ If fail → report & exit 1
   └─ If pass → continue
5. Run build check (if level >= 2)
   ├─ If fail → report & exit 1
   └─ If pass → continue
6. Report success & exit 0
```

### Parallel Flow (Levels 3-4)

```
1-5. Same as sequential

6. Start analyzer check (background)
7. Start format check (background, if level 4)
8. Wait for analyzer
9. Wait for format (if running)
10. Check results
    ├─ If any failed → report & exit 1
    └─ If all passed → continue
11. Report success & exit 0
```

## Performance Optimization

### 1. Incremental Building

Only build projects containing modified files:

```bash
# Find unique projects
for file in $MODIFIED_FILES; do
    find_containing_project "$file"
done | sort -u
```

### 2. Parallel Execution

Run independent checks concurrently:

```bash
analyzer-check.sh $FILES &
ANALYZER_PID=$!

format-check.sh $FILES &
FORMAT_PID=$!

wait $ANALYZER_PID || FAILED=1
wait $FORMAT_PID || FAILED=1
```

### 3. Early Exit

Stop at first failure (fail-fast):

```bash
if ! run_check "syntax" csharp-syntax-check.py; then
    exit 1
fi
# Don't run build check if syntax failed
```

### 4. Caching (Future Enhancement)

Cache validation results based on file hash:

```bash
FILE_HASH=$(sha256sum "$file" | cut -d' ' -f1)
if [ -f "$CACHE_DIR/$FILE_HASH.result" ]; then
    # Use cached result
fi
```

## Error Handling

### Error Categories

1. **Configuration Errors** (exit 2):
   - Invalid config file
   - Missing required settings

2. **Dependency Errors** (exit 4):
   - Missing dotnet CLI
   - Missing Python
   - Missing jq

3. **Timeout Errors** (exit 3):
   - Validation exceeds timeout
   - Individual check hangs

4. **Validation Errors** (exit 1):
   - Syntax errors
   - Build errors
   - Analyzer violations
   - Format violations

### Error Recovery

- **Graceful degradation**: Continue without optional tools (jq)
- **Clear messages**: Provide actionable error messages
- **Fallback**: Skip checks if tools unavailable (with warning)

## Security Considerations

### Input Validation

- Validate file paths to prevent injection
- Sanitize git output
- Limit file size for syntax checking

### Command Injection Prevention

```bash
# Use arrays for file lists
FILES=("$@")

# Quote variables
dotnet build "$project"

# Avoid eval
# DON'T: eval "dotnet build $project"
```

### Privilege Management

- Run with user privileges (no sudo)
- No system-wide changes
- Cache files in project directory

## Extensibility

### Adding New Checks

1. Create new check script in `tools/`
2. Follow naming convention: `<name>-check.sh` or `.py`
3. Implement standard interface:
   ```bash
   #!/bin/bash
   # Input: list of files
   # Output: error messages to stdout
   # Exit: 0 on success, 1 on failure
   ```
4. Add to orchestrator:
   ```bash
   if [ "$VALIDATION_LEVEL" -ge 5 ]; then
       run_check "custom" "$SCRIPT_DIR/custom-check.sh"
   fi
   ```

### Adding New Configuration Options

1. Update config schema in `~/.amplihack/.claude/config/cs-validator.json`
2. Parse in orchestrator:
   ```bash
   CUSTOM_OPTION=$(jq -r '.customOption // "default"' "$CONFIG_FILE")
   ```
3. Pass to check scripts as needed

## Testing Strategy

### Unit Tests

Test each component independently:

```bash
# Test syntax checker
python3 -m pytest tools/test_csharp_syntax_check.py

# Test build checker
./tools/test_build_check.sh

# Test format checker
./tools/test_format_check.sh
```

### Integration Tests

Test full pipeline:

```bash
# Test with valid code
./tools/cs-validator.sh --level 4 test/fixtures/valid/

# Test with invalid code
! ./tools/cs-validator.sh --level 4 test/fixtures/invalid/
```

### Performance Tests

Benchmark against targets:

```bash
# Should complete in <5s
time ./tools/cs-validator.sh --level 4
```

## Future Enhancements

### Phase 2: Advanced Features

1. **Smart Caching**
   - Content-based change detection
   - Dependency graph analysis
   - Cross-project caching

2. **Better Error Messages**
   - Code snippets with context
   - Suggested fixes (using Roslyn)
   - Links to documentation

3. **IDE Integration**
   - VS Code extension
   - Real-time validation
   - Inline error display

4. **Metrics and Reporting**
   - Validation history
   - Performance trends
   - Code quality dashboard

### Phase 3: Enterprise Features

1. **Team Configuration**
   - Shared configuration repository
   - Organization-wide rules
   - Team-specific overrides

2. **CI/CD Integration**
   - GitHub Actions workflow
   - Azure Pipelines task
   - Jenkins plugin

3. **Advanced Analysis**
   - Security vulnerability scanning
   - Dependency analysis
   - Code coverage integration

## Troubleshooting

### Common Issues

1. **Slow validation**
   - Solution: Reduce validation level
   - Solution: Skip test projects
   - Solution: Increase timeout

2. **False positives**
   - Solution: Adjust severity threshold
   - Solution: Configure skip patterns
   - Solution: Update analyzer configuration

3. **Missing dependencies**
   - Solution: Install required tools
   - Solution: Update PATH
   - Solution: Use Docker container

## References

- [.NET CLI Documentation](https://docs.microsoft.com/en-us/dotnet/core/tools/)
- [Roslyn Analyzers](https://docs.microsoft.com/en-us/dotnet/fundamentals/code-analysis/overview)
- [dotnet format](https://github.com/dotnet/format)
- [Claude Code Documentation](https://claude.com/claude-code)
