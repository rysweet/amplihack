# How to Create Your Own Code Analysis Tool

This guide helps you create a tool similar to **Analyze Codebase** by following the proven patterns and architecture.

## Understanding the Pattern

### Core Concept

Analyze Codebase is a **Multi-Agent Analysis Tool** that follows the **Parallel Agent Coordination** pattern. The key insight is:

> "Comprehensive analysis requires multiple specialized perspectives working simultaneously to provide insights no single approach could deliver."

### Architecture Overview

```
Input Target → File Discovery → Agent Dispatch → Parallel Analysis → Result Aggregation → Formatted Output
                    ↓                ↓              ↓                ↓                  ↓
                File Types     [Analyzer Agent]  [Security]      [Combiner]       [Reporter]
                Validation     [Security Agent]  [Performance]   [Correlator]     [Formatter]
                Permission     [Optimizer Agent] [Patterns]      [Prioritizer]    [Exporter]
                Filtering      [Patterns Agent]  [Architecture]
```

## Step-by-Step Creation Guide

### Step 1: Define Your Tool's Purpose

Answer these questions:

- **What problem does your tool solve?**
  "I need to quickly understand the structure, quality, and potential issues in an unfamiliar codebase"

- **Who is your target user?**
  "Developers joining new projects, code reviewers, and architects planning refactoring"

- **What is the minimal viable solution?**
  "A tool that analyzes code files and provides actionable insights about structure and quality"

### Step 2: Choose Your Tool Name

Follow amplihack naming conventions:

- **Format**: `analyze-{domain}` or `{action}-{target}`
- **Examples**: `analyze-api`, `review-security`, `optimize-performance`
- **Your tool**: `analyze-{your-domain}`

### Step 3: Set Up Directory Structure

```bash
# Start in ai_working/ for experimentation
mkdir .claude/ai_working/analyze-{your-domain}
cd .claude/ai_working/analyze-{your-domain}

# Create basic files
touch README.md
touch prototype.py
touch notes.md
mkdir examples
mkdir tests
```

### Step 4: Implement Core Functionality

#### Template Code Structure

```python
#!/usr/bin/env python3
"""
Analyze {Your Domain}

Multi-agent analysis tool for {domain} insights and recommendations.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for amplihack imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.amplihack.core.config import load_config
from src.amplihack.agents.agent_manager import AgentManager
from src.amplihack.core.security import validate_path, sanitize_input

@dataclass
class AnalysisResult:
    """Structured result from analysis."""
    agent_name: str
    findings: List[Dict[str, Any]]
    metrics: Dict[str, float]
    recommendations: List[str]
    timestamp: datetime
    execution_time: float

class {YourDomain}Analyzer:
    """Main analysis tool implementing multi-agent coordination pattern."""

    def __init__(self, config: dict = None):
        """Initialize analyzer with configuration."""
        self.config = config or self._load_default_config()
        self.agent_manager = AgentManager()
        self.results: List[AnalysisResult] = []

    def analyze(self, target_path: str, options: dict = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of target using multiple agents.

        Args:
            target_path: Directory or file to analyze
            options: Additional analysis options (depth, format, etc.)

        Returns:
            Comprehensive analysis results with recommendations

        Example:
            >>> analyzer = {YourDomain}Analyzer()
            >>> result = analyzer.analyze("./src", {"depth": "deep"})
            >>> print(result["summary"]["score"])
        """
        start_time = datetime.now()

        # Validate and prepare target
        validated_path = self._validate_input(target_path)
        analysis_options = self._prepare_options(options or {})

        # Discover analyzable content
        content_map = self._discover_content(validated_path)

        if not content_map:
            return self._empty_result("No analyzable content found")

        # Execute parallel agent analysis
        agent_results = asyncio.run(self._execute_agents(content_map, analysis_options))

        # Aggregate and format results
        final_result = self._aggregate_results(agent_results, start_time)

        # Apply user preferences to output
        formatted_result = self._format_output(final_result, analysis_options)

        return formatted_result

    async def _execute_agents(self, content_map: Dict, options: Dict) -> List[AnalysisResult]:
        """Execute multiple specialized agents in parallel."""
        agents_to_run = self._select_agents(content_map, options)

        tasks = []
        for agent_name, agent_config in agents_to_run.items():
            task = self._run_agent(agent_name, content_map, agent_config)
            tasks.append(task)

        # Wait for all agents to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        valid_results = [r for r in results if isinstance(r, AnalysisResult)]

        return valid_results

    async def _run_agent(self, agent_name: str, content_map: Dict, config: Dict) -> AnalysisResult:
        """Run a single specialized agent."""
        start_time = datetime.now()

        try:
            # Invoke agent through agent manager
            agent_output = await self.agent_manager.invoke_agent(
                agent_name,
                content_map,
                config
            )

            # Parse agent output into structured result
            result = self._parse_agent_output(agent_name, agent_output)
            result.execution_time = (datetime.now() - start_time).total_seconds()

            return result

        except Exception as e:
            # Return error result for failed agents
            return AnalysisResult(
                agent_name=agent_name,
                findings=[{"error": str(e)}],
                metrics={"success": 0.0},
                recommendations=[f"Agent {agent_name} failed: {str(e)}"],
                timestamp=start_time,
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _validate_input(self, target_path: str) -> Path:
        """Validate input parameters and security constraints."""
        # Validate path safety
        clean_path = validate_path(target_path, allow_parent_access=False)

        # Ensure path exists and is readable
        if not clean_path.exists():
            raise ValueError(f"Target path does not exist: {target_path}")

        if not clean_path.is_dir() and not clean_path.is_file():
            raise ValueError(f"Target must be a file or directory: {target_path}")

        return clean_path

    def _discover_content(self, target_path: Path) -> Dict[str, List[Path]]:
        """Discover and categorize analyzable content."""
        content_map = {
            "python": [],
            "javascript": [],
            "typescript": [],
            "yaml": [],
            "json": [],
            "markdown": [],
            "other": []
        }

        # File extension mappings
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown"
        }

        if target_path.is_file():
            # Single file analysis
            ext = target_path.suffix.lower()
            category = ext_map.get(ext, "other")
            content_map[category].append(target_path)
        else:
            # Directory analysis
            for file_path in target_path.rglob("*"):
                if file_path.is_file() and not self._should_skip_file(file_path):
                    ext = file_path.suffix.lower()
                    category = ext_map.get(ext, "other")
                    content_map[category].append(file_path)

        # Filter out empty categories
        return {k: v for k, v in content_map.items() if v}

    def _select_agents(self, content_map: Dict, options: Dict) -> Dict[str, Dict]:
        """Select appropriate agents based on content and options."""
        available_agents = {
            "analyzer": {"priority": 1, "scope": "all"},
            "security": {"priority": 2, "scope": "code"},
            "optimizer": {"priority": 3, "scope": "code"},
            "patterns": {"priority": 4, "scope": "all"}
        }

        # Filter agents based on content type
        selected = {}
        for agent_name, agent_config in available_agents.items():
            if self._agent_applicable(agent_name, content_map, agent_config):
                selected[agent_name] = agent_config

        return selected

    def _aggregate_results(self, agent_results: List[AnalysisResult], start_time: datetime) -> Dict[str, Any]:
        """Aggregate results from multiple agents into unified report."""
        if not agent_results:
            return self._empty_result("No agent results available")

        # Aggregate metrics
        all_metrics = {}
        for result in agent_results:
            for metric, value in result.metrics.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append(value)

        # Calculate summary metrics
        summary_metrics = {
            metric: sum(values) / len(values)
            for metric, values in all_metrics.items()
        }

        # Collect all findings and recommendations
        all_findings = []
        all_recommendations = []

        for result in agent_results:
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)

        # Build comprehensive result
        return {
            "timestamp": start_time.isoformat(),
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "summary": {
                "agents_run": len(agent_results),
                "total_findings": len(all_findings),
                "metrics": summary_metrics
            },
            "findings": self._prioritize_findings(all_findings),
            "recommendations": self._prioritize_recommendations(all_recommendations),
            "agent_details": [
                {
                    "name": result.agent_name,
                    "findings_count": len(result.findings),
                    "execution_time": result.execution_time,
                    "metrics": result.metrics
                }
                for result in agent_results
            ]
        }

    def _format_output(self, result: Dict[str, Any], options: Dict) -> Dict[str, Any]:
        """Format output according to user preferences and options."""
        format_type = options.get("format", "text")

        if format_type == "json":
            return result
        elif format_type == "text":
            return self._format_text_output(result)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _format_text_output(self, result: Dict[str, Any]) -> str:
        """Format results as human-readable text."""
        lines = []
        lines.append(f"🔍 Analysis Results ({result['timestamp']})")
        lines.append("")

        # Summary
        summary = result["summary"]
        lines.append("📊 Summary:")
        lines.append(f"- Agents executed: {summary['agents_run']}")
        lines.append(f"- Total findings: {summary['total_findings']}")
        lines.append(f"- Analysis time: {result['execution_time']:.1f}s")
        lines.append("")

        # Top recommendations
        if result["recommendations"]:
            lines.append("📋 Top Recommendations:")
            for i, rec in enumerate(result["recommendations"][:5], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Metrics
        if summary.get("metrics"):
            lines.append("📈 Metrics:")
            for metric, value in summary["metrics"].items():
                lines.append(f"- {metric}: {value:.2f}")

        return "\n".join(lines)

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for the analyzer."""
        return {
            "max_file_size": 1024 * 1024,  # 1MB
            "timeout_per_agent": 60,  # seconds
            "skip_patterns": [".git", "__pycache__", "node_modules"],
            "analysis_depth": "deep"
        }

    def _empty_result(self, message: str) -> Dict[str, Any]:
        """Return empty result with message."""
        return {
            "timestamp": datetime.now().isoformat(),
            "execution_time": 0.0,
            "summary": {"message": message, "agents_run": 0, "total_findings": 0},
            "findings": [],
            "recommendations": [],
            "agent_details": []
        }

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Analyze {your domain} code for insights and recommendations')

    parser.add_argument('target', help='Directory or file to analyze')
    parser.add_argument('--format', help='Output format (text/json)', default='text')
    parser.add_argument('--depth', help='Analysis depth (shallow/deep)', default='deep')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Prepare options
    options = {
        "format": args.format,
        "depth": args.depth,
        "verbose": args.verbose
    }

    # Create and run analyzer
    analyzer = {YourDomain}Analyzer()
    result = analyzer.analyze(args.target, options)

    # Output results
    if args.output:
        output_path = Path(args.output)
        if args.format == "json":
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            with open(output_path, 'w') as f:
                f.write(result)
        print(f"Analysis saved to: {output_path}")
    else:
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(result)

if __name__ == '__main__':
    main()
```

### Step 5: Add Security Validation

Implement these security measures:

```python
import re
from pathlib import Path

def validate_tool_name(name: str) -> bool:
    """Validate tool name to prevent injection attacks."""
    if not re.match(r'^[a-z0-9-]+$', name):
        raise ValueError(f"Invalid tool name: {name}")
    return True

def validate_file_path(path: str, allowed_dirs: list = None) -> Path:
    """Validate file paths to prevent directory traversal."""
    clean_path = Path(path).resolve()

    # Prevent directory traversal
    if '..' in str(clean_path):
        raise ValueError(f"Directory traversal not allowed: {path}")

    # Restrict to allowed directories
    if allowed_dirs:
        if not any(str(clean_path).startswith(str(Path(d).resolve()))
                  for d in allowed_dirs):
            raise ValueError(f"Path not in allowed directories: {path}")

    return clean_path

def sanitize_output_content(content: str) -> str:
    """Sanitize output content to prevent injection."""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'"]
    for char in dangerous_chars:
        content = content.replace(char, f"&{ord(char)};")
    return content
```

### Step 6: Write Tests

Create comprehensive test coverage:

```python
# tests/test_analyze_{your_domain}.py
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ..analyze_{your_domain} import {YourDomain}Analyzer, AnalysisResult

class Test{YourDomain}Analyzer:
    """Test suite for {YourDomain}Analyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.analyzer = {YourDomain}Analyzer()

        # Create sample files
        (self.temp_dir / "sample.py").write_text("print('hello')")
        (self.temp_dir / "config.yaml").write_text("key: value")

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Unit Tests (60% of coverage)
    def test_validate_input_valid_path(self):
        """Test input validation with valid paths."""
        result = self.analyzer._validate_input(str(self.temp_dir))
        assert result == self.temp_dir.resolve()

    def test_validate_input_invalid_path(self):
        """Test input validation catches invalid inputs."""
        with pytest.raises(ValueError):
            self.analyzer._validate_input("/nonexistent/path")

    def test_discover_content_python_files(self):
        """Test content discovery finds Python files."""
        content_map = self.analyzer._discover_content(self.temp_dir)
        assert "python" in content_map
        assert len(content_map["python"]) == 1

    def test_security_validation_directory_traversal(self):
        """Test security constraints prevent directory traversal."""
        with pytest.raises(ValueError):
            self.analyzer._validate_input("../../../etc/passwd")

    def test_agent_selection_based_on_content(self):
        """Test agent selection adapts to content types."""
        content_map = {"python": [Path("test.py")]}
        agents = self.analyzer._select_agents(content_map, {})
        assert "analyzer" in agents
        assert "security" in agents

    # Integration Tests (30% of coverage)
    @patch('src.amplihack.agents.agent_manager.AgentManager')
    def test_agent_integration(self, mock_agent_manager):
        """Test integration with amplihack agents."""
        # Mock agent responses
        mock_agent_manager.return_value.invoke_agent.return_value = {
            "findings": [],
            "metrics": {"score": 8.5},
            "recommendations": ["Test recommendation"]
        }

        result = self.analyzer.analyze(str(self.temp_dir))
        assert "summary" in result
        assert result["summary"]["agents_run"] > 0

    def test_configuration_loading(self):
        """Test configuration system integration."""
        config = {"custom_setting": "test_value"}
        analyzer = {YourDomain}Analyzer(config)
        assert analyzer.config["custom_setting"] == "test_value"

    def test_output_formatting_json(self):
        """Test JSON output formatting."""
        mock_result = {
            "timestamp": "2023-01-01T00:00:00",
            "summary": {"agents_run": 1},
            "findings": [],
            "recommendations": []
        }

        formatted = self.analyzer._format_output(mock_result, {"format": "json"})
        assert isinstance(formatted, dict)
        assert "timestamp" in formatted

    def test_output_formatting_text(self):
        """Test text output formatting."""
        mock_result = {
            "timestamp": "2023-01-01T00:00:00",
            "execution_time": 1.5,
            "summary": {"agents_run": 1, "total_findings": 0},
            "findings": [],
            "recommendations": ["Test recommendation"]
        }

        formatted = self.analyzer._format_output(mock_result, {"format": "text"})
        assert isinstance(formatted, str)
        assert "Analysis Results" in formatted

    # End-to-End Tests (10% of coverage)
    def test_full_analysis_workflow(self):
        """Test complete user workflow from input to output."""
        # Create more comprehensive test directory
        (self.temp_dir / "src").mkdir()
        (self.temp_dir / "src" / "main.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
        """)

        (self.temp_dir / "tests").mkdir()
        (self.temp_dir / "tests" / "test_main.py").write_text("""
import unittest
from src.main import hello_world

class TestMain(unittest.TestCase):
    def test_hello_world(self):
        # This would test the function
        pass
        """)

        # Mock the agent manager to return realistic results
        with patch('src.amplihack.agents.agent_manager.AgentManager') as mock_manager:
            mock_manager.return_value.invoke_agent.return_value = {
                "findings": [
                    {"type": "info", "message": "Function found", "file": "main.py"}
                ],
                "metrics": {"complexity": 1.0, "coverage": 0.8},
                "recommendations": ["Add docstrings to functions"]
            }

            result = self.analyzer.analyze(str(self.temp_dir), {"format": "json"})

            # Verify complete result structure
            assert "timestamp" in result
            assert "summary" in result
            assert "findings" in result
            assert "recommendations" in result
            assert "agent_details" in result

            # Verify analysis actually ran
            assert result["summary"]["agents_run"] > 0
            assert len(result["recommendations"]) > 0

    def test_cli_integration(self):
        """Test command-line interface integration."""
        from ..analyze_{your_domain} import main

        # Test would involve subprocess or argument mocking
        # This ensures the CLI interface works end-to-end
        pass
```

### Step 7: Add Makefile Integration

```makefile
# Add to project Makefile
analyze-{your-domain}:
	@echo "Running {Your Domain} Analysis..."
	@python .claude/scenarios/analyze-{your-domain}/tool.py $(TARGET) $(OPTIONS)

.PHONY: analyze-{your-domain}
```

### Step 8: Graduate to Scenarios

When your tool meets graduation criteria:

```bash
# Move from ai_working to scenarios
mkdir .claude/scenarios/analyze-{your-domain}
cp -r .claude/ai_working/analyze-{your-domain}/* .claude/scenarios/analyze-{your-domain}/

# Rename and enhance files
mv prototype.py tool.py
# Complete documentation using templates
# Add full test suite
# Update Makefile
# Create HOW_TO_CREATE_YOUR_OWN.md
```

## Customization Points

### Common Variations

**Domain-Specific Analysis**: Adapt for specific code types

- Modify: `_discover_content()`, `_select_agents()`, file type mappings
- Examples: API analysis, database schema analysis, test coverage analysis

**Output Format Customization**: Different reporting styles

- Modify: `_format_output()`, add new format types
- Examples: HTML reports, CSV metrics, interactive dashboards

**Agent Configuration**: Different analysis approaches

- Modify: `_select_agents()`, agent priority and configuration
- Examples: Security-focused analysis, performance-only analysis

### Configuration Options

```python
# Typical configuration structure
DEFAULT_CONFIG = {
    'max_file_size': 1024 * 1024,  # 1MB
    'timeout_per_agent': 60,  # seconds
    'skip_patterns': ['.git', '__pycache__', 'node_modules'],
    'analysis_depth': 'deep',
    'parallel_agents': True,
    'output_detail': 'comprehensive'
}
```

### Extension Points

The tool can be extended by:

1. **Custom Agents**: Add domain-specific analysis agents
2. **Output Formats**: Add new export formats (PDF, HTML, etc.)
3. **Integration Hooks**: Connect with external tools and services

## Common Patterns

### Pattern 1: Multi-Agent Coordination

**When to use**: When analysis requires multiple specialized perspectives
**Implementation**: Async execution of specialized agents with result aggregation

### Pattern 2: Progressive Analysis

**When to use**: When analysis can be done in stages with increasing detail
**Implementation**: Shallow pass first, then deep analysis on interesting areas

### Pattern 3: Incremental Analysis

**When to use**: When analyzing large codebases or changes over time
**Implementation**: Cache previous results and analyze only changed components

## Best Practices

### Code Quality

- Follow amplihack's ruthless simplicity philosophy
- Implement comprehensive error handling for agent failures
- Use structured data formats for consistent results
- Provide clear, actionable recommendations

### User Experience

- Start with sensible defaults that work immediately
- Provide progress feedback for long-running analysis
- Include examples in all error messages
- Support both human-readable and machine-readable output

### Integration

- Respect user preferences for output verbosity and style
- Work seamlessly with existing amplihack agents
- Follow the standard workflow patterns
- Implement proper security validation

## Troubleshooting Creation Process

### Common Issues

**Issue**: Agents not being invoked correctly
**Solution**: Verify agent manager setup and agent name spellings, check agent availability

**Issue**: Analysis results inconsistent or incomplete
**Solution**: Add result validation, implement fallback for failed agents, improve error handling

**Issue**: Performance issues with large codebases
**Solution**: Implement file filtering, add progress tracking, consider incremental analysis

## Next Steps

After creating your tool:

1. **Test Extensively**: Use with real codebases of various sizes
2. **Gather Feedback**: Get input from other developers
3. **Monitor Performance**: Track analysis times and success rates
4. **Iterate Rapidly**: Improve based on real usage patterns
5. **Document Patterns**: Update this template with new insights

## Resources

- **Original Tool**: `.claude/scenarios/analyze-codebase/`
- **Template Files**: `.claude/scenarios/templates/`
- **Agent Documentation**: `.claude/agents/`
- **Agent Manager**: `src/amplihack/agents/agent_manager.py`
- **Philosophy Guide**: `.claude/context/PHILOSOPHY.md`

---

_Remember: Start simple, test with real code, iterate based on actual analysis needs. The best analysis tools provide insights that lead to immediate action._
