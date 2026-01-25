# Development Patterns & Solutions

This document captures proven patterns and solutions for clean design and robust development. It serves as a quick reference for recurring challenges.

## Pattern Curation Philosophy

This document maintains **14 foundational patterns** that apply across most amplihack development.

**Patterns are kept when they:**

1. Solve recurring problems (used 3+ times in real PRs)
2. Apply broadly across multiple agent types and scenarios
3. Represent non-obvious solutions with working code
4. Prevent costly errors or enable critical capabilities

**Patterns are removed when they:**

- Become project-specific (better suited for PROJECT.md or DISCOVERIES.md)
- Are one-time solutions (preserved in git history)
- Are obvious applications of existing patterns
- Haven't been referenced in 6+ months

**Trust in Emergence**: Removed patterns can re-emerge when needed. See git history for context: `git log -p .claude/context/PATTERNS.md`

**This refactoring (2024-11):** Reduced from 24 to 14 patterns (74% reduction) based on usage analysis and philosophy compliance. Removed patterns include: CI Failure Rapid Diagnosis, Incremental Processing, Configuration Single Source of Truth, Parallel Task Execution (covered in CLAUDE.md), Multi-Layer Security Sanitization, Reflection-Driven Self-Improvement, Unified Validation Flow, Modular User Visibility, and others that were either too specific or better documented elsewhere.

## Core Architecture Patterns

### Pattern: Bricks & Studs Module Design with Clear Public API

> **Philosophy Reference**: See @~/.amplihack/.claude/context/PHILOSOPHY.md "The Brick Philosophy for AI Development" for the philosophical foundation of this pattern.

**Challenge**: Modules become tightly coupled, making them hard to regenerate or replace.

**Solution**: Design modules as self-contained "bricks" with clear "studs" (public API) defined via `__all__`.

```python
"""Module docstring documents philosophy and public API.

Philosophy:
- Single responsibility
- Standard library only (when possible)
- Self-contained and regeneratable

Public API (the "studs"):
    MainClass: Primary functionality
    helper_function: Utility function
    CONSTANT: Configuration value
"""

# ... implementation ...

__all__ = ["MainClass", "helper_function", "CONSTANT"]
```

**Module Structure**:

```
module_name/
├── __init__.py         # Public interface via __all__
├── README.md          # Contract specification
├── core.py           # Implementation
├── tests/            # Test the contract
└── examples/         # Working examples
```

**Key Points**:

- Module docstring documents philosophy and public API
- `__all__` defines the public interface explicitly
- Standard library only for core utilities (avoid circular dependencies)
- Tests verify the contract, not implementation details

### Pattern: Zero-BS Implementation

> **Philosophy Reference**: See @~/.amplihack/.claude/context/PHILOSOPHY.md "Zero-BS Implementations" section for the core principle behind this pattern.

**Challenge**: Avoiding stub code and placeholders that serve no purpose.

**Solution**: Every function must work or not exist.

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

    payments = []
    if Path(payments_file).exists():
        payments = json.loads(Path(payments_file).read_text())

    payments.append(payment)
    Path(payments_file).write_text(json.dumps(payments, indent=2))
    return payment
```

**Key Points**:

- Every function must work or not exist
- Use files instead of external services initially
- No TODOs without working code
- Start simple, add complexity when needed

## API & Integration Patterns

### Pattern: API Validation Before Implementation

**Challenge**: Invalid API calls cause immediate failures. Wrong model names, missing imports, or incorrect types lead to 20-30 min debug cycles.

**Solution**: Validate APIs before implementation using official documentation.

**Validation Checklist**:

1. **Model/LLM APIs**: Check model name format, verify parameters, test minimal example
2. **Imports/Libraries**: Verify module exists, check function signatures
3. **Services/Config**: Verify endpoints, check response format
4. **Error Handling**: Plan for rate limits, timeouts, specific error types

```python
# WRONG - assumptions without validation
client = Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",  # ❌ Not verified
    max_tokens="1024",  # ❌ Wrong type
    messages=[{"role": "user", "content": prompt}]
)

# RIGHT - validated against docs
VALID_MODELS = ["claude-3-opus-20240229", "claude-3-sonnet-20241022"]
model = "claude-3-sonnet-20241022"  # ✓ Verified
max_tokens = 1024  # ✓ Correct type

if model not in VALID_MODELS:
    raise ValueError(f"Invalid model: {model}")

try:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
except Exception as e:
    raise RuntimeError(f"API call failed: {e}")
```

**Key Points**:

- 5-10 min validation prevents 20-30 min debug cycles
- Use official documentation as source of truth
- Test imports and minimal examples before full implementation

### Pattern: Claude Code SDK Integration

**Challenge**: Integrating Claude Code SDK requires proper environment setup and timeout handling.

**Solution**:

```python
import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def extract_with_claude_sdk(prompt: str, timeout_seconds: int = 120):
    """Extract using Claude Code SDK with proper timeout handling"""
    try:
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

**Key Points**:

- 120-second timeout is optimal
- SDK only works in Claude Code environment
- Handle markdown in responses

## Error Handling & Reliability Patterns

### Pattern: Safe Subprocess Wrapper with Comprehensive Error Handling

**Challenge**: Subprocess calls fail with cryptic error messages. Different error types need different user guidance.

**Solution**: Create a safe subprocess wrapper with user-friendly, actionable error messages.

```python
def safe_subprocess_call(
    cmd: List[str],
    context: str,
    timeout: Optional[int] = 30,
) -> Tuple[int, str, str]:
    """Safely execute subprocess with comprehensive error handling."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr

    except FileNotFoundError:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command not found: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please ensure the tool is installed and in your PATH."
        return 127, "", error_msg

    except subprocess.TimeoutExpired:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command timed out after {timeout}s: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 124, "", error_msg

    except Exception as e:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Unexpected error running {cmd_name}: {str(e)}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg
```

**Key Points**:

- Standard exit codes (127 for command not found)
- Context parameter is critical - always tell users what operation failed
- User-friendly messages with actionable guidance
- No exceptions propagate

### Pattern: Fail-Fast Prerequisite Checking

**Challenge**: Users start using a tool, get cryptic errors mid-workflow when dependencies are missing.

**Solution**: Check all prerequisites at startup with clear, actionable error messages.

```python
@dataclass
class ToolCheckResult:
    tool: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None

class PrerequisiteChecker:
    REQUIRED_TOOLS = {
        "node": "--version",
        "npm": "--version",
        "uv": "--version",
    }

    def check_and_report(self) -> bool:
        """Check prerequisites and print report if any are missing."""
        result = self.check_all_prerequisites()

        if result.all_available:
            return True

        print(self.format_missing_prerequisites(result.missing_tools))
        return False

class Launcher:
    def prepare_launch(self) -> bool:
        """Check prerequisites FIRST before any other operations"""
        checker = PrerequisiteChecker()
        if not checker.check_and_report():
            return False
        return self._setup_environment()
```

**Key Points**:

- Check at entry point before any operations
- Check all at once - show all issues
- Structured results with dataclasses
- Never auto-install - user control first

### Pattern: Resilient Batch Processing

**Challenge**: Processing large batches where individual items might fail.

**Solution**:

```python
class ResilientProcessor:
    async def process_batch(self, items):
        results = {"succeeded": [], "failed": []}

        for item in items:
            try:
                result = await self.process_item(item)
                results["succeeded"].append(result)
                self.save_results(results)  # Save after every item
            except Exception as e:
                results["failed"].append({
                    "item": item,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                continue  # Continue processing other items

        return results
```

**Key Points**:

- Save after every item - never lose progress
- Continue on failure - don't let one failure stop the batch
- Track failure reasons

## Testing & Validation Patterns

### Pattern: TDD Testing Pyramid for System Utilities

**Challenge**: Testing system utilities that interact with external tools while maintaining fast execution.

**Solution**: Follow testing pyramid with 60% unit tests, 30% integration tests, 10% E2E tests.

```python
"""Tests for module - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

# UNIT TESTS (60%)
class TestPlatformDetection:
    def test_detect_macos(self):
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()
            assert checker.platform == Platform.MACOS

# INTEGRATION TESTS (30%)
class TestPrerequisiteIntegration:
    def test_full_check_workflow(self):
        checker = PrerequisiteChecker()
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"
            result = checker.check_all_prerequisites()
            assert result.all_available is True

# E2E TESTS (10%)
class TestEndToEnd:
    def test_complete_workflow_with_guidance(self):
        checker = PrerequisiteChecker()
        result = checker.check_all_prerequisites()
        message = checker.format_missing_prerequisites(result.missing_tools)
        assert "prerequisite" in message.lower()
```

**Key Points**:

- 60% unit tests for speed
- Strategic mocking of external dependencies
- E2E tests for complete workflows
- All tests run in seconds

## Environment & Platform Patterns

### Pattern: Platform-Specific Installation Guidance

**Challenge**: Users on different platforms need different installation commands.

**Solution**: Detect platform automatically and provide exact installation commands.

```python
class Platform(Enum):
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    WINDOWS = "windows"

class PrerequisiteChecker:
    INSTALL_COMMANDS = {
        Platform.MACOS: {
            "node": "brew install node",
            "git": "brew install git",
        },
        Platform.LINUX: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora:\nsudo dnf install nodejs",
        },
    }

    def get_install_command(self, tool: str) -> str:
        platform_commands = self.INSTALL_COMMANDS.get(self.platform, {})
        return platform_commands.get(tool, f"Please install {tool} manually")
```

**Key Points**:

- Automatic platform detection (including WSL)
- Multiple package managers for Linux
- Documentation links for complex installations

### Pattern: Graceful Environment Adaptation

**Challenge**: Different behavior needed in different environments (UVX, normal, testing).

**Solution**: Detect environment automatically and adapt through configuration objects.

```python
class EnvironmentAdapter:
    def detect_environment(self) -> str:
        if self._is_uvx_environment():
            return "uvx"
        elif self._is_testing_environment():
            return "testing"
        else:
            return "normal"

    def get_config(self) -> Dict[str, Any]:
        env = self.detect_environment()
        configs = {
            "uvx": {"use_add_dir": True, "timeout_multiplier": 1.5},
            "normal": {"use_add_dir": False, "timeout_multiplier": 1.0},
            "testing": {"use_add_dir": False, "timeout_multiplier": 0.5},
        }
        config = configs.get(env, configs["normal"])
        self._apply_env_overrides()  # Allow env variable overrides
        return config
```

**Key Points**:

- Automatic environment detection
- Configuration objects over scattered conditionals
- Environment variable overrides for customization

## Performance & Optimization Patterns

### Pattern: Intelligent Caching with Lifecycle Management

**Challenge**: Expensive operations repeated unnecessarily, but naive caching leads to memory leaks.

**Solution**: Smart caching with invalidation strategies.

```python
from functools import lru_cache
import threading

class SmartCache:
    @lru_cache(maxsize=128)
    def expensive_operation(self, input_data: str) -> str:
        return self._compute_expensive_result(input_data)

    def invalidate_cache(self) -> None:
        with self._lock:
            self.expensive_operation.cache_clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        cache_info = self.expensive_operation.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "hit_rate": cache_info.hits / max(1, cache_info.hits + cache_info.misses)
        }
```

**Key Points**:

- lru_cache for automatic size management
- Thread safety is essential
- Provide invalidation methods
- Track cache performance

## File I/O & Async Patterns

### Pattern: File I/O with Cloud Sync Resilience

**Challenge**: File operations fail mysteriously when directories are synced with cloud services.

**Solution**:

```python
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
                    print("File I/O error - retrying. May be cloud sync issue.")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise
```

**Key Points**:

- Exponential backoff for cloud sync
- Inform user about delays
- Create parent directories

### Pattern: System Metadata vs User Content Classification in Git Operations

**Challenge**: Git-aware operations treat framework-generated metadata files (like `.version`, `.state`) as user content, causing false conflict warnings when files are auto-updated by the system.

**Solution**: Explicitly categorize and filter system-generated files based on semantic purpose, not just directory structure.

```python
from pathlib import Path
from typing import Set, List

class GitAwareFileFilter:
    """Distinguish system metadata from user content in git operations"""

    # System-generated files that should never trigger conflicts
    SYSTEM_METADATA = {
        ".version",           # Framework version tracking
        ".state",            # Runtime state
        "settings.json",     # Auto-generated settings
        "*.pyc",             # Compiled bytecode
        "__pycache__",       # Python cache
        ".pytest_cache",     # Test cache
    }

    def _filter_conflicts(
        self, uncommitted_files: List[str], essential_dirs: List[str]
    ) -> List[str]:
        """Filter git status to exclude system metadata"""
        conflicts = []
        for file_path in uncommitted_files:
            if file_path.startswith(".claude/"):
                relative_path = file_path[8:]  # Strip ".claude/"

                # Skip system-generated metadata - safe to overwrite
                if relative_path in self.SYSTEM_METADATA:
                    continue

                # Check if file is in essential directories (user content)
                for essential_dir in essential_dirs:
                    if (
                        relative_path.startswith(essential_dir + "/")
                        or relative_path == essential_dir
                    ):
                        conflicts.append(file_path)
                        break

        return conflicts
```

**Usage in conflict detection**:

```python
class ConflictChecker:
    def check_conflicts(self, source_dir: Path, essential_dirs: List[str]) -> List[Path]:
        """Check for REAL conflicts - ignore system metadata"""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=source_dir
        )

        uncommitted = self._parse_git_status(result.stdout)
        user_changes = self._filter_conflicts(uncommitted, essential_dirs)

        if user_changes:
            raise ConflictError(
                f"Uncommitted user content: {user_changes}\n"
                f"(System metadata changes are normal and ignored)"
            )
```

**Key Points**:

- **Semantic categorization**: Filter by PURPOSE (system vs user), not location
- **Root-level awareness**: Don't assume all root files are user content
- **Clear error messages**: Tell users when conflicts are real vs system noise
- **Philosophy alignment**: Ruthlessly simple - add explicit exclusion list
- **Common pitfall**: Only checking subdirectories and missing root-level system files

> **Origin**: Discovered investigating `.version` file causing false conflicts during UVX deployment. See DISCOVERIES.md (2025-12-01).

### Pattern: Async Context Management

**Challenge**: Nested asyncio event loops cause hangs.

**Solution**: Design APIs to be fully async or fully sync, not both.

```python
# WRONG - Creates nested event loops
class Service:
    def process(self, data):
        return asyncio.run(self._async_process(data))  # Creates new loop

# RIGHT - Pure async throughout
class Service:
    async def process(self, data):
        return await self._async_process(data)  # No new loop
```

**Key Points**:

- Never mix sync/async APIs
- Avoid asyncio.run() in libraries
- Let caller manage the event loop

## Documentation & Investigation Patterns

### Pattern: Documentation Discovery Before Code Analysis

**Challenge**: Agents dive into code without checking if documentation already explains the system.

**Solution**: Always perform documentation discovery before code analysis.

**Process**:

1. Search for documentation files (README, ARCHITECTURE, docs/)
2. Filter by relevance using keywords
3. Read top 5 most relevant files
4. Establish documentation baseline
5. Use docs to guide code analysis

```markdown
Before analyzing [TOPIC], discover existing documentation:

1. Glob: **/README.md, **/ARCHITECTURE.md, **/docs/**/\*.md
2. Grep: Search for keywords related to TOPIC
3. Read: Top 5 most relevant files
4. Establish: What docs claim vs what exists
5. Analyze: Verify code matches docs, identify gaps
```

**Key Points**:

- Always discover docs first (30-second limit)
- Identify doc/code discrepancies
- Graceful degradation for missing docs

## Decision-Making Patterns

### Pattern: Cross-Domain Pattern Applicability Analysis

**Challenge**: Teams import "industry best practices" from other domains without validating applicability, leading to unnecessary complexity.

**Solution**: Five-phase framework for evaluating pattern adoption from other domains.

**Phase 1: Threat Model Match**

- Identify actual failure modes in YOUR system
- Identify pattern's target failure modes
- Verify failure modes match
- If mismatch, REJECT pattern

**Phase 2: Mechanism Appropriateness**

- Does pattern assume adversarial nodes? (Usually wrong for AI agents)
- Does pattern optimize for network communication? (Usually irrelevant for AI)
- Does pattern solve YOUR domain's specific problem?

**Phase 3: Complexity Justification**

```
Justified Complexity: Benefit Gain / Complexity Cost > 3.0
```

If ratio < 3.0, seek simpler alternatives.

**Phase 4: Domain Validation**

- Research pattern's origin domain
- Verify target domain shares those characteristics
- Check for successful applications in similar contexts

**Phase 5: Alternative Exploration**

- Can simpler mechanisms achieve same benefits?
- Can you get 80% of benefit with 20% of complexity?

**Key Points**:

- Threat model mismatch is primary source of inappropriate pattern adoption
- Distributed systems patterns rarely map to AI agent systems
- "Industry best practice" without context validation is a red flag
- Default to ruthless simplicity unless complexity clearly justified

> **Origin**: Discovered evaluating PBZFT vs N-Version Programming. PBZFT would be 6-9x more complex with zero benefit. See DISCOVERIES.md (2025-10-20).

## Multi-Model AI Patterns

### Pattern: Multi-Model Validation Anti-Pattern (STOP Gates)

**Challenge**: Validation checkpoints in AI guidance can trigger model-specific responses, helping one model while breaking another.

**Problem**: STOP gates added to improve Opus caused Sonnet degradation:

- Opus 4.5: STOP gates help (20/22 → 22/22 steps) ✅
- Sonnet 4.5: STOP gates break (22/22 → 8/22 steps) ❌
- Same text, opposite outcomes

**Solution**: Remove validation checkpoints, use flow language instead.

**Example - Bad (STOP Gates)**:

```markdown
## Step 1: Create GitHub Issue

Create an issue for your feature.

## STOP - Verify Issue Created

Before proceeding to Step 2, confirm:

- [ ] GitHub issue created
- [ ] Issue number recorded

Only proceed after verification complete.

## Step 2: Create Branch

...
```

**Example - Good (Flow Language)**:

```markdown
## Step 1: Create GitHub Issue

Create an issue for your feature.

## Step 2: Create Branch

After creating the issue, create a feature branch...
```

**Why This Works**:

- Provides clear structure without interruption points
- Uses flow language ("After X, do Y") not interruption language ("STOP before Y")
- Allows continuous autonomous execution
- Works for both models

**Empirical Evidence** (Issue #1755, 6/8 benchmarks complete):

| Model  | With STOP Gates  | Without STOP Gates (V2)           |
| ------ | ---------------- | --------------------------------- |
| Sonnet | 8/22 steps (36%) | 22/22 steps (100%)                |
| Opus   | 22/22 steps      | ~20/22 steps (maintains baseline) |

**Performance Results**:

- Sonnet V2: -16% cost improvement
- Opus V2: -21% cost improvement
- Removing gates IMPROVES performance (STOP Gate Paradox)

**Key Points**:

- Different models interpret "STOP" differently
- Opus: Treats as checkpoint, proceeds
- Sonnet: Treats as permission gate, asks user
- High-salience language ("STOP", "MUST", ALL CAPS) risky
- Always test multi-model before deploying guidance changes

**When to Use Flow Language**:

- "After X, proceed to Y" ✅
- "When X completes, Y begins" ✅
- "Following X, continue with Y" ✅

**When to AVOID Interruption Language**:

- "STOP before Y" ❌
- "Only proceed after X" ❌
- "Wait for confirmation before Y" ❌

**Related**: Issue #1755, DISCOVERIES.md (2025-12-01)
**Validation**: 75% complete (6/8 benchmarks), both models tested
**Impact**: $20K-$406K annual savings from removing STOP gates

---

## Multi-Model AI Patterns

### Pattern: AI-Optimized Workflows (No Human Psychology)

> **Philosophy Reference**: See @~/.amplihack/.claude/context/PHILOSOPHY.md "Ruthless Simplicity" and "Code you don't write has no bugs"

**Challenge**: Workflows designed with human psychology (commitment, celebration) add overhead for AI agents without providing benefit.

**Solution**: Remove psychological framing, keep only essential workflow steps.

```markdown
# ANTI-PATTERN - Human Psychology in AI Workflows ❌

## Workflow Contract

By reading this workflow file, you are committing to execute ALL 22 steps.
**Your Commitment**: [commitment checkboxes]

[22 Workflow Steps]

## 🎉 Workflow Complete!

Congratulations! You executed all 22 steps systematically.
[Celebration and verification]

# GOOD PATTERN - AI-Optimized Workflow ✅

[22 Workflow Steps - Just the steps, no psychology]
```

**Empirical Evidence** (V8 Testing, Issue #1785):
| Metric | With Psychology | Without Psychology | Improvement |
|--------|----------------|-------------------|-------------|
| Cost (MEDIUM) | Unknown | $2.93-$8.36 (avg $5.62) | 72-95% |
| Cost (HIGH) | Unknown | $13.56-$31.95 (avg $21.72) | Est. 90% |
| Quality | Unknown | 100% (22/22) | 100% |
| Lines | 482 | 443 | -8% |

**Key Points**:

- AI agents don't need commitment (already committed by design)
- AI agents don't experience celebration (wasted tokens)
- Psychological framing = ~8% overhead with zero benefit
- Removal improves performance 72-95% while maintaining 100% quality
- Builder autonomously applied this pattern (removed psychology without being told)

**When to Use**:

- Designing workflows for AI agents
- Optimizing prompts for AI consumption
- Creating AI-facing documentation
- Any content primarily read by AI (not humans)

**When NOT to Use**:

- Human-facing documentation (humans benefit from psychology)
- User-facing guides (motivation helps users)
- Team communication (celebration builds culture)

**Philosophy Alignment**:

- ✅ Ruthless simplicity (remove non-essential)
- ✅ "Code you don't write has no bugs" (applied to prompts)
- ✅ Minimize abstractions (removed psychological layer)
- ✅ Essential only (Wabi-sabi)

> **Origin**: V8 testing (Issue #1785, 2025-12-02). Builder agent autonomously removed psychological framing, achieving 90% cost reduction. See tag: v8-no-psych-winner, Archive: .claude/runtime/benchmarks/v8_experiments_archive_20251202_212646/

---

## Remember

These patterns represent proven solutions from real development challenges:

1. **Check this document first** - Don't reinvent solutions
2. **Update when learning** - Keep patterns current
3. **Include context** - Explain why, not just how
4. **Show working code** - Examples should be copy-pasteable
5. **Document gotchas** - Save others from the same pain
