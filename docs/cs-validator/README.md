# C# Post-Edit Validation Tool

Automated validation tool that runs after C# file edits to catch compiler warnings, errors, and code quality issues before commit. Designed for seamless integration with Claude Code stop hooks.

## Features

- **Fast Syntax Validation**: Parse C# files for common syntax errors in <100ms
- **Incremental Build Checking**: Compile only affected projects in <3 seconds
- **Code Quality Analysis**: Run Roslyn analyzers to catch code smells
- **Format Verification**: Ensure code follows formatting standards
- **Parallel Execution**: Run independent checks concurrently for speed
- **Configurable Levels**: Choose validation depth based on your needs
- **Clear Error Reporting**: Get actionable error messages with file locations

## Quick Start

### Installation

1. Clone this repository or copy the `tools/` directory to your project
2. Copy the example stop hook:
   ```bash
   cp .claude/hooks/stop.sh.example .claude/hooks/stop.sh
   chmod +x .claude/hooks/stop.sh
   ```
3. Make scripts executable:
   ```bash
   chmod +x tools/*.sh tools/*.py
   ```
4. Ensure dependencies are installed:
   - Python 3.8+
   - .NET SDK 6.0+
   - jq (for JSON processing)

### Basic Usage

Run validation manually on modified files:

```bash
./tools/cs-validator.sh
```

Run with specific validation level:

```bash
./tools/cs-validator.sh --level 3
```

Run with verbose output:

```bash
./tools/cs-validator.sh --verbose
```

### Validation Levels

Choose the appropriate level based on your needs:

| Level | Checks                     | Speed  | Use Case                              |
| ----- | -------------------------- | ------ | ------------------------------------- |
| 1     | Syntax only                | <100ms | Quick pre-commit check                |
| 2     | Syntax + Build             | <3s    | **Recommended** - Catches most errors |
| 3     | Syntax + Build + Analyzers | <5s    | Ensure code quality                   |
| 4     | All + Format               | <5s    | Strict validation before PR           |

## Configuration

Edit `~/.amplihack/.claude/config/cs-validator.json` to customize behavior:

```json
{
  "enabled": true,
  "validationLevel": 2,
  "analyzerSeverityThreshold": "Error",
  "skipProjects": ["Tests/**/*.csproj"],
  "timeoutSeconds": 30,
  "parallel": true,
  "cacheEnabled": true,
  "reporting": {
    "format": "json",
    "verbose": false,
    "outputFile": ".cache/cs-validator/last-run.json"
  }
}
```

### Configuration Options

- **validationLevel**: Set default level (1-4)
- **analyzerSeverityThreshold**: `"Error"`, `"Warning"`, or `"Info"`
- **skipProjects**: Glob patterns for projects to skip
- **timeoutSeconds**: Maximum time for entire validation
- **parallel**: Enable concurrent execution of independent checks
- **cacheEnabled**: Cache results for unchanged files (coming soon)

## Integration with Claude Code

### Stop Hook Integration

The validator automatically runs after Claude Code edits when integrated as a stop hook:

1. **Copy the example hook**:

   ```bash
   cp .claude/hooks/stop.sh.example .claude/hooks/stop.sh
   chmod +x .claude/hooks/stop.sh
   ```

2. **Customize validation level** in the hook file (default is level 2)

3. **The hook runs automatically** after each Claude Code edit session

### Skip Validation

To temporarily skip validation:

```bash
export SKIP_CS_VALIDATION=1
# Make your changes
# Validation will be skipped
unset SKIP_CS_VALIDATION
```

## Error Handling

### Common Errors and Solutions

#### Syntax Errors

```
✗ MyFile.cs:
  - Unbalanced braces: 1 extra {
```

**Solution**: Check for missing closing braces

#### Build Errors

```
✗ Build validation failed
  MyService.cs:42 [CS0103]
    The name 'configValue' does not exist in the current context
```

**Solution**: Fix the compiler error at the specified line

#### Analyzer Violations

```
✗ Analyzer violations found
  CA1822: Member 'DoWork' does not access instance data
```

**Solution**: Make the method static or use instance data

#### Format Violations

```
✗ Format violations found
  Run: dotnet format to fix automatically
```

**Solution**: Run `dotnet format` to auto-fix formatting

## Command Line Options

```bash
./tools/cs-validator.sh [OPTIONS]

Options:
  --level N          Validation level (1-4, default: 2)
  --config PATH      Config file path (default: .claude/config/cs-validator.json)
  --verbose          Enable verbose output
  --timeout SECONDS  Timeout in seconds (default: 30)
  --help             Show help message
```

## Exit Codes

- `0`: All validations passed
- `1`: Validation failed (syntax/build/analyzer errors)
- `2`: Configuration error
- `3`: Timeout exceeded
- `4`: Required tool not found (dotnet, python)

## Performance

The tool is optimized for interactive use:

- **Syntax check**: <100ms per file
- **Build check**: 2-4 seconds for single project
- **Analyzer check**: 1-3 seconds
- **Format check**: <1 second
- **Total**: <5 seconds for typical edits

### Optimization Features

- **Incremental building**: Only affected projects
- **Parallel execution**: Independent checks run concurrently
- **Early exit**: Stops at first failure (fail-fast)
- **Caching**: (Coming soon) Cache results for unchanged files

## Troubleshooting

### Validator not found

```bash
⚠ C# validator not found at: /path/to/cs-validator.sh
```

**Solution**: Ensure `tools/cs-validator.sh` exists and is executable

### dotnet CLI not found

```bash
✗ dotnet CLI not found. Please install .NET SDK.
```

**Solution**: Install .NET SDK from https://dotnet.microsoft.com/download

### jq not found

The validator works without `jq` but with reduced functionality.

**Solution (macOS)**: `brew install jq`
**Solution (Ubuntu)**: `apt-get install jq`

### Validation takes too long

**Solution 1**: Reduce validation level to 1 or 2
**Solution 2**: Increase timeout in configuration
**Solution 3**: Skip tests projects in configuration

### False positives

**Solution**: Adjust `analyzerSeverityThreshold` in configuration from `"Warning"` to `"Error"`

## Examples

### Example 1: Quick syntax check before commit

```bash
./tools/cs-validator.sh --level 1
```

### Example 2: Full validation with verbose output

```bash
./tools/cs-validator.sh --level 4 --verbose
```

### Example 3: Custom timeout for large projects

```bash
./tools/cs-validator.sh --timeout 60
```

### Example 4: Skip validation for emergency fix

```bash
export SKIP_CS_VALIDATION=1
# Make emergency fix
git commit -m "hotfix: critical bug fix"
unset SKIP_CS_VALIDATION
```

## Best Practices

1. **Use Level 2 for daily development**: Good balance of speed and coverage
2. **Use Level 4 before creating PRs**: Ensure highest code quality
3. **Configure project-specific rules**: Skip test projects if they're slow
4. **Don't abuse skip**: Only skip validation for emergency fixes
5. **Fix errors immediately**: Don't accumulate technical debt
6. **Run manually before committing**: Catch issues early

## Advanced Usage

### Custom Validation Scripts

You can extend the validator by adding custom check scripts:

1. Create a new script in `tools/` directory
2. Follow the same pattern as existing checks
3. Return 0 for success, 1 for failure
4. Modify `cs-validator.sh` to call your custom check

### CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Validate C# Code
  run: ./tools/cs-validator.sh --level 3
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
./tools/cs-validator.sh --level 2 || exit 1
```

## Contributing

To contribute to this tool:

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all checks pass at level 4

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review the architecture documentation
3. Check existing GitHub issues
4. Create a new issue with details

## License

See repository LICENSE file.

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed design and implementation
- [INTEGRATION.md](./INTEGRATION.md) - Integration guide for different setups
