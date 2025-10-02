# Development Patterns & Solutions

This document captures proven patterns, solutions to common problems, and lessons learned from development. It serves as a quick reference for recurring challenges.

## Pattern: Claude Code SDK Integration

### Challenge

Integrating Claude Code SDK for AI-powered operations requires proper environment setup and timeout handling.

### Solution

```python
import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def extract_with_claude_sdk(prompt: str, timeout_seconds: int = 120):
    """Extract using Claude Code SDK with proper timeout handling"""
    try:
        # Always use 120-second timeout for SDK operations
        async with asyncio.timeout(timeout_seconds):
            async with ClaudeSDKClient(
                options=ClaudeCodeOptions(
                    system_prompt="Extract information...",
                    max_turns=1,
                )
            ) as client:
                await client.query(prompt)

                response = ""
                async for message in client.receive_response():
                    if hasattr(message, "content"):
                        content = getattr(message, "content", [])
                        if isinstance(content, list):
                            for block in content:
                                if hasattr(block, "text"):
                                    response += getattr(block, "text", "")
                return response
    except asyncio.TimeoutError:
        print(f"Claude Code SDK timed out after {timeout_seconds} seconds")
        return ""
```

### Key Points

- **120-second timeout is optimal** - Gives SDK enough time without hanging forever
- **SDK only works in Claude Code environment** - Accept empty results outside
- **Handle markdown in responses** - Strip ```json blocks before parsing

## Pattern: Resilient Batch Processing

### Challenge

Processing large batches where individual items might fail, but we want to maximize successful processing.

### Solution

```python
class ResilientProcessor:
    async def process_batch(self, items):
        results = {"succeeded": [], "failed": []}

        for item in items:
            try:
                result = await self.process_item(item)
                results["succeeded"].append(result)
                # Save progress immediately
                self.save_results(results)
            except Exception as e:
                results["failed"].append({
                    "item": item,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                # Continue processing other items
                continue

        return results
```

### Key Points

- **Save after every item** - Never lose progress
- **Continue on failure** - Don't let one failure stop the batch
- **Track failure reasons** - Distinguish between types of failures
- **Support selective retry** - Only retry failed items

## Pattern: File I/O with Cloud Sync Resilience

### Challenge

File operations can fail mysteriously when directories are synced with cloud services (OneDrive, Dropbox).

### Solution

```python
import time
from pathlib import Path

def write_with_retry(filepath: Path, data: str, max_retries: int = 3):
    """Write file with exponential backoff for cloud sync issues"""
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(data)
            return
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:
                if attempt == 0:
                    print(f"File I/O error - retrying. May be cloud sync issue.")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise
```

### Key Points

- **Retry with exponential backoff** - Give cloud sync time to complete
- **Inform user about cloud sync** - Help them understand delays
- **Create parent directories** - Ensure path exists before writing

## Pattern: Async Context Management

### Challenge

Nested asyncio event loops cause hangs when integrating async SDKs.

### Solution

```python
# WRONG - Creates nested event loops
class Service:
    def process(self, data):
        return asyncio.run(self._async_process(data))  # Creates new loop

# Called from async context:
await loop.run_in_executor(None, service.process, data)  # Nested loops!

# RIGHT - Pure async throughout
class Service:
    async def process(self, data):
        return await self._async_process(data)  # No new loop

# Called from async context:
await service.process(data)  # Clean async chain
```

### Key Points

- **Never mix sync/async APIs** - Choose one approach
- **Avoid asyncio.run() in libraries** - Let caller manage the event loop
- **Design APIs to be fully async or fully sync** - Not both

## Pattern: Module Regeneration Structure

### Challenge

Creating modules that can be regenerated by AI without breaking system integration.

### Solution

```
module_name/
├── __init__.py         # Public interface ONLY via __all__
├── README.md           # Contract specification (required)
├── core.py             # Main implementation
├── models.py           # Data structures
├── tests/
│   ├── test_contract.py    # Verify public interface
│   └── test_core.py         # Unit tests
└── examples/
    └── basic_usage.py       # Working example
```

### Key Points

- **Contract in README.md** - AI can regenerate from this spec
- \***\*all** defines public interface\*\* - Clear boundary
- **Tests verify contract** - Not implementation details
- **Examples must work** - Validated by tests

## Pattern: Zero-BS Implementation

### Challenge

Avoiding stub code and placeholders that serve no purpose.

### Solution

```python
# BAD - Stub that does nothing
def process_payment(amount):
    # TODO: Implement Stripe integration
    raise NotImplementedError("Coming soon")

# GOOD - Working implementation
def process_payment(amount, payments_file="payments.json"):
    """Record payment locally - fully functional."""
    payment = {
        "amount": amount,
        "timestamp": datetime.now().isoformat(),
        "id": str(uuid.uuid4())
    }

    # Load and update
    payments = []
    if Path(payments_file).exists():
        payments = json.loads(Path(payments_file).read_text())

    payments.append(payment)
    Path(payments_file).write_text(json.dumps(payments, indent=2))

    return payment
```

### Key Points

- **Every function must work** - Or not exist
- **Use files instead of external services** - Start simple
- **No TODOs without code** - Implement or remove
- **Legitimate empty patterns are OK** - e.g., `pass` in Click groups

## Pattern: Incremental Processing

### Challenge

Supporting resumable, incremental processing of large datasets.

### Solution

```python
class IncrementalProcessor:
    def __init__(self, state_file="processing_state.json"):
        self.state_file = Path(state_file)
        self.state = self.load_state()

    def load_state(self):
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"processed": [], "failed": [], "last_id": None}

    def save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def process_items(self, items):
        for item in items:
            if item.id in self.state["processed"]:
                continue  # Skip already processed

            try:
                self.process_item(item)
                self.state["processed"].append(item.id)
                self.state["last_id"] = item.id
                self.save_state()  # Save after each item
            except Exception as e:
                self.state["failed"].append({
                    "id": item.id,
                    "error": str(e)
                })
                self.save_state()
```

### Key Points

- **Save state after every item** - Resume from exact position
- **Track both success and failure** - Know what needs retry
- **Use fixed filenames** - Easy to find and resume
- **Support incremental updates** - Add new items without reprocessing

## Pattern: Configuration Single Source of Truth

### Challenge

Configuration scattered across multiple files causes drift and maintenance burden.

### Solution

```python
# Single source: pyproject.toml
[tool.myapp]
exclude = [".venv", "__pycache__", "node_modules"]
timeout = 30
batch_size = 100

# Read from single source
import tomllib

def load_config():
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    return config["tool"]["myapp"]

# Use everywhere
config = load_config()
excludes = config["exclude"]  # Don't hardcode these elsewhere
```

### Key Points

- **One authoritative location** - pyproject.toml for Python projects
- **Read, don't duplicate** - Load config at runtime
- **Document the source** - Make it clear where config lives
- **Accept minimal duplication** - Only for bootstrap/emergency

## Pattern: Parallel Task Execution

### Challenge

Executing multiple independent operations efficiently.

### Solution

```python
# WRONG - Sequential execution
results = []
for item in items:
    result = await process(item)
    results.append(result)

# RIGHT - Parallel execution
tasks = [process(item) for item in items]
results = await asyncio.gather(*tasks)

# With error handling
async def safe_process(item):
    try:
        return await process(item)
    except Exception as e:
        return {"error": str(e), "item": item}

tasks = [safe_process(item) for item in items]
results = await asyncio.gather(*tasks)
```

### Key Points

- **Use asyncio.gather() for parallel work** - Much faster
- **Wrap in error handlers** - Prevent one failure from stopping all
- **Consider semaphores for rate limiting** - Control concurrency
- **Return errors as values** - Don't let exceptions propagate

## Pattern: CI Failure Rapid Diagnosis

### Challenge

CI failures require systematic investigation across multiple dimensions (environment, syntax, logic, dependencies) while minimizing time to resolution. Traditional sequential debugging can take 45+ minutes.

### Solution

Deploy specialized agents in parallel for comprehensive diagnosis, targeting 20-25 minute resolution:

```python
# Parallel Agent Orchestration for CI Debugging
async def diagnose_ci_failure(pr_number: str, failure_logs: str):
    """Rapid CI failure diagnosis using parallel agent deployment"""

    # Phase 1: Environment Quick Check (2-3 minutes)
    basic_checks = await asyncio.gather(
        check_environment_setup(),
        validate_dependencies(),
        verify_branch_status()
    )

    if basic_checks_pass(basic_checks):
        # Phase 2: Parallel Specialized Diagnosis (8-12 minutes)
        diagnostic_tasks = [
            # Core diagnostic agents
            Task("ci-diagnostics", f"Analyze CI logs for {pr_number}"),
            Task("silent-failure-detector", "Identify silent test failures"),
            Task("pattern-matcher", "Match against known failure patterns")
        ]

        # Deploy all agents simultaneously
        results = await asyncio.gather(*[
            agent.execute(task) for agent, task in zip(
                [ci_diagnostics_agent, silent_failure_agent, pattern_agent],
                diagnostic_tasks
            )
        ])

        # Phase 3: Synthesis and Action (5-8 minutes)
        diagnosis = synthesize_findings(results)
        action_plan = create_fix_strategy(diagnosis)

        return {
            "root_cause": diagnosis.primary_issue,
            "fix_strategy": action_plan,
            "confidence": diagnosis.confidence_score,
            "estimated_fix_time": action_plan.time_estimate
        }

    return {"requires_escalation": True, "basic_check_failures": basic_checks}
```

### Agent Coordination Workflow

```
┌─── Environment Check (2-3 min) ───┐
│   ├── Dependencies valid?          │
│   ├── Branch conflicts?            │
│   └── Basic setup correct?         │
└─────────────┬───────────────────────┘
              │
              ▼ (if environment OK)
┌─── Parallel Diagnosis (8-12 min) ──┐
│   ├── ci-diagnostics.md            │
│   │   └── Parse logs, find errors  │
│   ├── silent-failure-detector.md   │
│   │   └── Find hidden failures     │
│   └── pattern-matcher.md           │
│       └── Match known patterns     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─── Synthesis & Action (5-8 min) ───┐
│   ├── Combine findings             │
│   ├── Identify root cause          │
│   ├── Generate fix strategy        │
│   └── Execute solution             │
└─────────────────────────────────────┘
```

### Decision Points

```python
def should_escalate(diagnosis_results):
    """Decide whether to escalate or continue automated fixing"""
    escalate_triggers = [
        diagnosis_results.confidence < 0.7,
        diagnosis_results.estimated_fix_time > 30,  # minutes
        diagnosis_results.requires_infrastructure_change,
        diagnosis_results.affects_multiple_systems
    ]
    return any(escalate_triggers)

def should_parallel_debug(initial_scan):
    """Determine if parallel agent deployment is worth it"""
    return (
        initial_scan.environment_healthy and
        initial_scan.failure_complexity > "simple" and
        initial_scan.logs_available
    )
```

### Tool Integration

```bash
# Environment checks (use built-in tools)
gh pr view ${PR_NUMBER} --json statusCheckRollup
git status --porcelain
npm test --dry-run  # or equivalent

# Agent delegation (use Task tool)
Task("ci-diagnostics", {
    "pr_number": pr_number,
    "logs": failure_logs,
    "focus": "error_identification"
})

# Pattern capture (update DISCOVERIES.md)
echo "## CI Pattern: ${failure_type}
- Root cause: ${root_cause}
- Solution: ${solution}
- Time to resolve: ${resolution_time}
- Confidence: ${confidence_score}" >> DISCOVERIES.md
```

### Specialized Agents Used

1. **ci-diagnostics.md**: Parse CI logs, identify error patterns, suggest fixes
2. **silent-failure-detector.md**: Find tests that pass but shouldn't, timeout issues
3. **pattern-matcher.md**: Match against historical failures, suggest proven solutions

### Time Optimization Strategies

- **Environment First**: Eliminate basic issues before deep diagnosis (saves 10-15 min)
- **Parallel Deployment**: Run all diagnostic agents simultaneously (saves 15-20 min)
- **Pattern Matching**: Use historical data to shortcut common issues (saves 5-10 min)
- **Confidence Thresholds**: Escalate low-confidence diagnoses early (prevents wasted time)

### Learning Loop Integration

```python
def capture_ci_pattern(failure_type, solution, resolution_time):
    """Capture successful patterns for future use"""
    pattern_entry = {
        "failure_signature": extract_signature(failure_type),
        "solution_steps": solution.steps,
        "resolution_time": resolution_time,
        "confidence_score": solution.confidence,
        "timestamp": datetime.now().isoformat()
    }

    # Add to DISCOVERIES.md for pattern recognition
    append_to_discoveries(pattern_entry)

    # Update pattern-matcher agent with new pattern
    update_pattern_database(pattern_entry)
```

### Success Metrics

- **Target Resolution Time**: 20-25 minutes (down from 45+ minutes)
- **Confidence Threshold**: >0.7 for automated fixes
- **Escalation Rate**: <20% of CI failures
- **Pattern Recognition Hit Rate**: >60% for repeat issues

### Key Points

- **Environment checks prevent wasted effort** - Always validate basics first
- **Parallel agent deployment is crucial** - Don't debug sequentially
- **Capture patterns immediately** - Update DISCOVERIES.md after every resolution
- **Use confidence scores for escalation** - Don't waste time on uncertain diagnoses
- **Historical patterns accelerate resolution** - Build and use pattern database
- **Specialized agents handle complexity** - Each agent has focused expertise

### Integration with Existing Patterns

- **Combines with Parallel Task Execution** - Uses asyncio.gather() for agent coordination
- **Follows Zero-BS Implementation** - All diagnostic code must work, no stubs
- **Uses Configuration Single Source** - CI settings centralized in pyproject.toml
- **Implements Incremental Processing** - Builds pattern database over time

## Pattern: Unified Validation Flow

### Challenge

Systems with multiple execution modes (UVX, normal) that have divergent validation paths, causing inconsistent behavior and hard-to-debug issues.

### Solution

Move all validation logic before execution mode branching to ensure consistent behavior across all modes.

```python
class SystemLauncher:
    def prepare_launch(self) -> bool:
        """Unified validation before mode-specific logic"""

        # Universal validation for ALL modes - no exceptions
        target_dir = self.detector.find_target_directory()
        if not target_dir:
            print("No valid target directory found")
            return False

        # Validate directory security and accessibility
        if not self.validate_directory_security(target_dir):
            print(f"Directory failed security validation: {target_dir}")
            return False

        # Now branch to mode-specific handling with validated directory
        if self.is_special_mode():
            return self._handle_special_mode(target_dir)
        else:
            return self._handle_normal_mode(target_dir)
```

### Key Points

- **Validate before branching** - Ensure all modes get same validation
- **No execution mode should bypass validation** - Creates divergent behavior
- **Pass validated data to mode handlers** - Don't re-validate
- **Log validation results** - Help debug validation failures

### Real Impact

From PR #148: Fixed UVX users ending up in wrong directory by moving directory validation before UVX/normal mode branching.

## Pattern: Modular User Visibility

### Challenge

Background processes that appear broken because users can't see progress, but adding visibility shouldn't break existing functionality.

### Solution

Create dedicated display modules that can be imported optionally and provide graceful fallbacks.

```python
# display.py - Standalone visibility module
def show_progress(message: str, stage: str = "info"):
    """User-visible progress indicator with emoji-based stages"""
    stage_icons = {
        "start": "🤖",
        "progress": "🔍",
        "success": "✅",
        "warning": "⚠️",
        "complete": "🏁"
    }

    print(f"{stage_icons.get(stage, 'ℹ️')} {message}")

def show_analysis_header(total_items: int):
    """Clear analysis start indicator"""
    print(f"\n{'=' * 60}")
    print(f"🤖 AI ANALYSIS STARTING")
    print(f"📊 Processing {total_items} items...")
    print(f"{'=' * 60}")

# In main processing module
def analyze_data(data):
    """Analysis with optional user feedback"""
    try:
        from .display import show_progress, show_analysis_header
        show_analysis_header(len(data))

        for i, item in enumerate(data):
            show_progress(f"Processing item {i+1}/{len(data)}")
            result = process_item(item)

        show_progress("Analysis complete", "complete")
        return results

    except ImportError:
        # Graceful fallback when display module unavailable
        return process_silently(data)
```

### Key Points

- **Optional dependency on display module** - System works without it
- **Clear progress indicators** - Use emoji and consistent formatting
- **Modular design** - Display logic separate from business logic
- **Environment-controlled verbosity** - Respect user preferences

### Real Impact

From PR #147: Made reflection system visible to users while maintaining all existing functionality through optional display module.

## Pattern: Multi-Layer Security Sanitization

### Challenge

Sensitive data (passwords, tokens, system paths) appearing in user output, logs, or stored analysis files across multiple processing layers.

### Solution

Implement sanitization at every data transformation point with safe fallbacks.

```python
# security.py - Dedicated security module
import re
from typing import Dict, List

class ContentSanitizer:
    """Multi-layer content sanitization with fallback strategies"""

    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*[^\s"]+',
        r'token["\s]*[:=]["\s]*[^\s"]+',
        r'api[_-]?key["\s]*[:=]["\s]*[^\s"]+',
        r'secret["\s]*[:=]["\s]*[^\s"]+',
        r'auth["\s]*[:=]["\s]*[^\s"]+',
    ]

    SYSTEM_PATHS = [
        r'/etc/[^\s]*',
        r'/private/etc/[^\s]*',
        r'/usr/bin/[^\s]*',
        r'/System/Library/[^\s]*',
    ]

    def sanitize_content(self, content: str, max_length: int = 10000) -> str:
        """Comprehensive content sanitization"""
        if not content:
            return content

        # Length limit to prevent information leakage
        if len(content) > max_length:
            content = content[:max_length] + "... [truncated for security]"

        # Remove sensitive credentials
        for pattern in self.SENSITIVE_PATTERNS:
            content = re.sub(pattern, "[REDACTED]", content, flags=re.IGNORECASE)

        # Remove system paths
        for pattern in self.SYSTEM_PATHS:
            content = re.sub(pattern, "[SYSTEM_PATH]", content)

        return content

# In processing modules - sanitize at every layer
def process_user_input(raw_input: str) -> str:
    """Input sanitization layer"""
    try:
        from .security import ContentSanitizer
        sanitizer = ContentSanitizer()
        return sanitizer.sanitize_content(raw_input)
    except ImportError:
        # Safe fallback sanitization
        return basic_sanitize(raw_input)

def store_analysis(data: Dict) -> None:
    """Storage sanitization layer"""
    try:
        from .security import ContentSanitizer
        sanitizer = ContentSanitizer()

        # Sanitize all string values before storage
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = sanitizer.sanitize_content(value)
            else:
                sanitized_data[key] = value

        save_to_file(sanitized_data)
    except ImportError:
        # Sanitize with basic patterns if security module unavailable
        save_to_file(basic_sanitize_dict(data))

def display_to_user(content: str) -> None:
    """Output sanitization layer"""
    try:
        from .security import ContentSanitizer
        sanitizer = ContentSanitizer()
        print(sanitizer.sanitize_content(content))
    except ImportError:
        print(basic_sanitize(content))

def basic_sanitize(content: str) -> str:
    """Fallback sanitization when security module unavailable"""
    # Basic patterns for critical security
    patterns = [
        (r'password["\s]*[:=]["\s]*[^\s"]+', '[REDACTED]'),
        (r'token["\s]*[:=]["\s]*[^\s"]+', '[REDACTED]'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    return content
```

### Key Points

- **Sanitize at every transformation** - Input, processing, storage, output
- **Safe fallback patterns** - Basic sanitization if security module fails
- **Length limits prevent leakage** - Truncate very long content
- **Multiple pattern types** - Credentials, paths, personal data
- **Never fail on security errors** - Always provide fallback

### Real Impact

From PR #147: Implemented comprehensive sanitization that prevented sensitive data exposure while maintaining system functionality through fallback strategies.

## Pattern: Intelligent Caching with Lifecycle Management

### Challenge

Expensive operations (path resolution, environment detection) repeated unnecessarily, but naive caching leads to memory leaks and stale data.

### Solution

Implement smart caching with invalidation strategies and resource management.

```python
from functools import lru_cache
from typing import Optional, Dict, Any
import threading

class SmartCache:
    """Intelligent caching with lifecycle management"""

    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache_stats = {"hits": 0, "misses": 0}
        self._lock = threading.RLock()

    @lru_cache(maxsize=128)
    def expensive_operation(self, input_data: str) -> str:
        """Cached expensive operation with automatic size management"""
        # Expensive computation here
        result = self._compute_expensive_result(input_data)

        # Track cache performance
        with self._lock:
            cache_info = self.expensive_operation.cache_info()
            if cache_info.hits > self._cache_stats["hits"]:
                self._cache_stats["hits"] = cache_info.hits
            else:
                self._cache_stats["misses"] += 1

        return result

    def invalidate_cache(self) -> None:
        """Clear cache when data might be stale"""
        with self._lock:
            self.expensive_operation.cache_clear()
            self._cache_stats = {"hits": 0, "misses": 0}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        with self._lock:
            cache_info = self.expensive_operation.cache_info()
            return {
                "hits": cache_info.hits,
                "misses": cache_info.misses,
                "current_size": cache_info.currsize,
                "max_size": cache_info.maxsize,
                "hit_rate": cache_info.hits / max(1, cache_info.hits + cache_info.misses)
            }

# Thread-safe lazy initialization pattern
class LazyResource:
    """Lazy initialization with thread safety"""

    def __init__(self):
        self._resource = None
        self._initialized = False
        self._lock = threading.RLock()

    def _ensure_initialized(self) -> None:
        """Thread-safe lazy initialization"""
        with self._lock:
            if not self._initialized:
                self._resource = self._create_expensive_resource()
                self._initialized = True

    def get_resource(self):
        """Get resource, initializing if needed"""
        self._ensure_initialized()
        return self._resource

    def invalidate(self) -> None:
        """Force re-initialization on next access"""
        with self._lock:
            self._resource = None
            self._initialized = False
```

### Key Points

- **Use lru_cache for automatic size management** - Prevents unbounded growth
- **Thread safety is essential** - Multiple threads may access simultaneously
- **Provide invalidation methods** - Cache must be clearable when stale
- **Track cache performance** - Monitor hit rates for optimization
- **Lazy initialization with locks** - Don't initialize until needed

### Real Impact

From PR #148: Added intelligent caching that achieved 4.1x and 10x performance improvements while maintaining thread safety and preventing memory leaks.

## Pattern: Graceful Environment Adaptation

### Challenge

Systems that need different behavior in different environments (UVX, normal, testing) without hard-coding environment-specific logic everywhere.

### Solution

Detect environment automatically and adapt behavior through configuration objects and environment variables.

```python
class EnvironmentAdapter:
    """Automatic environment detection and adaptation"""

    def __init__(self):
        self._environment = None
        self._config = None

    def detect_environment(self) -> str:
        """Automatically detect current execution environment"""
        if self._environment:
            return self._environment

        # Detection logic
        if self._is_uvx_environment():
            self._environment = "uvx"
        elif self._is_testing_environment():
            self._environment = "testing"
        else:
            self._environment = "normal"

        return self._environment

    def get_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        if self._config:
            return self._config

        env = self.detect_environment()

        # Environment-specific configurations
        configs = {
            "uvx": {
                "use_add_dir": True,
                "validate_paths": True,
                "working_directory": "auto_detect",
                "timeout_multiplier": 1.5,
            },
            "normal": {
                "use_add_dir": False,
                "validate_paths": True,
                "working_directory": "change_to_project",
                "timeout_multiplier": 1.0,
            },
            "testing": {
                "use_add_dir": False,
                "validate_paths": False,  # Faster tests
                "working_directory": "temp",
                "timeout_multiplier": 0.5,
            }
        }

        self._config = configs.get(env, configs["normal"])

        # Allow environment variable overrides
        self._apply_env_overrides()

        return self._config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        import os

        # Map environment variables to config keys
        env_mappings = {
            "AMPLIHACK_USE_ADD_DIR": ("use_add_dir", lambda x: x.lower() == "true"),
            "AMPLIHACK_VALIDATE_PATHS": ("validate_paths", lambda x: x.lower() == "true"),
            "AMPLIHACK_TIMEOUT_MULTIPLIER": ("timeout_multiplier", float),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            if env_var in os.environ:
                try:
                    self._config[config_key] = converter(os.environ[env_var])
                except (ValueError, TypeError):
                    # Log but don't fail on invalid environment variables
                    pass

# Usage pattern
class SystemManager:
    def __init__(self):
        self.adapter = EnvironmentAdapter()

    def execute(self):
        """Execute with environment-appropriate behavior"""
        config = self.adapter.get_config()

        if config["use_add_dir"]:
            return self._execute_with_add_dir()
        else:
            return self._execute_with_directory_change()
```

### Key Points

- **Automatic environment detection** - Don't require manual configuration
- **Configuration objects over scattered conditionals** - Centralize environment logic
- **Environment variable overrides** - Allow runtime customization
- **Sensible defaults for each environment** - Work out of the box
- **Graceful degradation** - Handle invalid configurations

### Real Impact

From PR #148: Enabled seamless operation across UVX and normal environments while maintaining consistent behavior and allowing user customization.

## Pattern: Reflection-Driven Self-Improvement

### Challenge

Systems that repeat the same mistakes because they don't learn from user interactions or identify improvement opportunities automatically.

### Solution

Implement AI-powered analysis of user sessions to automatically identify patterns and create improvement issues.

```python
class SessionReflector:
    """AI-powered session analysis for self-improvement"""

    def analyze_session(self, messages: List[Dict]) -> Dict:
        """Analyze session for improvement opportunities"""

        # Extract session patterns
        patterns = self._extract_patterns(messages)

        # Use AI to analyze patterns
        improvement_opportunities = self._ai_analyze_patterns(patterns)

        # Prioritize opportunities
        prioritized = self._prioritize_improvements(improvement_opportunities)

        return {
            "session_stats": self._get_session_stats(messages),
            "patterns": patterns,
            "improvements": prioritized,
            "automation_candidates": self._identify_automation_candidates(prioritized)
        }

    def _extract_patterns(self, messages: List[Dict]) -> List[Dict]:
        """Extract behavioral patterns from session"""
        patterns = []

        # Error patterns
        error_count = 0
        error_types = {}

        for msg in messages:
            content = str(msg.get("content", ""))

            if "error" in content.lower():
                error_count += 1
                # Extract error type
                error_type = self._classify_error(content)
                error_types[error_type] = error_types.get(error_type, 0) + 1

        if error_count > 2:
            patterns.append({
                "type": "error_handling",
                "severity": "high" if error_count > 5 else "medium",
                "details": {"total_errors": error_count, "error_types": error_types}
            })

        # Repetition patterns
        repeated_actions = self._find_repeated_actions(messages)
        if repeated_actions:
            patterns.append({
                "type": "workflow_inefficiency",
                "severity": "medium",
                "details": {"repeated_actions": repeated_actions}
            })

        return patterns

    def _ai_analyze_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """Use AI to suggest improvements for patterns"""
        improvements = []

        for pattern in patterns:
            if pattern["type"] == "error_handling":
                improvements.append({
                    "type": "error_handling",
                    "priority": "high",
                    "suggestion": "Improve error handling and user feedback",
                    "evidence": f"Found {pattern['details']['total_errors']} errors",
                    "implementation_hint": "Add try-catch blocks with user-friendly messages"
                })

            elif pattern["type"] == "workflow_inefficiency":
                improvements.append({
                    "type": "automation",
                    "priority": "medium",
                    "suggestion": "Automate repetitive workflow steps",
                    "evidence": f"User repeated actions: {pattern['details']['repeated_actions']}",
                    "implementation_hint": "Create compound commands for common sequences"
                })

        return improvements

    def create_improvement_issue(self, improvement: Dict) -> Optional[str]:
        """Automatically create GitHub issue for improvement"""

        title = f"AI-detected {improvement['type']}: {improvement['suggestion'][:60]}"

        body = f"""# AI-Detected Improvement Opportunity

**Type**: {improvement['type']}
**Priority**: {improvement['priority']}
**Evidence**: {improvement.get('evidence', 'Detected during session analysis')}

## Suggestion
{improvement['suggestion']}

## Implementation Hint
{improvement.get('implementation_hint', 'See analysis for details')}

## Analysis Details
This improvement was identified by AI analysis of session logs. The system detected patterns indicating this area needs attention.

**Labels**: ai-improvement, {improvement['type']}, {improvement['priority']}-priority
"""

        # Create issue using GitHub CLI
        result = subprocess.run([
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", f"ai-improvement,{improvement['type']},{improvement['priority']}-priority"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            return issue_url.split("/")[-1]  # Extract issue number

        return None
```

### Key Points

- **Analyze actual user behavior** - Don't guess at improvements
- **Use AI for pattern recognition** - Identify complex behavioral patterns
- **Automatic issue creation** - Convert insights to actionable work items
- **Evidence-based improvements** - Link suggestions to actual session data
- **Prioritization based on impact** - Focus on high-value improvements first

### Real Impact

From PR #147: Created self-improving system that analyzes 1,338+ session files and automatically creates GitHub issues for detected improvement opportunities.

## Pattern: Safe Subprocess Wrapper with Comprehensive Error Handling

### Challenge

Subprocess calls fail with cryptic error messages that don't help users understand what went wrong or how to fix it. Different subprocess errors (FileNotFoundError, PermissionError, TimeoutExpired) need different user-facing guidance.

### Solution

Create a safe subprocess wrapper that catches all error types and provides user-friendly, actionable error messages with context.

```python
def safe_subprocess_call(
    cmd: List[str],
    context: str,
    timeout: Optional[int] = 30,
) -> Tuple[int, str, str]:
    """Safely execute subprocess with comprehensive error handling.

    Args:
        cmd: Command and arguments to execute
        context: Human-readable context for what this command does
        timeout: Timeout in seconds (default 30)

    Returns:
        Tuple of (returncode, stdout, stderr)
        On error, returncode is non-zero and stderr contains helpful message
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    except FileNotFoundError:
        # Command not found - most common error
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command not found: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please ensure the tool is installed and in your PATH."
        return 127, "", error_msg

    except PermissionError:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Permission denied: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please check file permissions or run with appropriate privileges."
        return 126, "", error_msg

    except subprocess.TimeoutExpired:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command timed out after {timeout}s: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "The operation took too long to complete."
        return 124, "", error_msg

    except OSError as e:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"OS error running {cmd_name}: {str(e)}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg

    except Exception as e:
        # Catch-all for unexpected errors
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Unexpected error running {cmd_name}: {str(e)}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg
```

### Key Points

- **Standard exit codes** - Use conventional exit codes (127 for command not found, 126 for permission denied)
- **Context parameter is critical** - Always tell users what operation failed ("checking git version", "installing npm package")
- **User-friendly messages** - Avoid technical jargon, provide actionable guidance
- **No exceptions propagate** - Always return error info via return values
- **Default timeout** - 30 seconds prevents hanging on network issues

### When to Use

- ANY subprocess call in your codebase
- Especially when calling external tools (git, npm, uv, etc.)
- When users need to understand and fix issues themselves
- Replace all direct subprocess.run() calls with this wrapper

### Benefits

- Consistent error handling across entire codebase
- Users get actionable error messages
- No cryptic Python tracebacks for tool issues
- Easy to track what operation failed via context string

### Trade-offs

- Slightly more verbose than bare subprocess.run()
- Must provide context string (but this is a feature, not a bug)

### Related Patterns

- Combines with Platform-Specific Installation Guidance pattern
- Used by Fail-Fast Prerequisite Checking pattern

### Real Impact

From PR #457: Eliminated cryptic subprocess errors, making it clear when tools like npm or git are missing and exactly how to install them.

## Pattern: Platform-Specific Installation Guidance

### Challenge

Users on different platforms (macOS, Linux, WSL, Windows) need different installation commands. Providing generic "install X" guidance wastes user time looking up platform-specific instructions.

### Solution

Detect platform automatically and provide exact installation commands for that platform.

```python
from enum import Enum
import platform
from pathlib import Path

class Platform(Enum):
    """Supported platforms for prerequisite checking."""
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    WINDOWS = "windows"
    UNKNOWN = "unknown"

class PrerequisiteChecker:
    # Installation commands by platform and tool
    INSTALL_COMMANDS = {
        Platform.MACOS: {
            "node": "brew install node",
            "git": "brew install git",
        },
        Platform.LINUX: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs\n# Arch:\nsudo pacman -S nodejs",
            "git": "# Ubuntu/Debian:\nsudo apt install git\n# Fedora/RHEL:\nsudo dnf install git\n# Arch:\nsudo pacman -S git",
        },
        Platform.WSL: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs",
            "git": "sudo apt install git  # or your WSL distro's package manager",
        },
        Platform.WINDOWS: {
            "node": "winget install OpenJS.NodeJS\n# Or: choco install nodejs",
            "git": "winget install Git.Git\n# Or: choco install git",
        },
    }

    # Documentation links for each tool
    DOCUMENTATION_LINKS = {
        "node": "https://nodejs.org/",
        "git": "https://git-scm.com/",
    }

    def __init__(self):
        self.platform = self._detect_platform()

    def _detect_platform(self) -> Platform:
        """Detect the current platform."""
        system = platform.system()

        if system == "Darwin":
            return Platform.MACOS
        elif system == "Linux":
            if self._is_wsl():
                return Platform.WSL
            return Platform.LINUX
        elif system == "Windows":
            return Platform.WINDOWS
        else:
            return Platform.UNKNOWN

    def _is_wsl(self) -> bool:
        """Check if running under Windows Subsystem for Linux."""
        try:
            proc_version = Path("/proc/version")
            if proc_version.exists():
                content = proc_version.read_text().lower()
                return "microsoft" in content
        except (OSError, PermissionError):
            pass
        return False

    def get_install_command(self, tool: str) -> str:
        """Get platform-specific installation command for a tool."""
        platform_commands = self.INSTALL_COMMANDS.get(
            self.platform, self.INSTALL_COMMANDS.get(Platform.UNKNOWN, {})
        )
        return platform_commands.get(tool, f"Please install {tool} manually")

    def format_missing_prerequisites(self, missing_tools: List[str]) -> str:
        """Format user-friendly message with installation instructions."""
        lines = []
        lines.append("=" * 70)
        lines.append("MISSING PREREQUISITES")
        lines.append("=" * 70)
        lines.append("")
        lines.append("The following required tools are not installed:")
        lines.append("")

        for tool in missing_tools:
            lines.append(f"  ✗ {tool}")
        lines.append("")

        lines.append("=" * 70)
        lines.append("INSTALLATION INSTRUCTIONS")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Platform detected: {self.platform.value}")
        lines.append("")

        for tool in missing_tools:
            lines.append(f"To install {tool}:")
            lines.append("")
            install_cmd = self.get_install_command(tool)
            for cmd_line in install_cmd.split("\n"):
                lines.append(f"  {cmd_line}")
            lines.append("")

            if tool in self.DOCUMENTATION_LINKS:
                lines.append(f"  Documentation: {self.DOCUMENTATION_LINKS[tool]}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("")
        lines.append("After installing the missing tools, please run this command again.")

        return "\n".join(lines)
```

### Key Points

- **Automatic platform detection** - No user input needed
- **WSL detection is critical** - WSL needs different commands than native Linux
- **Multiple package managers** - Support apt, dnf, pacman, yum for Linux
- **Documentation links** - Give users official docs for complex installations
- **Clear formatting** - Use separators and indentation for readability

### When to Use

- Any tool that requires external dependencies
- CLI tools that users need to install before using your system
- Cross-platform Python applications
- Systems with multiple required tools

### Benefits

- Users get copy-paste commands that work
- No time wasted looking up installation instructions
- Supports Linux diversity (apt, dnf, pacman)
- WSL users get appropriate guidance

### Trade-offs

- Must maintain commands for each platform
- Commands may become outdated over time
- Doesn't cover all Linux distributions

### Related Patterns

- Works with Safe Subprocess Wrapper pattern
- Part of Fail-Fast Prerequisite Checking pattern

### Real Impact

From PR #457: Users on Windows/WSL got exact installation commands instead of generic "install Node.js" guidance, reducing setup time significantly.

## Pattern: Fail-Fast Prerequisite Checking

### Challenge

Users start using a tool, get cryptic errors mid-workflow when missing dependencies are discovered. This wastes time and creates frustration.

### Solution

Check all prerequisites at startup with clear, actionable error messages before any other operations.

```python
@dataclass
class ToolCheckResult:
    """Result of checking a single tool prerequisite."""
    tool: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None

@dataclass
class PrerequisiteResult:
    """Result of checking all prerequisites."""
    all_available: bool
    missing_tools: List[ToolCheckResult] = field(default_factory=list)
    available_tools: List[ToolCheckResult] = field(default_factory=list)

class PrerequisiteChecker:
    # Required tools with their version check arguments
    REQUIRED_TOOLS = {
        "node": "--version",
        "npm": "--version",
        "uv": "--version",
        "git": "--version",
    }

    def check_tool(self, tool: str, version_arg: Optional[str] = None) -> ToolCheckResult:
        """Check if a single tool is available."""
        tool_path = shutil.which(tool)

        if not tool_path:
            return ToolCheckResult(
                tool=tool,
                available=False,
                error=f"{tool} not found in PATH",
            )

        # Tool found - optionally check version
        version = None
        if version_arg:
            returncode, stdout, stderr = safe_subprocess_call(
                [tool, version_arg],
                context=f"checking {tool} version",
                timeout=5,
            )
            if returncode == 0:
                version = stdout.strip().split("\n")[0] if stdout else None

        return ToolCheckResult(
            tool=tool,
            available=True,
            path=tool_path,
            version=version,
        )

    def check_all_prerequisites(self) -> PrerequisiteResult:
        """Check all required prerequisites."""
        missing_tools = []
        available_tools = []

        for tool, version_arg in self.REQUIRED_TOOLS.items():
            result = self.check_tool(tool, version_arg)

            if result.available:
                available_tools.append(result)
            else:
                missing_tools.append(result)

        return PrerequisiteResult(
            all_available=len(missing_tools) == 0,
            missing_tools=missing_tools,
            available_tools=available_tools,
        )

    def check_and_report(self) -> bool:
        """Check prerequisites and print report if any are missing.

        Returns:
            True if all prerequisites available, False otherwise
        """
        result = self.check_all_prerequisites()

        if result.all_available:
            return True

        # Print detailed report
        print(self.format_missing_prerequisites(result.missing_tools))
        return False

# Integration with launcher
class ClaudeLauncher:
    def prepare_launch(self) -> bool:
        """Prepare for launch - check prerequisites FIRST"""
        # Check prerequisites before anything else
        checker = PrerequisiteChecker()
        if not checker.check_and_report():
            return False

        # Now proceed with other setup
        return self._setup_environment()
```

### Key Points

- **Check at entry point** - Before any other operations
- **Check all at once** - Don't fail on first missing tool, show all issues
- **Structured results** - Use dataclasses for clear data contracts
- **Version checking optional** - Can verify specific versions if needed
- **Never auto-install** - User control and security first

### When to Use

- CLI tools with external dependencies
- Systems that call external tools (git, npm, docker)
- Before any operation that will fail without prerequisites
- At application startup, not mid-workflow

### Benefits

- Users know all issues upfront
- No time wasted in failed workflows
- Clear data structures for testing
- Easy to mock in tests

### Trade-offs

- Slight startup delay (typically < 1 second)
- May check tools that won't be used in this run
- Requires maintenance as tools change

### Related Patterns

- Uses Safe Subprocess Wrapper for checks
- Uses Platform-Specific Installation Guidance for error messages
- Part of TDD Testing Pyramid pattern

### Real Impact

From PR #457: Prevented users from starting workflows that would fail 5 minutes later due to missing npm, providing clear guidance immediately.

## Pattern: TDD Testing Pyramid for System Utilities

### Challenge

System utility modules interact with external tools and platform-specific behavior, making them hard to test comprehensively while maintaining fast test execution.

### Solution

Follow testing pyramid with 60% unit tests, 30% integration tests, 10% E2E tests, using strategic mocking for speed.

```python
"""Tests for prerequisites module - TDD approach.

Following the testing pyramid:
- 60% Unit tests (18 tests)
- 30% Integration tests (9 tests)
- 10% E2E tests (3 tests)
"""

# ============================================================================
# UNIT TESTS (60% - 18 tests)
# ============================================================================

class TestPlatformDetection:
    """Unit tests for platform detection."""

    def test_detect_macos(self):
        """Test macOS platform detection."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.MACOS

    def test_detect_wsl(self):
        """Test WSL platform detection."""
        with patch("platform.system", return_value="Linux"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="Linux version microsoft"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.WSL

class TestToolChecking:
    """Unit tests for individual tool checking."""

    def test_check_tool_found(self):
        """Test checking for a tool that exists."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/git"):
            result = checker.check_tool("git")
            assert result.available is True
            assert result.path == "/usr/bin/git"

    def test_check_tool_with_version(self):
        """Test checking tool with version verification."""
        checker = PrerequisiteChecker()
        with patch("shutil.which", return_value="/usr/bin/node"), \
             patch("subprocess.run", return_value=Mock(returncode=0, stdout="v20.0.0", stderr="")):
            result = checker.check_tool("node", version_arg="--version")
            assert result.available is True
            assert result.version == "v20.0.0"

# ============================================================================
# INTEGRATION TESTS (30% - 9 tests)
# ============================================================================

class TestPrerequisiteIntegration:
    """Integration tests for prerequisite checking workflow."""

    def test_full_check_workflow_all_present(self):
        """Test complete prerequisite check when all tools present."""
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"
            result = checker.check_all_prerequisites()

            assert result.all_available is True
            assert len(result.available_tools) == 4

    def test_platform_specific_install_commands(self):
        """Test that platform detection affects install commands."""
        platforms = [
            ("Darwin", Platform.MACOS, "brew"),
            ("Linux", Platform.LINUX, "apt"),
            ("Windows", Platform.WINDOWS, "winget"),
        ]

        for system, expected_platform, expected_cmd in platforms:
            with patch("platform.system", return_value=system):
                checker = PrerequisiteChecker()
                assert checker.platform == expected_platform
                install_cmd = checker.get_install_command("git")
                assert expected_cmd in install_cmd.lower()

# ============================================================================
# E2E TESTS (10% - 3 tests)
# ============================================================================

class TestEndToEnd:
    """End-to-end tests for complete prerequisite checking workflows."""

    def test_e2e_missing_prerequisites_with_guidance(self):
        """E2E: Complete workflow with missing prerequisites and user guidance."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                result = checker.check_all_prerequisites()
                assert result.all_available is False

                message = checker.format_missing_prerequisites(result.missing_tools)

                # Message should contain all missing tools
                assert all(tool in message.lower() for tool in ["node", "npm", "uv", "git"])
                # Installation commands
                assert "brew install" in message
                # Helpful context
                assert "prerequisite" in message.lower()
```

### Key Points

- **60% unit tests** - Fast, focused tests with heavy mocking
- **30% integration tests** - Multiple components working together
- **10% E2E tests** - Complete workflows with minimal mocking
- **Explicit test organization** - Comment blocks separate test levels
- **Strategic mocking** - Mock platform.system(), shutil.which(), subprocess calls
- **Test data structures** - Verify dataclass behavior

### When to Use

- System utilities that interact with OS/external tools
- Modules with platform-specific behavior
- Code that calls subprocess frequently
- Any module that needs fast tests despite external dependencies

### Benefits

- Fast test execution (all tests run in seconds)
- High confidence without slow E2E tests
- Easy to run in CI
- Clear test organization

### Trade-offs

- Heavy mocking may miss integration issues
- Platform-specific behavior harder to test comprehensively
- Mock maintenance when APIs change

### Related Patterns

- Tests the Fail-Fast Prerequisite Checking pattern
- Verifies Safe Subprocess Wrapper behavior
- Validates Platform-Specific Installation Guidance

### Real Impact

From PR #457: 70 tests run in < 2 seconds, providing comprehensive coverage of platform detection, tool checking, and error formatting without requiring actual tools installed.

## Pattern: Standard Library Only for Core Utilities

### Challenge

Core system utilities gain external dependencies, causing circular dependency issues or installation problems for users without those dependencies.

### Solution

Use only Python standard library for core utility modules. If advanced features need external dependencies, make them optional.

```python
"""Prerequisite checking and installation guidance.

Philosophy:
- Standard library only (no dependencies)
- Safe subprocess error handling throughout
- Platform-specific installation commands
- Never auto-install (user control and security)

Public API:
    PrerequisiteChecker: Main class for checking prerequisites
    safe_subprocess_call: Safe wrapper for all subprocess operations
    Platform: Enum of supported platforms
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# No external dependencies - only stdlib

class PrerequisiteChecker:
    """Check prerequisites using only standard library."""

    def check_tool(self, tool: str) -> bool:
        """Check if tool is available using stdlib shutil.which()"""
        return shutil.which(tool) is not None

    def _detect_platform(self) -> str:
        """Detect platform using stdlib platform module"""
        system = platform.system()

        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            # Check for WSL using /proc/version (stdlib pathlib)
            proc_version = Path("/proc/version")
            if proc_version.exists():
                if "microsoft" in proc_version.read_text().lower():
                    return "wsl"
            return "linux"
        elif system == "Windows":
            return "windows"
        else:
            return "unknown"
```

### Key Points

- **Zero external dependencies** - Only use Python stdlib
- **Document in module docstring** - Make constraint clear
- **Use stdlib alternatives** - shutil.which(), platform.system(), pathlib
- **Optional advanced features** - If needed, make them try/except imports
- **Clear **all** exports** - Define public API explicitly

### When to Use

- Core utility modules
- Modules imported early in startup
- System-level functionality (platform detection, path resolution)
- Modules that check for other dependencies

### Benefits

- No circular dependency issues
- Works immediately after Python installation
- Easy to vendor or copy between projects
- Faster import time

### Trade-offs

- May need to reimplement features available in external packages
- More verbose code without helper libraries
- Limited to stdlib capabilities

### Related Patterns

- Enables Fail-Fast Prerequisite Checking (no bootstrap problem)
- Supports Bricks & Studs modular design
- Follows Zero-BS Implementation (all code works)

### Real Impact

From PR #457: Prerequisites module has zero dependencies, preventing circular import issues when checking for tools needed by other parts of the system.

## Pattern: Bricks & Studs Module Design with Clear Public API

### Challenge

Modules become tightly coupled, making it hard to regenerate or replace them. Internal implementation details leak into public usage.

### Solution

Design modules as self-contained "bricks" with clear "studs" (public API) defined via **all**.

```python
"""Prerequisite checking and installation guidance.

This module provides comprehensive prerequisite checking for all required tools.

Philosophy:
- Check prerequisites early and fail fast with helpful guidance
- Provide platform-specific installation commands
- Never auto-install (user control and security)
- Standard library only (no dependencies)

Public API (the "studs" that other modules connect to):
    PrerequisiteChecker: Main class for checking prerequisites
    safe_subprocess_call: Safe wrapper for all subprocess operations
    Platform: Enum of supported platforms
    PrerequisiteResult: Results of prerequisite checking
    ToolCheckResult: Results of individual tool checking
"""

# ... implementation ...

# Define public API explicitly
__all__ = [
    "Platform",
    "ToolCheckResult",
    "PrerequisiteResult",
    "PrerequisiteChecker",
    "safe_subprocess_call",
    "check_prerequisites",
]
```

### Module Structure

```
src/amplihack/utils/
└── prerequisites.py          # Self-contained module (428 lines)
    ├── Module docstring      # Philosophy and public API
    ├── Platform enum         # Platform types
    ├── ToolCheckResult      # Individual tool results
    ├── PrerequisiteResult   # Overall results
    ├── safe_subprocess_call # Safe subprocess wrapper
    ├── PrerequisiteChecker  # Main class
    └── __all__              # Explicit public API

tests/
├── test_prerequisites.py              # 35 unit tests
├── test_subprocess_error_handling.py  # 22 error handling tests
└── test_prerequisite_integration.py   # 13 integration tests
```

### Key Points

- **Single file module** - One file, one responsibility
- **Module docstring documents philosophy** - Explain design decisions
- **Public API in docstring** - List all public exports
- \***\*all** defines studs\*\* - Explicit public interface
- **Standard library only** - No external dependencies (when possible)
- **Comprehensive tests** - Test the public API contract

### When to Use

- Any utility module
- Modules that might be regenerated by AI
- Shared functionality used across codebase
- System-level utilities

### Benefits

- Clear contract for consumers
- Easy to regenerate from specification
- No accidental tight coupling
- Simple to replace or refactor

### Trade-offs

- May have some internal code duplication
- Resists sharing internal helpers
- Larger single files

### Related Patterns

- Enables Module Regeneration Structure
- Follows Zero-BS Implementation
- Works with Standard Library Only pattern

### Real Impact

From PR #457: Prerequisites module can be used by any part of the system without worrying about internal implementation details. Clear **all** makes public API obvious.

## Remember

These patterns represent hard-won knowledge from real development challenges. When facing similar problems:

1. **Check this document first** - Don't reinvent solutions
2. **Update when you learn something new** - Keep patterns current
3. **Include context** - Explain why, not just how
4. **Show working code** - Examples should be copy-pasteable
5. **Document the gotchas** - Save others from the same pain
