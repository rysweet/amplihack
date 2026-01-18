---
name: N_VERSION_WORKFLOW
version: 1.0.0
description: N-version programming for critical code - generate multiple independent implementations and select best
steps: 7
phases:
  - common-context-preparation
  - n-independent-implementations
  - collection-and-comparison
  - review-and-evaluation
  - selection-or-synthesis
  - final-implementation
  - learning-documentation
success_criteria:
  - "N independent implementations generated (N=2-6)"
  - "All implementations tested against same specification"
  - "Selection based on correctness > security > simplicity > philosophy > performance"
  - "Best solution identified or hybrid synthesized"
  - "Learnings from rejected versions captured"
philosophy_alignment:
  - principle: Reduced Risk
    application: Multiple implementations catch errors single approach misses
  - principle: Exploration
    application: Different approaches reveal design trade-offs
  - principle: Evidence-Based Selection
    application: Systematic comparison vs gut feeling
  - principle: Learning
    application: Rejected versions provide valuable insights
references:
  workflows:
    - DEFAULT_WORKFLOW.md
    - CONSENSUS_WORKFLOW.md
customizable: true
---

# N-Version Programming Workflow

This workflow implements N-version programming for critical decisions where multiple independent implementations should be generated and compared to select the best solution.

> **DEPRECATION WARNING**: Markdown workflows deprecated. See `docs/WORKFLOW_TO_SKILLS_MIGRATION.md`

## Configuration

### Core Parameters

**N (Number of Versions)**: Number of independent implementations to generate

- `3` - Default for standard tasks
- `4-6` - Critical features requiring high confidence
- `2` - Quick validation of approach

**Selection Criteria** (in priority order):

1. Correctness - Meets all requirements and passes tests
2. Security - No vulnerabilities or security anti-patterns
3. Simplicity - Ruthless simplicity, minimal complexity
4. Philosophy Compliance - Follows project principles
5. Performance - Efficiency and resource usage

**Agent Diversity Profiles** (optional):

- `conservative` - Focus on proven patterns and safety
- `innovative` - Explore novel approaches and optimizations
- `minimalist` - Prioritize ruthless simplicity
- `pragmatic` - Balance trade-offs for practical solutions
- `performance-focused` - Optimize for speed and efficiency

### Cost-Benefit Analysis

**When to Use:**

- Critical security features (authentication, authorization)
- Complex algorithms with multiple valid approaches
- High-risk refactoring of core components
- Architecture decisions with significant long-term impact
- When correctness is paramount over speed

**When NOT to Use:**

- Simple CRUD operations
- Straightforward bug fixes
- Documentation updates
- Minor UI tweaks
- Time-sensitive quick fixes

**Trade-offs:**

- Cost: N times the compute resources and time
- Benefit: Significantly reduced risk of critical errors
- Best for: Features where bugs are expensive (security, data integrity)

## How This Workflow Works

**Integration with DEFAULT_WORKFLOW:**

This workflow replaces Steps 4-5 (Research/Design and Implementation) of the DEFAULT_WORKFLOW when enabled. All other steps (requirements, testing, CI/CD) remain the same.

**Execution:**

- Invoke via `/ultrathink --workflow n-version` for critical tasks
- Or manually execute these steps for specific implementation phases
- Agents work in isolated subprocesses with no context sharing
- Results are collected and evaluated systematically

## The N-Version Workflow

### Step 1: Prepare Common Context

- [ ] **Use** prompt-writer agent to create crystal-clear specification
- [ ] Document all requirements explicitly
- [ ] Define success criteria measurably
- [ ] Prepare identical task specification for all N versions
- [ ] Identify evaluation metrics upfront
- [ ] **CRITICAL: Capture explicit user requirements that CANNOT be optimized away**

**Output**: Single authoritative specification document used by all implementations

### Step 2: Generate N Independent Implementations

- [ ] Spawn N Claude subprocesses simultaneously
- [ ] Each subprocess receives IDENTICAL task specification
- [ ] **NO context sharing between subprocesses** (true independence)
- [ ] Each uses different agent diversity profile (if configured)
- [ ] Each produces complete implementation with tests
- [ ] Each works in isolated directory (version_1/, version_2/, etc.)

**Implementation Details:**

- Subprocess 1: Assigned `conservative` profile
- Subprocess 2: Assigned `pragmatic` profile
- Subprocess 3: Assigned `minimalist` profile
- Subprocesses 4-N: Rotate through remaining profiles

**Parallelization**: All N implementations execute in parallel for maximum speed

**Example for N=3:**

```
Subprocess 1: Conservative approach
  - Use proven design patterns
  - Comprehensive error handling
  - Defensive programming

Subprocess 2: Pragmatic approach
  - Balance simplicity and robustness
  - Standard library solutions
  - Practical trade-offs

Subprocess 3: Minimalist approach
  - Ruthless simplification
  - Minimal dependencies
  - Direct implementation
```

### Step 3: Collect and Compare Implementations

- [ ] Wait for all N implementations to complete
- [ ] Collect outputs from all subprocesses
- [ ] **Use** analyzer agent to examine each implementation
- [ ] **Use** tester agent to run tests for each version
- [ ] Document results in comparison matrix

**Comparison Matrix Structure:**

```
| Version | Correctness | Security | Simplicity | Philosophy | Performance | Lines of Code |
|---------|-------------|----------|------------|------------|-------------|---------------|
| v1      | PASS        | PASS     | 7/10       | 8/10       | 150ms       | 180           |
| v2      | PASS        | PASS     | 9/10       | 9/10       | 180ms       | 95            |
| v3      | FAIL        | N/A      | 10/10      | 7/10       | N/A         | 65            |
```

### Step 4: Review and Evaluate

- [ ] **Use** reviewer agent to perform comprehensive comparison
- [ ] **Use** security agent to evaluate security of each version
- [ ] Apply selection criteria in priority order
- [ ] Eliminate versions that fail correctness tests
- [ ] Compare remaining versions on other criteria
- [ ] Identify best parts of each implementation

**Evaluation Process:**

1. Filter: Remove any versions failing correctness tests
2. Security Gate: Eliminate versions with security issues
3. Philosophy Check: Score each on simplicity and compliance
4. Performance Compare: Measure and compare benchmarks
5. Synthesis: Identify if hybrid approach could be superior

### Step 5: Select or Synthesize Solution

- [ ] **Decision Point**: Choose best single version OR synthesize hybrid
- [ ] If one version clearly superior: Select it
- [ ] If versions have complementary strengths: Synthesize hybrid
- [ ] **Use** architect agent to design synthesis if needed
- [ ] Document selection rationale thoroughly
- [ ] Explain why chosen approach was selected
- [ ] Document what was learned from rejected versions

**Selection Decision Tree:**

```
1. Is there ONE version that passes all criteria?
   YES → Select it and document why
   NO → Continue to step 2

2. Are there 2+ versions tied on top criteria?
   YES → Continue to step 3
   NO → Select highest scoring version

3. Do versions have complementary strengths?
   (e.g., v1 has better error handling, v2 has simpler logic)
   YES → Synthesize hybrid combining best parts
   NO → Select based on weighted criteria priority
```

**Example Synthesis:**

```
Selected: Hybrid of v1 and v2
- Core logic from v2 (ruthless simplicity)
- Error handling from v1 (comprehensive coverage)
- Testing approach from v2 (focused, minimal)
- Documentation style from v1 (thorough)

Rationale: v2's minimalist core paired with v1's robust
error handling provides optimal balance of simplicity
and production-readiness.
```

### Step 6: Implement Selected Solution

- [ ] **Use** builder agent to implement final version
- [ ] If single version selected: Use it directly
- [ ] If synthesis: Implement hybrid combining best parts
- [ ] Preserve all explicit user requirements from Step 1
- [ ] Run full test suite
- [ ] Document selection rationale in code comments

**Documentation Template:**

```python
"""
N-Version Implementation Selection

Generated Versions: 3
Selection: Hybrid of v1 (conservative) and v2 (pragmatic)

Rationale:
- v1 had superior error handling and edge case coverage
- v2 had cleaner architecture and better testability
- v3 failed correctness tests (edge case handling)

This implementation combines v2's core logic with v1's
defensive programming approach for production robustness.

Selection Criteria Applied:
1. Correctness: v1=PASS, v2=PASS, v3=FAIL
2. Security: All passed
3. Simplicity: v2 ranked highest
4. Philosophy: v1 and v2 tied
5. Performance: Negligible difference

See: n_version_analysis.md for full comparison matrix
"""
```

### Step 7: Document Learnings

- [ ] Create analysis document: `n_version_analysis.md`
- [ ] Document all N implementations generated
- [ ] Explain selection rationale in detail
- [ ] Capture insights from rejected versions
- [ ] Store patterns learned in memory using `store_discovery()` from `amplihack.memory.discoveries`
- [ ] Include comparison matrix for future reference

**Analysis Document Structure:**

```markdown
# N-Version Analysis: [Feature Name]

## Configuration

- N = 3
- Profiles: conservative, pragmatic, minimalist
- Selection Criteria: correctness > security > simplicity

## Implementations Generated

### Version 1 (Conservative)

- Approach: [description]
- Strengths: [list]
- Weaknesses: [list]
- Test Results: [summary]

### Version 2 (Pragmatic)

- Approach: [description]
- Strengths: [list]
- Weaknesses: [list]
- Test Results: [summary]

### Version 3 (Minimalist)

- Approach: [description]
- Strengths: [list]
- Weaknesses: [list]
- Test Results: [summary]

## Comparison Matrix

[Include detailed comparison table]

## Selection Decision

Selected: [chosen version or "Hybrid"]
Rationale: [detailed explanation]

## Learnings

- Pattern identified: [description]
- Trade-offs discovered: [list]
- Future recommendations: [list]
```

## Return to DEFAULT_WORKFLOW

After completing these steps:

- [ ] Continue with Step 6 (Refactor and Simplify) of DEFAULT_WORKFLOW
- [ ] All subsequent steps (testing, CI/CD, PR) proceed normally
- [ ] Selected implementation is treated as if it were single implementation

## Examples

### Example 1: Authentication System

**Task**: Implement JWT-based authentication

**Configuration**:

- N = 4 (critical security feature)
- Profiles: conservative, security-focused, pragmatic, minimalist

**Result**:

- v1 (conservative): Most comprehensive but over-engineered
- v2 (security-focused): Excellent security but complex
- v3 (pragmatic): Good balance, missing edge cases
- v4 (minimalist): Too simple, security gaps

**Selection**: Hybrid of v2 and v3

- Security implementation from v2
- API design and simplicity from v3

**Rationale**: Security cannot be compromised, but v3's cleaner API design improved usability without sacrificing security.

### Example 2: Data Processing Pipeline

**Task**: Process large CSV files efficiently

**Configuration**:

- N = 3 (performance-critical)
- Profiles: pragmatic, performance-focused, minimalist

**Result**:

- v1 (pragmatic): Pandas-based, familiar but slow
- v2 (performance-focused): Custom streaming, 10x faster
- v3 (minimalist): Python CSV module, simple but slow

**Selection**: v2 (performance-focused)

**Rationale**: Performance requirements justified complexity. v2's streaming approach met throughput requirements while v1 and v3 could not scale.

### Example 3: Configuration Parser

**Task**: Parse YAML configuration files

**Configuration**:

- N = 3 (standard feature)
- Profiles: pragmatic, minimalist, conservative

**Result**:

- v1 (pragmatic): Full-featured with validation
- v2 (minimalist): Direct PyYAML wrapper
- v3 (conservative): Custom parser, over-engineered

**Selection**: v2 (minimalist)

**Rationale**: PyYAML is battle-tested and sufficient. v1's additional validation was not required by specs. v3's custom parser violated simplicity principle.

## Customization

To customize this workflow:

1. Edit the Configuration section to adjust N, criteria, or profiles
2. Modify selection criteria priority order based on project needs
3. Add or remove agent diversity profiles
4. Adjust evaluation metrics in comparison matrix
5. Save changes - updated workflow applies to future executions

## Philosophy Notes

This workflow enforces:

- **Reduced Risk**: Multiple implementations catch errors single approach might miss
- **Exploration**: Different approaches reveal design trade-offs
- **Evidence-Based Selection**: Systematic comparison vs. gut feeling
- **Learning**: Rejected versions still provide valuable insights
- **Parallel Execution**: N implementations run simultaneously for efficiency
