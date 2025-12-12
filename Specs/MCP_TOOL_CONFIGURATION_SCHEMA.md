# MCP Tool Configuration Schema

## Purpose

Defines the standard schema for describing ANY MCP tool's capabilities, expected advantages, and integration requirements. Enables tool-agnostic evaluation framework.

## Schema Definition

### ToolConfiguration

```yaml
# Required Fields
tool_id: string # Unique identifier (lowercase, underscores)
tool_name: string # Human-readable name
version: string # Semantic version (X.Y.Z)
description: string # What the tool does (1-2 sentences)

# Capabilities
capabilities: # List of tool capabilities
  - id: string # Capability identifier
    name: string # Human-readable name
    description: string # What this capability does
    relevant_scenarios: [enum] # Which test categories benefit
    expected_improvement: enum # "faster" | "more_accurate" | "both"
    mcp_commands: [string] # Actual MCP commands this maps to

# Integration
adapter_class: string # Python class name for adapter
setup_required: boolean # Does tool need setup?
setup_instructions: string # How to set up (if required)
health_check_url: string? # Optional health endpoint
environment_variables: dict? # Required env vars

# Evaluation
expected_advantages: # Where we expect improvements
  NAVIGATION: [string] # Expected benefits for navigation
  ANALYSIS: [string] # Expected benefits for analysis
  MODIFICATION: [string] # Expected benefits for modification

baseline_comparison_mode: enum # "with_vs_without" | "before_vs_after"

# Constraints
max_concurrent_calls: int? # Rate limiting
timeout_seconds: int? # Per-call timeout
fallback_behavior: enum? # "fail" | "skip" | "baseline"
```

### Enumerations

```yaml
ScenarioCategory:
  - NAVIGATION # Finding code across files
  - ANALYSIS # Understanding code structure
  - MODIFICATION # Making precise edits

ExpectedImprovement:
  - faster # Reduces time/operations
  - more_accurate # Improves correctness/completeness
  - both # Improves speed AND accuracy

ComparisonMode:
  - with_vs_without # Compare tool-enabled vs disabled (recommended)
  - before_vs_after # Compare tool before/after integration

FallbackBehavior:
  - fail # Fail test if tool unavailable
  - skip # Skip test if tool unavailable
  - baseline # Fall back to baseline approach
```

## Validation Rules

### Required Fields

- All top-level fields except those marked `?` are REQUIRED
- `capabilities` list must have at least 1 item
- `expected_advantages` must cover all relevant scenario categories

### Field Constraints

- `tool_id`: lowercase, underscores only, no spaces
- `version`: valid semver (X.Y.Z where X, Y, Z are integers)
- `adapter_class`: valid Python class name
- `mcp_commands`: must be actual MCP protocol commands
- `max_concurrent_calls`: positive integer
- `timeout_seconds`: positive integer

### Logical Consistency

- Capabilities' `relevant_scenarios` must match keys in `expected_advantages`
- If `setup_required: true`, `setup_instructions` must be non-empty
- If `health_check_url` provided, must be valid URL
- `adapter_class` must exist in `tools/{tool_id}_adapter.py`

## Examples

### Minimal Configuration

```yaml
tool_id: simple_tool
tool_name: "Simple MCP Tool"
version: "1.0.0"
description: "Basic code navigation tool"

capabilities:
  - id: find_files
    name: "File Finder"
    description: "Find files by pattern"
    relevant_scenarios: [NAVIGATION]
    expected_improvement: faster
    mcp_commands: ["files/search"]

adapter_class: "SimpleToolAdapter"
setup_required: false
setup_instructions: ""

expected_advantages:
  NAVIGATION:
    - "Faster file location"

baseline_comparison_mode: "with_vs_without"
```

### Complete Configuration (Serena)

```yaml
tool_id: serena
tool_name: "Serena MCP Server"
version: "1.0.0"
description: "LSP-powered code intelligence for Python, TypeScript, and Go with symbol navigation, hover documentation, and semantic search"

capabilities:
  - id: symbol_navigation
    name: "Symbol Navigation"
    description: "Jump to definitions, find references, locate symbols across files"
    relevant_scenarios: [NAVIGATION, ANALYSIS]
    expected_improvement: both
    mcp_commands:
      - "serena/find_symbol"
      - "serena/goto_definition"
      - "serena/find_references"

  - id: hover_documentation
    name: "Hover Documentation"
    description: "Get inline documentation, type information, and signatures"
    relevant_scenarios: [ANALYSIS]
    expected_improvement: more_accurate
    mcp_commands:
      - "serena/hover"
      - "serena/get_signature"

  - id: semantic_search
    name: "Semantic Search"
    description: "Find code by meaning and intent, not just text matching"
    relevant_scenarios: [NAVIGATION, ANALYSIS]
    expected_improvement: both
    mcp_commands:
      - "serena/semantic_search"
      - "serena/find_similar"

  - id: code_completion
    name: "Code Completion"
    description: "Context-aware code completion suggestions"
    relevant_scenarios: [MODIFICATION]
    expected_improvement: faster
    mcp_commands:
      - "serena/complete"
      - "serena/suggest"

  - id: diagnostics
    name: "Real-time Diagnostics"
    description: "Syntax errors, type errors, linting issues"
    relevant_scenarios: [ANALYSIS, MODIFICATION]
    expected_improvement: more_accurate
    mcp_commands:
      - "serena/diagnostics"
      - "serena/get_errors"

adapter_class: "SerenaToolAdapter"
setup_required: true
setup_instructions: |
  1. Install Serena MCP server: npm install -g serena-mcp
  2. Start server: serena-mcp start --port 8080
  3. Verify health: curl http://localhost:8080/health

health_check_url: "http://localhost:8080/health"
environment_variables:
  SERENA_MCP_URL: "http://localhost:8080"
  SERENA_MCP_ENABLED: "1"

expected_advantages:
  NAVIGATION:
    - "Find symbols across files without text-based false positives"
    - "Jump to definitions instantly (no grep needed)"
    - "Locate all references to functions/classes"
    - "Semantic search finds code by intent, not keywords"

  ANALYSIS:
    - "Accurate type information from LSP, not inference"
    - "Complete dependency graphs including transitive deps"
    - "Inline documentation without reading source files"
    - "Real-time diagnostics catch errors before execution"

  MODIFICATION:
    - "Context-aware edit suggestions based on types"
    - "Code completion reduces boilerplate writing"
    - "Error detection prevents invalid edits"

baseline_comparison_mode: "with_vs_without"

# Optional constraints
max_concurrent_calls: 10
timeout_seconds: 30
fallback_behavior: baseline
```

### Future Tool (GitHub Copilot MCP)

```yaml
tool_id: github_copilot_mcp
tool_name: "GitHub Copilot MCP Server"
version: "1.0.0"
description: "AI-powered code completion and generation via GitHub Copilot"

capabilities:
  - id: code_generation
    name: "Code Generation"
    description: "Generate complete functions from natural language"
    relevant_scenarios: [MODIFICATION]
    expected_improvement: faster
    mcp_commands:
      - "copilot/generate"
      - "copilot/complete_function"

  - id: code_explanation
    name: "Code Explanation"
    description: "Natural language explanations of code"
    relevant_scenarios: [ANALYSIS]
    expected_improvement: more_accurate
    mcp_commands:
      - "copilot/explain"

  - id: test_generation
    name: "Test Generation"
    description: "Generate unit tests for functions"
    relevant_scenarios: [MODIFICATION]
    expected_improvement: faster
    mcp_commands:
      - "copilot/generate_tests"

adapter_class: "CopilotToolAdapter"
setup_required: true
setup_instructions: |
  1. Install GitHub Copilot CLI: npm install -g @github/copilot-cli
  2. Authenticate: gh copilot auth
  3. Start MCP server: copilot-mcp start

health_check_url: "http://localhost:8081/health"
environment_variables:
  COPILOT_MCP_URL: "http://localhost:8081"
  COPILOT_API_KEY: "[from-env]"

expected_advantages:
  ANALYSIS:
    - "Natural language explanations of complex code"
    - "Summarize large codebases quickly"

  MODIFICATION:
    - "Generate boilerplate code from descriptions"
    - "Auto-generate unit tests"
    - "Suggest fixes for errors"

baseline_comparison_mode: "with_vs_without"
max_concurrent_calls: 5
timeout_seconds: 60
fallback_behavior: baseline
```

## Loading and Validation

### Python Types

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
import yaml

class ScenarioCategory(Enum):
    NAVIGATION = "NAVIGATION"
    ANALYSIS = "ANALYSIS"
    MODIFICATION = "MODIFICATION"

class ExpectedImprovement(Enum):
    FASTER = "faster"
    MORE_ACCURATE = "more_accurate"
    BOTH = "both"

class ComparisonMode(Enum):
    WITH_VS_WITHOUT = "with_vs_without"
    BEFORE_VS_AFTER = "before_vs_after"

class FallbackBehavior(Enum):
    FAIL = "fail"
    SKIP = "skip"
    BASELINE = "baseline"

@dataclass
class ToolCapability:
    """A single capability an MCP tool provides."""
    id: str
    name: str
    description: str
    relevant_scenarios: List[ScenarioCategory]
    expected_improvement: ExpectedImprovement
    mcp_commands: List[str]

    def __post_init__(self):
        # Convert string enums to enum types
        self.relevant_scenarios = [
            ScenarioCategory(s) if isinstance(s, str) else s
            for s in self.relevant_scenarios
        ]
        if isinstance(self.expected_improvement, str):
            self.expected_improvement = ExpectedImprovement(self.expected_improvement)

@dataclass
class ToolConfiguration:
    """Configuration for a specific MCP tool."""

    # Required fields
    tool_id: str
    tool_name: str
    version: str
    description: str
    capabilities: List[ToolCapability]
    adapter_class: str
    setup_required: bool
    setup_instructions: str
    expected_advantages: Dict[ScenarioCategory, List[str]]
    baseline_comparison_mode: ComparisonMode

    # Optional fields
    health_check_url: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    max_concurrent_calls: Optional[int] = None
    timeout_seconds: Optional[int] = 30
    fallback_behavior: FallbackBehavior = FallbackBehavior.BASELINE

    def __post_init__(self):
        # Convert string enums to enum types
        if isinstance(self.baseline_comparison_mode, str):
            self.baseline_comparison_mode = ComparisonMode(self.baseline_comparison_mode)
        if isinstance(self.fallback_behavior, str):
            self.fallback_behavior = FallbackBehavior(self.fallback_behavior)

        # Convert expected_advantages keys to enums
        self.expected_advantages = {
            ScenarioCategory(k) if isinstance(k, str) else k: v
            for k, v in self.expected_advantages.items()
        }

        # Convert capabilities list of dicts to ToolCapability objects
        self.capabilities = [
            ToolCapability(**cap) if isinstance(cap, dict) else cap
            for cap in self.capabilities
        ]

    @classmethod
    def from_yaml(cls, path: str) -> "ToolConfiguration":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Tool ID validation
        if not self.tool_id.islower() or ' ' in self.tool_id:
            errors.append("tool_id must be lowercase with no spaces")

        # Version validation
        try:
            parts = self.version.split('.')
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append("version must be valid semver (X.Y.Z)")
        except:
            errors.append("version must be valid semver (X.Y.Z)")

        # Capabilities validation
        if not self.capabilities:
            errors.append("capabilities list cannot be empty")

        # Setup instructions validation
        if self.setup_required and not self.setup_instructions.strip():
            errors.append("setup_instructions required when setup_required is true")

        # Consistency validation
        capability_scenarios = set()
        for cap in self.capabilities:
            capability_scenarios.update(cap.relevant_scenarios)

        advantage_scenarios = set(self.expected_advantages.keys())

        if capability_scenarios != advantage_scenarios:
            missing = capability_scenarios - advantage_scenarios
            extra = advantage_scenarios - capability_scenarios
            if missing:
                errors.append(f"expected_advantages missing scenarios: {missing}")
            if extra:
                errors.append(f"expected_advantages has extra scenarios: {extra}")

        # Constraint validation
        if self.max_concurrent_calls is not None and self.max_concurrent_calls <= 0:
            errors.append("max_concurrent_calls must be positive")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")

        return errors

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        # Convert enums back to strings for YAML serialization
        data = {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "version": self.version,
            "description": self.description,
            "capabilities": [
                {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "relevant_scenarios": [s.value for s in cap.relevant_scenarios],
                    "expected_improvement": cap.expected_improvement.value,
                    "mcp_commands": cap.mcp_commands
                }
                for cap in self.capabilities
            ],
            "adapter_class": self.adapter_class,
            "setup_required": self.setup_required,
            "setup_instructions": self.setup_instructions,
            "expected_advantages": {
                k.value: v for k, v in self.expected_advantages.items()
            },
            "baseline_comparison_mode": self.baseline_comparison_mode.value,
        }

        # Add optional fields if present
        if self.health_check_url:
            data["health_check_url"] = self.health_check_url
        if self.environment_variables:
            data["environment_variables"] = self.environment_variables
        if self.max_concurrent_calls:
            data["max_concurrent_calls"] = self.max_concurrent_calls
        if self.timeout_seconds:
            data["timeout_seconds"] = self.timeout_seconds
        data["fallback_behavior"] = self.fallback_behavior.value

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```

### Usage Example

```python
# Load and validate configuration
config = ToolConfiguration.from_yaml("tools/serena_config.yaml")

errors = config.validate()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)

print(f"Loaded configuration for {config.tool_name} v{config.version}")
print(f"Capabilities: {len(config.capabilities)}")
for cap in config.capabilities:
    print(f"  - {cap.name}: {cap.description}")
```

## Configuration Checklist

When creating a new tool configuration:

- [ ] Tool ID is lowercase, no spaces
- [ ] Version follows semver (X.Y.Z)
- [ ] Description is clear and concise (1-2 sentences)
- [ ] All capabilities have valid MCP commands
- [ ] Relevant scenarios match capability usage
- [ ] Expected advantages cover all relevant scenarios
- [ ] Adapter class name matches actual implementation
- [ ] Setup instructions are complete (if setup required)
- [ ] Health check URL is valid (if provided)
- [ ] Environment variables are documented
- [ ] Configuration passes validation
- [ ] Tool adapter exists in `tools/{tool_id}_adapter.py`

## Integration with Evaluation Framework

```python
# Configuration drives evaluation
config = ToolConfiguration.from_yaml("tools/serena_config.yaml")
framework = MCPEvaluationFramework(config)

# Framework uses configuration to:
# 1. Load correct adapter class
# 2. Filter relevant test scenarios
# 3. Set expected advantages for comparison
# 4. Configure health checks
# 5. Apply rate limiting/timeouts
# 6. Handle fallback behavior

report = framework.run_evaluation(all_scenarios)
```

## Versioning Strategy

Configuration files should be versioned alongside tool versions:

```
tools/
├── serena_config_v1.0.0.yaml    # Serena 1.0.0
├── serena_config_v1.1.0.yaml    # Serena 1.1.0 (new capabilities)
├── serena_config.yaml           # Symlink to latest
└── serena_adapter.py            # Adapter handles all versions
```

This allows:

- Testing against multiple tool versions
- Historical comparisons
- Regression detection
- Version-specific optimizations

---

**Status**: Schema Complete
**Next**: Create Serena configuration file using this schema
