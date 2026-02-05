# Outside-In Testing Skill

## Overview

The Outside-In Testing Skill helps you create behavior-driven tests that verify applications from an external user's perspective without requiring knowledge of internal implementation. Using the gadugi-agentic-test framework, you write declarative YAML scenarios that AI agents execute, observe, and validate.

**Key Benefits**:

- Tests survive refactoring (implementation changes don't break tests)
- Readable by non-developers (declarative YAML format)
- Platform-agnostic (same structure for CLI, TUI, Web, Electron)
- AI-powered execution (agents handle complex interactions)
- Evidence-based validation (screenshots, logs, output captures)

## What is Outside-In Testing?

**Traditional Testing** (Inside-Out):

```python
# Knows internal implementation
def test_user_service():
    service = UserService()
    user = service.create_user("test@example.com")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.created_at <= datetime.now()  # Internal state
```

**Outside-In Testing**:

```yaml
# Only knows external behavior
scenario:
  name: "User Registration"
  type: web
  steps:
    - action: navigate
      url: "/register"
    - action: type
      selector: "#email"
      value: "test@example.com"
    - action: click
      selector: "button[type=submit]"
    - action: verify_url
      contains: "/welcome"
```

The outside-in test verifies the same functionality but:

- Doesn't depend on internal classes (`UserService`)
- Doesn't check internal state (`created_at`, `id`)
- Tests from user's perspective (what they see and do)
- Remains valid even if implementation completely changes

## When to Use This Skill

### Perfect Scenarios

1. **Smoke Testing** - Quickly verify critical paths work
2. **Acceptance Testing** - Validate features meet requirements
3. **Regression Testing** - Ensure changes don't break existing behavior
4. **Cross-Platform Testing** - Test CLI, TUI, Web, Electron with same approach
5. **Refactoring Safety** - Tests protect behavior during rewrites
6. **Documentation as Tests** - YAML doubles as executable specifications

### Complementary to Unit Tests

Outside-in tests work best alongside unit tests:

- **Unit Tests** (60%): Internal logic, edge cases, error handling
- **Integration Tests** (30%): Component interactions, API contracts
- **Outside-In Tests** (10%): Critical user workflows, end-to-end paths

Use `test-gap-analyzer` skill for unit test guidance, and this skill for behavioral validation.

## Quick Start

### 1. Install Framework

**Option A: From GitHub (Recommended - Latest)**

```bash
# Install globally
npm install -g github:rysweet/gadugi-agentic-test

# Or use with npx
npx github:rysweet/gadugi-agentic-test gadugi-test run test.yaml

# Or clone and build
git clone https://github.com/rysweet/gadugi-agentic-test
cd gadugi-agentic-test
npm install
npm run build
node dist/cli.js run scenarios/your-test.yaml
```

**Option B: From npm (when published)**

```bash
npm install -g @gadugi/agentic-test
gadugi-test run test.yaml
```

**Note**: Framework is Node.js/TypeScript based, not Python. If you get dependency errors, see troubleshooting below.

### 2. Create Your First Test

Save as `test-hello.yaml`:

```yaml
scenario:
  name: "Hello World Test"
  description: "Verify application prints greeting"
  type: cli

  steps:
    - action: launch
      target: "./hello-world"

    - action: verify_output
      contains: "Hello, World!"

    - action: verify_exit_code
      expected: 0
```

### 3. Run the Test

**If installed globally**:

```bash
gadugi-test run test-hello.yaml
```

**If using from source**:

```bash
cd /path/to/gadugi-agentic-test
node dist/cli.js run /path/to/test-hello.yaml
```

**Run all tests in directory**:

```bash
node dist/cli.js run -d ./my-test-scenarios
```

### 4. Review Results

The framework generates evidence in `./evidence/`:

- Execution logs
- Output captures
- Screenshots (for TUI/Web/Electron)
- Timing data
- HTML report

## Supported Application Types

### CLI (Command-Line Interface)

Test command-line tools, scripts, and utilities:

```yaml
scenario:
  name: "Git Status Test"
  type: cli
  steps:
    - action: launch
      target: "git"
      args: ["status"]
    - action: verify_output
      contains: "On branch"
```

**Common Use Cases**:

- Package managers (npm, pip, cargo)
- Build tools (make, gradle, webpack)
- DevOps tools (docker, kubectl, terraform)
- Custom CLI applications

### TUI (Terminal User Interface)

Test interactive terminal applications:

```yaml
scenario:
  name: "TUI Navigation"
  type: tui
  steps:
    - action: launch
      target: "./file-manager"
    - action: send_keypress
      value: "down"
      times: 3
    - action: verify_screen
      contains: "> documents/"
```

**Common Use Cases**:

- System monitors (htop, top)
- Text editors (vim, nano)
- File managers (ranger, midnight commander)
- Custom TUI dashboards

### Web Applications

Test browser-based applications:

```yaml
scenario:
  name: "Web Dashboard Test"
  type: web
  steps:
    - action: navigate
      url: "http://localhost:3000"
    - action: verify_element
      selector: "h1"
      contains: "Dashboard"
```

**Common Use Cases**:

- SPAs (React, Vue, Angular apps)
- Admin panels
- E-commerce sites
- SaaS applications

### Electron Applications

Test desktop apps built with Electron:

```yaml
scenario:
  name: "Desktop App Test"
  type: electron
  steps:
    - action: launch
      target: "./dist/my-app"
    - action: verify_window
      title: "My Application"
```

**Common Use Cases**:

- Code editors (VS Code-like apps)
- Chat applications (Slack, Discord clones)
- Productivity tools
- Custom desktop applications

## Progressive Learning Path

The skill teaches testing in three levels:

### Level 1: Fundamentals (Start Here)

- Basic test structure (YAML anatomy)
- Single-action tests
- Simple verification
- Smoke tests

**Examples**:

- `examples/cli/calculator-basic.yaml`
- `examples/tui/file-manager-navigation.yaml`
- `examples/web/dashboard-smoke-test.yaml`
- `examples/electron/single-window-basic.yaml`

### Level 2: Intermediate

- Multi-step workflows
- Conditional logic
- Error handling
- Variables and templating

**Examples**:

- `examples/cli/cli-error-handling.yaml`
- `examples/tui/tui-form-validation.yaml`
- `examples/web/web-authentication-flow.yaml`
- `examples/electron/multi-window-coordination.yaml`

### Level 3: Advanced

- Custom comprehension agents
- Visual regression testing
- Performance validation
- IPC testing (Electron)

**Examples**:

- `examples/tui/tui-performance-monitoring.yaml`
- `examples/electron/electron-ipc-testing.yaml`
- `examples/custom-agents/custom-comprehension-agent.yaml`
- `examples/custom-agents/custom-reporter-integration.yaml`

## Example Library

This skill includes **15 complete working examples**:

### CLI (3 examples)

- Basic calculator operations [Level 1]
- Error handling and recovery [Level 2]
- Interactive session management [Level 2]

### TUI (3 examples)

- File manager navigation [Level 1]
- Form validation [Level 2]
- Performance monitoring [Level 3]

### Web (3 examples)

- Dashboard smoke test [Level 1]
- Authentication flow [Level 2]
- Visual regression [Level 2]

### Electron (4 examples)

- Single window basics [Level 1]
- Multi-window coordination [Level 2]
- Menu interactions [Level 2]
- IPC testing [Level 3]

### Custom Agents (2 examples)

- Domain-specific comprehension [Level 3]
- Custom reporting [Level 3]

All examples include:

- Complete working YAML
- Inline documentation
- Expected output
- Prerequisites
- Level indicators

## Using This Skill in Claude

### Invoke the Skill

```
Claude, use the outside-in-testing skill to create a CLI test for my calculator app.

Claude, use outside-in-testing to generate web tests for user login.

Claude, create Electron tests using outside-in-testing for my desktop app.
```

### What You'll Receive

1. **Complete YAML test scenario** matching your requirements
2. **Inline comments** explaining each section
3. **Best practices** applied (timeouts, waits, verification)
4. **Appropriate complexity** (Level 1, 2, or 3 based on needs)
5. **Instructions** for running the test

### Example Interaction

**You**: "Create a web test that verifies user can log in with valid credentials and sees their dashboard"

**Claude** (using this skill): Generates a complete Level 2 YAML scenario with:

- Navigation to login page
- Form filling (email, password)
- Submit button click
- URL verification (redirected to dashboard)
- Element verification (user profile visible)
- Screenshot capture
- Proper timeouts and waits

## Integration with Amplihack Philosophy

This skill embodies amplihack's core principles:

### Ruthless Simplicity

- Declarative YAML over complex code
- Minimal boilerplate
- Focus on behavior, not implementation

### Modular Design (Bricks & Studs)

- Self-contained test scenarios
- Clear action contracts
- Composable test steps

### Zero-BS Implementation

- No stubs or placeholders
- Every example is runnable
- Clear, actionable error messages

### Outside-In Thinking

- User perspective first
- Implementation-agnostic tests
- Behavior-driven validation

## Best Practices

### 1. Start Simple

Begin with basic smoke tests, then add complexity:

```yaml
# Level 1: Smoke test
steps:
  - action: launch
    target: "./app"
  - action: verify_output
    contains: "Ready"

# Level 2: Add interaction
steps:
  - action: launch
    target: "./app"
  - action: send_input
    value: "command\n"
  - action: verify_output
    contains: "Success"
```

### 2. Use Descriptive Names

```yaml
# Good
scenario:
  name: "User Login - Valid Credentials"
  description: "Verifies successful login with email and password"

# Bad
scenario:
  name: "Test 1"
```

### 3. Verify Critical Paths Only

Don't test every detail. Focus on user-facing behavior:

```yaml
# Good - User-visible behavior
- action: verify_element
  selector: ".welcome-message"
  contains: "Welcome back"

# Bad - Implementation detail
- action: verify_element
  selector: ".cache-status"
  contains: "initialized"
```

### 4. Always Wait for Dynamic Content

```yaml
# Good - Wait before verification
- action: click
  selector: ".load-data"
- action: wait_for_element
  selector: ".data-table"
  timeout: 10s
- action: verify_element
  selector: ".data-table"

# Bad - May fail due to timing
- action: click
  selector: ".load-data"
- action: verify_element
  selector: ".data-table" # Might not exist yet!
```

### 5. Clean Up After Tests

```yaml
steps:
  # Test steps...

cleanup:
  - action: delete_file
    path: "./test-data.json"
  - action: stop_application
```

## Troubleshooting

### Installation Issues

**Problem**: `@types/node-pty` not found error

**Solution**: This was fixed in gadugi-agentic-test. If you see this:

```bash
# Update to latest version
npm install -g github:rysweet/gadugi-agentic-test

# Or if you cloned, pull latest:
git pull origin main
npm install
npm run build
```

**Problem**: `tsc: command not found` when building

**Solution**: TypeScript not installed

```bash
npm install  # Installs all dependencies including TypeScript
npm run build  # Now will work
```

### Test Times Out

**Problem**: Test exceeds timeout and fails

**Solution**: Increase timeout for slow operations

```yaml
- action: wait_for_element
  selector: ".slow-loading-data"
  timeout: 30s # Generous timeout
```

### Scenario Format Issues

**Problem**: "Scenario must have a name" error

**Solution**: gadugi expects top-level `name:`, not nested under `scenario:`:

```yaml
# WRONG (won't load)
scenario:
  name: "My Test"
  steps: [...]

# RIGHT
name: "My Test"
description: "What this tests"
version: "1.0.0"
config:
  timeout: 120000
steps: [...]
```

### Element Not Found

**Problem**: Cannot find element to interact with

**Solutions**:

1. Use `wait_for_element` before interaction
2. Verify selector is correct
3. Check if element is in iframe

```yaml
- action: wait_for_element
  selector: ".target"
  timeout: 10s
- action: click
  selector: ".target"
```

### Flaky Tests in CI

**Problem**: Tests pass locally but fail in CI

**Solutions**:

1. Add longer timeouts for CI environments
2. Set explicit viewport sizes
3. Wait for application readiness

```yaml
scenario:
  environment:
    viewport:
      width: 1920
      height: 1080

  steps:
    - action: wait_for_element
      selector: ".app-ready"
      timeout: 30s # Generous for CI
```

## Framework Version Check

This skill embeds gadugi-agentic-test version **0.1.0**.

To check for newer versions:

```bash
python scripts/check-freshness.py
```

The script compares the embedded version against the latest GitHub release and notifies you of new features.

## Related Skills

- **test-gap-analyzer**: Find untested code paths (unit test focus)
- **philosophy-guardian**: Review test philosophy compliance
- **pr-review-assistant**: Include tests in PR reviews
- **module-spec-generator**: Generate specs with test scenarios

## Resources

### Documentation

- **Complete Skill Guide**: `SKILL.md` - Comprehensive 3000+ line documentation
- **Examples**: `examples/` - 15 complete working examples
- **Framework Repo**: https://github.com/rysweet/gadugi-agentic-test

### Getting Help

- Review examples in `examples/` directory
- Check `SKILL.md` for detailed explanations
- See troubleshooting section in `SKILL.md`
- Open issues at: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues

## Quick Reference

### Basic Test Template

```yaml
scenario:
  name: "Test Name"
  description: "What this verifies"
  type: cli | tui | web | electron

  prerequisites:
    - "Condition 1"

  steps:
    - action: launch
      target: "./app"

    - action: verify_output
      contains: "Expected"

  cleanup:
    - action: stop_application
```

### Common Actions

**CLI**:

- `launch` - Start application
- `send_input` - Send text
- `verify_output` - Check output
- `verify_exit_code` - Validate exit code

**TUI**:

- `send_keypress` - Send keys
- `verify_screen` - Check screen
- `capture_screenshot` - Save screenshot

**Web**:

- `navigate` - Go to URL
- `click` - Click element
- `type` - Type text
- `verify_element` - Check element

**Electron**:

- `window_action` - Control windows
- `menu_click` - Click menus
- `dialog_action` - Handle dialogs
- All web actions

## Success Stories

Outside-in testing shines when:

1. **Refactoring**: Change implementation without updating tests
2. **Collaboration**: Non-developers can read and understand tests
3. **Documentation**: Tests serve as executable specifications
4. **Regression Prevention**: Catch breaking changes in critical flows
5. **Cross-Platform**: Same test structure across CLI/TUI/Web/Electron

Start with Level 1 examples and progressively add complexity as needed. The AI agents handle the hard parts - you just describe what should happen.

---

**Remember**: Outside-in tests verify WHAT your application does, not HOW it does it. Focus on behavior, and your tests will remain stable across refactorings while providing meaningful validation.

## Real-World Example: Testing amplihack Guide Agent

Based on actual testing of amplihack's guide agent, here's a complete working example:

### Scenario: Naive Student Learning Flow

```yaml
name: "Guide Agent - Beginner First Question"
description: "Test how guide responds to complete beginner"
version: "1.0.0"

config:
  timeout: 180000 # 3 minutes for AI response
  retries: 1
  parallel: false

agents:
  - name: "student-cli"
    type: "system"
    config:
      shell: "bash"
      cwd: "/tmp/test-student"
      timeout: 180000
      capture_output: true

steps:
  - name: "Student asks: What is amplihack?"
    agent: "student-cli"
    action: "execute_command"
    params:
      command: 'mkdir -p /tmp/test-student && uvx --from git+https://github.com/rysweet/amplihack amplihack claude -- -p "Task(subagent_type=''guide'', prompt=''I am new. What is amplihack?'')" 2>&1 | head -100'
    expect:
      exit_code: 0
      stdout_contains:
        - "amplihack"
        - "AI"
    timeout: 180000

  - name: "Verify guide gives immediate action"
    agent: "student-cli"
    action: "execute_command"
    params:
      command: "grep -i 'TRY IT\\|try this\\|run this' /tmp/test-student/.claude/agents/amplihack/core/guide.md"
    expect:
      exit_code: 0
    timeout: 5000

metadata:
  tags: ["guide-agent", "beginner", "real-world"]
  priority: "high"
```

### What This Tests

1. **Installation via uvx** - Tests users can run without installing
2. **Guide agent invocation** - Verifies Task(subagent_type='guide') works
3. **Beginner-friendly response** - Checks for immediate actionable command
4. **Interactive elements** - Looks for TRY IT prompts

### Running This Test

```bash
cd gadugi-agentic-test
node dist/cli.js run scenarios/amplihack-guide-test.yaml --verbose
```

### What We Learned

**From testing amplihack guide agent**:

- Long-running AI commands need 180s+ timeouts
- Testing in clean `/tmp` directory avoids state pollution
- Combining `uvx --from git+...` with gadugi tests unreleased branches
- Checking file content (guide.md) verifies features beyond just output
- Real-world tests exposed gaps (guide showing bash commands in REPL context)
