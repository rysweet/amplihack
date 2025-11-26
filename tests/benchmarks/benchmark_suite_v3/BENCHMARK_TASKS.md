# Benchmark Task Suite v3

Four tasks of increasing complexity to evaluate Opus 4.5 vs Sonnet 4.5 workflow adherence, solution quality, and agent orchestration.

## Task 1: Simple - Greeting Utility (Baseline)

**Complexity**: Low
**Expected Workflow Steps**: 3-5 (for minimalist) or 22 (full workflow)
**Files to Create**: 2

```
Create a simple greeting utility:
1) Create src/amplihack/utils/greeting.py with greet(name) function that returns 'Hello, {name}!'
2) Create tests/unit/test_greeting.py with one test
3) Run the test
Use TDD approach. Complete all steps without asking questions.
```

**Quality Criteria**:

- Function works correctly
- Test passes
- Code follows project conventions

---

## Task 2: Medium - Configuration Manager

**Complexity**: Medium
**Expected Workflow Steps**: 10-15
**Files to Create**: 3-4

```
Create a configuration manager module:
1) Create src/amplihack/config/manager.py with a ConfigManager class that:
   - Loads config from YAML files
   - Supports environment variable overrides (AMPLIHACK_* prefix)
   - Has get(key, default=None) and set(key, value) methods
   - Validates required keys on initialization
2) Create tests/unit/test_config_manager.py with tests for:
   - Loading from YAML
   - Environment variable override
   - Default values
   - Validation errors
3) Create a sample config file at config/default.yaml
4) Run all tests
Use TDD approach. Handle edge cases. Complete all steps without asking questions.
```

**Quality Criteria**:

- All methods implemented correctly
- Edge cases handled (missing file, invalid YAML, missing required keys)
- Tests comprehensive (happy path + error cases)
- Proper error messages

---

## Task 3: Complex - CLI Command Plugin System

**Complexity**: High
**Expected Workflow Steps**: 15-20
**Files to Create**: 5-7

```
Implement a plugin system for CLI commands:
1) Create src/amplihack/plugins/base.py with:
   - Abstract PluginBase class with execute(args) method
   - PluginRegistry singleton for registering/discovering plugins
   - @register_plugin decorator
2) Create src/amplihack/plugins/loader.py with:
   - Function to discover plugins from a directory
   - Function to load plugin by name
   - Validation that plugins implement PluginBase
3) Create src/amplihack/plugins/builtin/hello.py as example plugin
4) Create tests/unit/test_plugin_system.py with tests for:
   - Plugin registration
   - Plugin discovery
   - Plugin loading
   - Invalid plugin handling
5) Create tests/integration/test_plugin_integration.py testing end-to-end flow
6) Update src/amplihack/plugins/__init__.py with public API
7) Run all tests
Use TDD approach. Follow SOLID principles. Complete all steps without asking questions.
```

**Quality Criteria**:

- Clean abstraction with proper inheritance
- Registry pattern correctly implemented
- Decorator works correctly
- Plugin discovery is robust
- Error handling for invalid plugins
- Integration test covers real usage

---

## Task 4: Advanced - REST API Client with Retry Logic

**Complexity**: Very High
**Expected Workflow Steps**: 20+
**Files to Create**: 6-8

```
Create a robust REST API client library:
1) Create src/amplihack/api/client.py with APIClient class:
   - Configurable base_url, timeout, headers
   - Methods: get, post, put, delete
   - Automatic retry with exponential backoff (max 3 retries)
   - Rate limiting support (respect 429 responses)
   - Request/response logging
2) Create src/amplihack/api/exceptions.py with custom exceptions:
   - APIError (base)
   - RateLimitError
   - TimeoutError
   - AuthenticationError
3) Create src/amplihack/api/models.py with:
   - Request/Response dataclasses
   - Serialization helpers
4) Create tests/unit/test_api_client.py testing:
   - Successful requests
   - Retry behavior
   - Rate limit handling
   - Timeout handling
   - Error responses
5) Create tests/unit/test_api_exceptions.py
6) Create tests/integration/test_api_integration.py with mock server
7) Update src/amplihack/api/__init__.py with public API
8) Run all tests
Use TDD approach. Handle all edge cases. Follow best practices for HTTP clients. Complete all steps without asking questions.
```

**Quality Criteria**:

- Retry logic with proper exponential backoff
- Rate limiting correctly implemented
- All HTTP methods work
- Custom exceptions are informative
- Dataclasses are well-designed
- Mock server in integration tests
- Comprehensive test coverage
- Proper logging

---

## Evaluation Metrics

For each task, we measure:

### Quantitative

- Duration (seconds)
- Turns (conversation rounds)
- Cost (USD)
- Token usage (input/output/cache)
- Tool calls count
- Subagent invocations
- Skills invoked

### Workflow Adherence

- Steps from DEFAULT_WORKFLOW.md executed
- GitHub issue created (Y/N)
- PR created (Y/N)
- Feature branch used (Y/N)
- Tests written before implementation (TDD)

### Quality Assessment

- Correctness: Does it work?
- Completeness: All requirements met?
- Error handling: Edge cases covered?
- Code quality: Clean, readable, maintainable?
- Test quality: Comprehensive coverage?
- Documentation: Comments where needed?

---

## Running the Benchmarks

Each task should be run in a fresh worktree with:

```bash
amplihack -- --model <model> --output-format json -p "<task prompt>"
```

Using claude-trace for detailed logging.
