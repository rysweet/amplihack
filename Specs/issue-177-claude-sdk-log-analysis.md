# Issue 177: Claude Code SDK-Based Log Analysis Architecture

## Problem Analysis

### Context

- **PR 178 CLOSED**: Implemented pattern matching instead of real Claude AI analysis
- **Issue 177 Requirement**: Analyze claude-trace logs using actual Claude AI via SDK
- **Critical Constraint**: "only use claude code sdk" - no simulation, no pattern matching
- **Validation Requirement**: Must prove real AI analysis through 4 critical tests

### Problem Decomposition

**Core Challenge**: Integrate Claude Code SDK to analyze JSON logs and extract insights that only AI can identify.

**Why Pattern Matching Failed**: Pattern matching can't understand:

- Semantic relationships between errors and fixes
- Context-dependent improvement opportunities
- Novel patterns not previously seen
- Quality/clarity of prompts
- Code improvement opportunities beyond keyword matches

**Why Real AI Succeeds**: Claude AI can:

- Understand code semantics
- Identify improvement opportunities contextually
- Generate novel insights
- Analyze prompt quality holistically
- Make judgment calls on confidence/priority

## Solution Architecture

### Design Philosophy

**Ruthless Simplicity**:

- Start with minimum viable SDK integration
- One module per responsibility
- No fallback to simulation (real SDK or fail gracefully)
- Clear error messages when SDK unavailable

**Modular Bricks**:

1. `jsonl_parser.py` - Parse logs (reusable from PR 178)
2. `sdk_analyzer.py` - **NEW**: Real Claude AI via SDK
3. `deduplication.py` - Prevent duplicates (reusable from PR 178)
4. `github_integration.py` - Create issues (reusable from PR 178)
5. `orchestrator.py` - Coordinate workflow

**Zero-BS Commitment**:

- SDK must actually be called (no fake responses)
- Errors fail visibly (no silent fallbacks)
- Every function works or raises clear exception

### System Architecture

```
┌──────────────────┐
│  claude-trace    │
│   JSONL Logs     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────┐
│  JSONL Parser    │────▶│  Parsed Entries     │
│  (Reusable)      │     │  (Structured Data)  │
└──────────────────┘     └──────────┬──────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   SDK Analyzer       │
                         │   ┌───────────────┐  │
                         │   │ Prompt Builder│  │
                         │   └───────┬───────┘  │
                         │           ▼          │
                         │   ┌───────────────┐  │
                         │   │  MCP Call     │  │
                         │   │ executeCode   │  │
                         │   └───────┬───────┘  │
                         │           ▼          │
                         │   ┌───────────────┐  │
                         │   │ Response Parse│  │
                         │   └───────────────┘  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Improvement         │
                         │  Patterns            │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Deduplication       │
                         │  Engine (Reusable)   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  GitHub Integration  │
                         │  (Reusable)          │
                         └──────────────────────┘
```

## Module Specifications

### Module 1: jsonl_parser.py (REUSABLE)

**Purpose**: Parse claude-trace JSONL files into structured entries

**Contract**:

- **Inputs**:
  - `file_path: str` - Path to JSONL file
  - `max_entries: int = 10000` - Safety limit
- **Outputs**:
  - `List[ParsedEntry]` - Structured log entries
- **Side Effects**:
  - File I/O (read-only)
  - Logging warnings for malformed entries

**Status**: Can be reused from PR 178 (already implements secure parsing)

---

### Module 2: sdk_analyzer.py (NEW - CRITICAL)

**Purpose**: Analyze log entries using actual Claude AI via `mcp__ide__executeCode`

**Contract**:

- **Inputs**:
  - `entries: List[ParsedEntry]` - Parsed log entries
  - `analysis_type: AnalysisType` - Code/Prompt/System
  - `config: SDKConfig` - SDK configuration
- **Outputs**:
  - `List[ImprovementPattern]` - AI-identified improvements
- **Side Effects**:
  - Calls `mcp__ide__executeCode` (Claude Code SDK)
  - Network I/O (API calls)
  - Logging analysis metadata

**Public Interface (Studs)**:

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

class AnalysisType(Enum):
    CODE_IMPROVEMENT = "code_improvement"
    PROMPT_IMPROVEMENT = "prompt_improvement"
    SYSTEM_FIX = "system_fix"

@dataclass
class SDKConfig:
    """Configuration for SDK analyzer"""
    timeout_seconds: int = 60
    max_retries: int = 3
    batch_size: int = 50  # Entries per SDK call
    enable_caching: bool = True

@dataclass
class ImprovementPattern:
    """AI-identified improvement pattern"""
    id: str
    type: str  # "code_improvement", "prompt_improvement", "system_fix"
    subtype: str  # "bug_fix", "clarity", "connection", etc.
    description: str  # Human-readable description
    confidence: float  # 0.0 to 1.0
    evidence: List[str]  # Supporting evidence from logs
    suggested_action: str  # Recommended fix/improvement
    ai_reasoning: str  # NEW: AI's explanation of why this matters
    metadata: Dict[str, Any]

class SDKAnalyzer:
    """Analyzes logs using real Claude AI via SDK"""

    def __init__(self, config: SDKConfig = SDKConfig()):
        self.config = config
        self._validate_sdk_available()

    def _validate_sdk_available(self) -> None:
        """Verify mcp__ide__executeCode is accessible"""
        # Raises RuntimeError if SDK unavailable
        pass

    def analyze(
        self,
        entries: List[ParsedEntry],
        analysis_type: AnalysisType
    ) -> List[ImprovementPattern]:
        """
        Analyze entries using Claude AI.

        Raises:
            RuntimeError: If SDK unavailable or fails
            ValueError: If entries invalid
        """
        pass

    def _build_analysis_prompt(
        self,
        entries: List[ParsedEntry],
        analysis_type: AnalysisType
    ) -> str:
        """Build prompt for Claude AI analysis"""
        pass

    def _call_claude_sdk(self, prompt: str) -> str:
        """
        Call mcp__ide__executeCode with analysis code.

        The code executes in a Jupyter kernel and returns
        structured analysis results as JSON.
        """
        pass

    def _parse_ai_response(self, response: str) -> List[ImprovementPattern]:
        """Parse AI response into structured patterns"""
        pass
```

**Key Design Decisions**:

1. **MCP Function Selection**: Use `mcp__ide__executeCode`
   - **Why**: Allows executing Python code in Jupyter kernel
   - **How**: Send analysis code that processes entries and returns JSON
   - **Alternative Considered**: Direct API calls (rejected - not "Claude Code SDK")

2. **Prompt Strategy**: Domain-specific analysis prompts
   - **Code Improvements**: Focus on bugs, performance, security
   - **Prompt Improvements**: Focus on clarity, context, specificity
   - **System Fixes**: Focus on connection, memory, API issues
   - **Why**: Specialized prompts yield better results than generic analysis

3. **Batching**: Process 50 entries per SDK call
   - **Why**: Balance between context size and processing time
   - **Trade-off**: Larger batches = more context but slower/costlier

4. **Error Handling**: Fail loudly, no silent fallbacks
   - **Why**: Debugging is easier when failures are explicit
   - **How**: Raise exceptions with clear error messages

**Implementation Strategy**:

```python
# Example SDK call pattern
def _call_claude_sdk(self, prompt: str) -> str:
    """Call Claude via mcp__ide__executeCode"""

    # Build Python code to execute in Jupyter kernel
    analysis_code = f"""
import json

# Entries data passed as string
entries_json = '''{json.dumps([e.to_dict() for e in entries])}'''
entries = json.loads(entries_json)

# Analysis instructions from prompt
analysis_instructions = '''{prompt}'''

# Perform analysis (Claude executes this)
improvements = []

for entry in entries:
    # Claude AI analyzes each entry contextually
    # This is where real AI understanding happens
    # Output structured improvement patterns
    pass

# Return as JSON
print(json.dumps(improvements))
"""

    try:
        # Use MCP function (available in Claude Code SDK)
        result = mcp__ide__executeCode(code=analysis_code)
        return result
    except Exception as e:
        raise RuntimeError(f"SDK call failed: {e}")
```

**Validation Points**:

- SDK actually called (verified via mocking in tests)
- Different content yields different AI analysis
- No hardcoded responses
- AI demonstrates understanding (reasoning field populated)

---

### Module 3: deduplication.py (REUSABLE)

**Purpose**: Prevent duplicate GitHub issues

**Contract**:

- **Inputs**:
  - `patterns: List[ImprovementPattern]` - New patterns
  - `existing_patterns: List[ImprovementPattern]` - Historical patterns
  - `similarity_threshold: float = 0.8` - Match threshold
- **Outputs**:
  - `List[ImprovementPattern]` - Deduplicated patterns
- **Side Effects**:
  - None (pure function)

**Status**: Can be reused from PR 178 with minor adaptation for new `ImprovementPattern` structure

---

### Module 4: github_integration.py (REUSABLE)

**Purpose**: Create GitHub issues for improvements

**Contract**:

- **Inputs**:
  - `pattern: ImprovementPattern` - Improvement to issue
  - `repo_config: GitHubConfig` - Repository settings
- **Outputs**:
  - `IssueResult` - Created issue details
- **Side Effects**:
  - GitHub API calls
  - Creates GitHub issues

**Status**: Can be reused from PR 178 (already implements issue creation)

---

### Module 5: orchestrator.py

**Purpose**: Coordinate the full workflow

**Contract**:

- **Inputs**:
  - `trace_files: List[str]` - JSONL files to analyze
  - `config: WorkflowConfig` - Overall configuration
- **Outputs**:
  - `AnalysisResult` - Summary of analysis and issues created
- **Side Effects**:
  - Calls all other modules
  - Logging workflow progress

**Public Interface**:

```python
@dataclass
class WorkflowConfig:
    """Overall workflow configuration"""
    sdk_config: SDKConfig
    github_config: GitHubConfig
    deduplication_threshold: float = 0.8
    create_issues: bool = True  # False for dry run

@dataclass
class AnalysisResult:
    """Results from full analysis workflow"""
    success: bool
    files_processed: int
    patterns_identified: int
    patterns_after_dedup: int
    issues_created: int
    execution_time_seconds: float
    error_message: Optional[str] = None

class TraceAnalyzer:
    """Main orchestrator for claude-trace analysis"""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.parser = JSONLParser()
        self.sdk_analyzer = SDKAnalyzer(config.sdk_config)
        self.deduplicator = Deduplicator()
        self.github = GitHubIntegration(config.github_config)

    def analyze_trace_files(
        self,
        trace_files: List[str]
    ) -> AnalysisResult:
        """
        Main workflow: parse → analyze → deduplicate → create issues

        Returns structured result even on partial failure.
        """
        pass
```

---

## Validation Test Designs

### Test 1: No Hardcoded Responses

**Purpose**: Prove AI generates different analysis for different content

**Test Design**:

```python
def test_no_hardcoded_responses():
    """Different log content yields different AI analysis"""

    # Two completely different log scenarios
    logs_scenario_a = create_logs_with_authentication_errors()
    logs_scenario_b = create_logs_with_performance_issues()

    analyzer = SDKAnalyzer()

    results_a = analyzer.analyze(logs_scenario_a, AnalysisType.CODE_IMPROVEMENT)
    results_b = analyzer.analyze(logs_scenario_b, AnalysisType.CODE_IMPROVEMENT)

    # Results must be semantically different
    assert results_a[0].description != results_b[0].description
    assert results_a[0].subtype != results_b[0].subtype
    assert results_a[0].ai_reasoning != results_b[0].ai_reasoning

    # AI reasoning must reflect actual content
    assert "authentication" in results_a[0].ai_reasoning.lower()
    assert "performance" in results_b[0].ai_reasoning.lower()
```

**Pass Criteria**: Different inputs produce contextually different outputs

---

### Test 2: Real SDK Usage

**Purpose**: Verify `mcp__ide__executeCode` is actually called

**Test Design**:

```python
def test_real_sdk_called(monkeypatch):
    """Verify mcp__ide__executeCode is invoked"""

    sdk_calls = []

    # Mock/spy the SDK function
    def mock_execute_code(code: str) -> str:
        sdk_calls.append(code)
        # Return realistic JSON response
        return json.dumps([{
            "type": "code_improvement",
            "description": "Optimize database query",
            "confidence": 0.85
        }])

    monkeypatch.setattr(
        'sdk_analyzer.mcp__ide__executeCode',
        mock_execute_code
    )

    analyzer = SDKAnalyzer()
    logs = create_sample_logs()
    analyzer.analyze(logs, AnalysisType.CODE_IMPROVEMENT)

    # SDK must have been called at least once
    assert len(sdk_calls) > 0
    # Code sent to SDK must contain analysis logic
    assert "improvements" in sdk_calls[0]
    assert "json" in sdk_calls[0].lower()
```

**Pass Criteria**: `mcp__ide__executeCode` called with valid Python code

---

### Test 3: No Pattern Matching Dependency

**Purpose**: Prove AI analyzes without keyword triggers

**Test Design**:

```python
def test_no_pattern_matching():
    """AI identifies improvements without obvious keywords"""

    # Logs with subtle issues (no obvious keywords)
    logs_with_subtle_issues = [
        {
            "type": "completion",
            "data": {
                "code_before": "users = db.query(User).all()",
                "code_after": "users = db.query(User).limit(100).all()",
                # No keywords like "fix", "bug", "improvement"
            }
        }
    ]

    analyzer = SDKAnalyzer()
    results = analyzer.analyze(
        logs_with_subtle_issues,
        AnalysisType.CODE_IMPROVEMENT
    )

    # AI should identify this as a performance improvement
    # even without explicit keywords
    assert len(results) > 0
    assert "performance" in results[0].subtype.lower()
    assert results[0].confidence > 0.5

    # AI reasoning should explain the improvement
    assert "limit" in results[0].ai_reasoning.lower()
    assert len(results[0].ai_reasoning) > 50  # Substantive explanation
```

**Pass Criteria**: AI identifies improvements in logs without obvious keywords

---

### Test 4: AI Understanding

**Purpose**: Verify AI demonstrates comprehension, not template filling

**Test Design**:

```python
def test_ai_understanding():
    """AI shows semantic understanding of code/issues"""

    # Complex scenario requiring understanding
    logs_complex_scenario = [
        {
            "type": "error",
            "data": {
                "error_type": "OperationalError",
                "error_message": "connection pool exhausted",
                "fix_applied": "increased pool size from 5 to 20",
                "performance_before": "100 req/s with failures",
                "performance_after": "150 req/s, no failures"
            }
        }
    ]

    analyzer = SDKAnalyzer()
    results = analyzer.analyze(
        logs_complex_scenario,
        AnalysisType.SYSTEM_FIX
    )

    # AI must provide substantive reasoning
    assert len(results) > 0
    reasoning = results[0].ai_reasoning

    # Reasoning must demonstrate understanding:
    # 1. Connects cause (pool exhaustion) to fix (increased size)
    # 2. Recognizes performance improvement
    # 3. Suggests proactive action
    assert "pool" in reasoning.lower()
    assert "connection" in reasoning.lower()
    assert len(reasoning) > 100  # Not a template

    # Suggested action must be specific and contextual
    action = results[0].suggested_action
    assert len(action) > 50
    assert "monitor" in action.lower() or "configure" in action.lower()
```

**Pass Criteria**: AI provides contextual reasoning demonstrating semantic understanding

---

## Implementation Plan

### Phase 1: SDK Integration Foundation (HIGH PRIORITY)

**Step 1.1**: Create `sdk_analyzer.py` skeleton

- Define all classes and interfaces
- Stub out methods with clear TODOs
- Add comprehensive docstrings

**Step 1.2**: Implement SDK availability check

- `_validate_sdk_available()` method
- Test that it correctly detects MCP function
- Fail gracefully with clear error if unavailable

**Step 1.3**: Implement basic SDK call

- `_call_claude_sdk()` method
- Simple test: pass JSON, get JSON back
- Verify actual `mcp__ide__executeCode` usage

**Step 1.4**: Implement prompt builder

- `_build_analysis_prompt()` method
- Create prompts for each `AnalysisType`
- Include clear instructions for structured output

**Step 1.5**: Implement response parser

- `_parse_ai_response()` method
- Handle JSON parsing errors
- Validate response structure

**Step 1.6**: Wire up full `analyze()` method

- Connect all pieces
- Add error handling
- Implement batching

**Validation**: Run Test 2 (Real SDK Usage)

---

### Phase 2: Analysis Quality (MEDIUM PRIORITY)

**Step 2.1**: Refine analysis prompts

- Iterate on prompt wording
- Test with real claude-trace logs
- Optimize for insight quality

**Step 2.2**: Implement confidence scoring

- AI assigns confidence to each pattern
- Threshold for filtering low-confidence results

**Step 2.3**: Add AI reasoning extraction

- Capture AI's explanation of each improvement
- Include in `ImprovementPattern.ai_reasoning`

**Validation**: Run Tests 1, 3, 4 (Quality tests)

---

### Phase 3: Integration (MEDIUM PRIORITY)

**Step 3.1**: Adapt deduplication for new patterns

- Update similarity algorithm for `ai_reasoning` field
- Test with AI-generated patterns

**Step 3.2**: Adapt GitHub integration

- Update issue templates to include AI reasoning
- Test issue creation with real patterns

**Step 3.3**: Implement orchestrator

- Wire all modules together
- Add progress logging
- Implement dry-run mode

**Validation**: End-to-end test with real logs

---

### Phase 4: Testing & Validation (HIGH PRIORITY)

**Step 4.1**: Implement all 4 validation tests

- Test 1: No hardcoded responses
- Test 2: Real SDK usage
- Test 3: No pattern matching
- Test 4: AI understanding

**Step 4.2**: Performance testing

- Test with large log files (10K+ entries)
- Verify batching works correctly
- Measure execution time

**Step 4.3**: Error handling testing

- Test SDK unavailable scenario
- Test malformed log files
- Test API failures

**Validation**: All tests pass

---

### Phase 5: Documentation (LOW PRIORITY)

**Step 5.1**: Update README

- Document SDK-based approach
- Provide usage examples
- Troubleshooting guide

**Step 5.2**: Add inline documentation

- Comprehensive docstrings
- Type hints
- Usage examples in docstrings

---

## What to Keep from PR 178

**KEEP (Reusable)**:

- `jsonl_parser.py` - Secure JSONL parsing with validation
- `deduplication_engine.py` - Multi-layer duplicate prevention
- `issue_generator.py` - GitHub integration with templates
- Security measures (input validation, sanitization, rate limiting)
- Test infrastructure (unit/integration/e2e structure)

**REPLACE (Pattern matching → SDK)**:

- `pattern_extractor.py` → `sdk_analyzer.py`
  - Remove all regex/keyword-based detection
  - Remove specialized analyzers (CodeAnalyzer, PromptAnalyzer, etc.)
  - Replace with single SDK-based analyzer

**DELETE (No longer needed)**:

- Pattern matching regex definitions
- Keyword-based scoring algorithms
- Simulation/mock analysis code

---

## Risk Assessment & Mitigation

### Risk 1: SDK Unavailable

**Impact**: HIGH - System can't function without SDK
**Likelihood**: LOW - MCP function is part of Claude Code SDK
**Mitigation**:

- Clear error message when SDK unavailable
- Fail early with actionable error
- Documentation on SDK requirements

### Risk 2: SDK Performance

**Impact**: MEDIUM - Analysis may be slow for large logs
**Likelihood**: MEDIUM - AI calls have latency
**Mitigation**:

- Implement batching (50 entries per call)
- Add progress logging
- Implement caching for repeated analysis

### Risk 3: SDK Cost

**Impact**: MEDIUM - AI calls may be expensive
**Likelihood**: HIGH - Each SDK call has cost
**Mitigation**:

- Batch processing to reduce call count
- Confidence threshold to filter low-value patterns
- Dry-run mode for testing

### Risk 4: AI Response Quality

**Impact**: HIGH - Poor analysis defeats the purpose
**Likelihood**: MEDIUM - Depends on prompt quality
**Mitigation**:

- Iterative prompt refinement
- Validation tests for quality
- AI reasoning field for transparency

### Risk 5: Test Validation Failure

**Impact**: CRITICAL - Can't merge if tests don't prove real AI
**Likelihood**: MEDIUM - Tests are strict
**Mitigation**:

- Design tests during architecture phase
- Implement tests alongside SDK integration
- Mock/spy patterns for verification

---

## Success Criteria

**Technical Success**:

1. All 4 validation tests pass
2. `mcp__ide__executeCode` provably called
3. Different content yields different AI analysis
4. AI demonstrates semantic understanding

**Functional Success**:

1. Analyzes ALL claude-trace JSONL logs
2. Identifies improvements in code/prompts/system
3. Creates one GitHub issue per distinct improvement
4. Deduplication prevents duplicates
5. Integration with existing reflection system

**Philosophy Compliance**:

1. Ruthlessly simple SDK integration
2. Modular brick architecture maintained
3. Zero-BS: Real SDK or fail loudly
4. No stubs, no placeholders, no simulation

---

## Next Steps (Implementation)

1. **Builder Agent**: Implement `sdk_analyzer.py` following this spec
2. **Tester Agent**: Implement 4 validation tests
3. **Integration**: Wire everything together in orchestrator
4. **Validation**: Run all tests, iterate until passing
5. **Review**: Philosophy compliance check

This architecture replaces pattern matching with real AI, proves it through strict validation, and maintains the modular philosophy of the project.
