# Template Variables Troubleshooting

## Overview

Recipe template variables (`{{variable}}`) are automatically expanded at runtime from the recipe context. For bash steps, the Recipe Runner applies proper shell escaping via `shlex.quote()` to prevent command injection vulnerabilities.

## Common Issues

### Issue: "JSON parsing error" or "command not found" in bash steps

**Symptom**: Bash steps fail with errors like:
- `bash: line 1: {"json":"data"}: command not found`
- `JSON parsing error: unterminated string`
- Python JSON decode errors when reading environment variables

**Example Failure**:
````yaml
- id: verify-fixes
  type: bash
  command: |
    export VALIDATED='{{validated_findings}}'  # ❌ WRONG
    python3 - <<'PYEOF'
    import json, os
    data = json.loads(os.environ['VALIDATED'])  # Fails!
    PYEOF
````

**Root Cause**: Manual quotes around template variables cause double-quoting:
1. Recipe YAML has: `'{{validated_findings}}'`
2. Recipe Runner expands to: `'{"json":"data"}'`
3. `render_shell()` applies `shlex.quote()`: `''{"json":"data"}''`
4. Bash sees: `export VALIDATED=''{"json":"data"}''`
5. Result: Bash interprets JSON as commands or creates malformed strings

**Solution**: Remove manual quotes - let `render_shell()` handle escaping automatically:

````yaml
- id: verify-fixes
  type: bash
  command: |
    export VALIDATED={{validated_findings}}  # ✅ CORRECT
    python3 - <<'PYEOF'
    import json, os
    data = json.loads(os.environ['VALIDATED'])  # Works!
    PYEOF
  output: verification_result
````

**Why This Works**: `render_shell()` automatically applies proper shell escaping to `{{validated_findings}}`, producing correctly quoted output that bash and Python can parse.

### Issue: Bash interprets template content as commands

**Symptom**: Unexpected command execution or syntax errors from data that should be treated as strings

**Example**:
````yaml
- id: process-data
  type: bash
  command: |
    DATA='{{user_input}}'  # ❌ If user_input contains $(command), it executes!
````

**Solution**: No manual quotes + heredoc for Python scripts:
````yaml
- id: process-data
  type: bash
  command: |
    export DATA={{user_input}}  # ✅ render_shell() escapes safely
    python3 - <<'PYEOF'
    import os
    data = os.environ['DATA']  # Safe - no command injection
    PYEOF
````

### Issue: Template variable undefined or empty

**Symptom**: `{{variable}}` expands to empty string or bash errors with "unbound variable"

**Cause**: Variable not defined in context or previous step didn't produce output

**Debug Steps**:
1. Check the context definition in recipe YAML:
   ````yaml
   context:
     my_variable: "default_value"  # Must be defined here
   ````

2. Verify previous step set the output:
   ````yaml
   - id: generate-data
     agent: amplihack:builder
     prompt: "Generate some data"
     output: my_variable  # Must match the template variable name
   ````

3. Use recipe validation to check:
   ````bash
   amplihack recipe validate my-recipe.yaml
   # Output shows: [WARN] Context variable "{{my_variable}}" used but not defined
   ````

### Issue: Nested variable access fails

**Symptom**: `{{nested.key}}` doesn't expand or produces errors

**Cause**: Template variable contains structured data but dot notation not supported

**Solution**: Use `parse_json: true` on the step that produces the data:
````yaml
- id: fetch-data
  type: bash
  command: "curl -s https://api.example.com/data"
  parse_json: true  # Parses JSON stdout into Python dict
  output: api_response

- id: use-nested-data
  agent: amplihack:builder
  prompt: |
    Process the following user ID: {{api_response.user.id}}
    And email: {{api_response.user.email}}
````

## Best Practices

### 1. Never Manually Quote Template Variables in Bash Steps

````yaml
# ❌ WRONG - causes double-quoting
command: export DATA='{{json_data}}'

# ✅ CORRECT - let render_shell() handle it
command: export DATA={{json_data}}
````

### 2. Use Heredocs for Multi-Line Python Scripts

````yaml
- id: complex-processing
  type: bash
  command: |
    export INPUT={{structured_data}}
    python3 - <<'PYEOF'
    import json, os
    data = json.loads(os.environ['INPUT'])
    # Process data safely
    print(json.dumps(result))
    PYEOF
  parse_json: true
  output: result
````

**Why**: Quoted heredoc delimiter (`<<'PYEOF'`) prevents bash from interpreting special characters inside the Python script.

### 3. Validate Recipes Before Running

````bash
amplihack recipe validate my-recipe.yaml --strict
````

This catches:
- Undefined template variables
- Invalid Python expressions in conditions
- Circular dependencies between steps

### 4. Use parse_json for Structured Data

````yaml
- id: generate-json
  agent: amplihack:architect
  prompt: "Generate a JSON config for the system"
  parse_json: true  # Makes nested.key access work
  output: config

- id: use-config
  agent: amplihack:builder
  prompt: "Use database URL: {{config.database.url}}"
````

## Security Considerations

The Recipe Runner uses `shlex.quote()` to prevent command injection:

````python
# render_shell() does this automatically
import shlex
safe_value = shlex.quote(context['user_input'])
command = f"export DATA={safe_value}"
````

**What This Prevents**:
- Command injection via `$(command)` or backticks
- Path traversal via `../../../etc/passwd`
- Shell metacharacter exploitation (`&`, `;`, `|`, etc.)

**What You Must Still Do**:
- Validate input data at the source (agent prompts should sanitize)
- Use heredocs for Python scripts to avoid nested quoting issues
- Never manually construct SQL or shell commands from template variables

## Testing Template Variables

Test recipe template expansion without executing:

````bash
# Dry run shows expanded templates
amplihack recipe run my-recipe --dry-run \
  --context '{"my_var": "test value"}'

# Output shows:
# [Step 1] Would execute: export DATA=test\ value
````

## Version History

### March 2026 (v0.9.0)

- **PR #2887**: Fixed double-quoting in `quality-audit-cycle.yaml` bash templates
  - Removed manual quotes from `{{variable}}` references
  - Documented best practice: let `render_shell()` handle shell escaping
  - Affected steps: verify-fixes, accumulate-history, recurse-decision

## See Also

- [Recipe YAML Format](./README.md#recipe-yaml-format) - Complete template variable syntax
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Command-line options
- [Recent Fixes - March 2026](./RECENT_FIXES_MARCH_2026.md#bash-template-variable-quoting-pr-2887) - Detailed fix explanation
