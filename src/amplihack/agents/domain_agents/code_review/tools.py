"""Code review domain tools. Pure functions for analyzing code quality, security, and style."""

from __future__ import annotations

import re
from typing import Any


def analyze_code(code: str, language: str = "python") -> dict[str, Any]:
    """Parse and analyze code structure."""
    if not code or not code.strip():
        return {
            "line_count": 0,
            "function_count": 0,
            "class_count": 0,
            "import_count": 0,
            "comment_ratio": 0.0,
            "complexity_indicators": {},
        }

    lines = code.strip().split("\n")
    total = len(lines)

    if language == "python":
        func_pattern, class_pattern = r"^\s*def\s+\w+", r"^\s*class\s+\w+"
        import_pattern, comment_pattern = r"^\s*(import|from)\s+", r"^\s*#"
    else:
        func_pattern, class_pattern = r"(def |function |fn |func )", r"class\s+\w+"
        import_pattern, comment_pattern = r"(import|require|use)", r"^\s*(#|//)"

    function_count = len(re.findall(func_pattern, code, re.MULTILINE))
    class_count = len(re.findall(class_pattern, code, re.MULTILINE))
    import_count = len(re.findall(import_pattern, code, re.MULTILINE))
    comment_lines = len([ln for ln in lines if re.match(comment_pattern, ln)])
    comment_ratio = comment_lines / total if total > 0 else 0.0

    max_indent, branch_count = 0, 0
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            max_indent = max(max_indent, len(line) - len(stripped))
        if re.match(r"\s*(if|elif|else|for|while|try|except|switch|case)\b", line):
            branch_count += 1

    return {
        "line_count": total,
        "function_count": function_count,
        "class_count": class_count,
        "import_count": import_count,
        "comment_ratio": round(comment_ratio, 3),
        "complexity_indicators": {
            "max_nesting_depth": max_indent // 4,
            "branch_count": branch_count,
            "avg_function_length": total // max(function_count, 1),
        },
    }


def check_style(code: str, language: str = "python") -> list[dict[str, Any]]:
    """Check code for style violations."""
    issues: list[dict[str, Any]] = []
    if not code or not code.strip():
        return issues
    lines = code.strip().split("\n")
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append(
                {
                    "line": i,
                    "type": "line_too_long",
                    "severity": "warning",
                    "message": f"Line is {len(line)} characters (max 120)",
                }
            )
        if line != line.rstrip():
            issues.append(
                {
                    "line": i,
                    "type": "trailing_whitespace",
                    "severity": "info",
                    "message": "Trailing whitespace",
                }
            )
    if language == "python":
        for func_name in re.findall(r"def\s+([a-z]+[A-Z]\w*)", code):
            issues.append(
                {
                    "line": 0,
                    "type": "naming_convention",
                    "severity": "warning",
                    "message": f"Function '{func_name}' uses camelCase instead of snake_case",
                }
            )
        if re.findall(r"except\s*:", code):
            issues.append(
                {
                    "line": 0,
                    "type": "bare_except",
                    "severity": "error",
                    "message": "Found bare except clause(s)",
                }
            )
    return issues


def detect_security_issues(code: str, language: str = "python") -> list[dict[str, Any]]:
    """Scan code for security vulnerabilities."""
    issues: list[dict[str, Any]] = []
    if not code or not code.strip():
        return issues
    sql_patterns = [
        (r"execute\s*\(\s*[\"'].*%s", "SQL injection via string formatting"),
        (r"execute\s*\(\s*f[\"']", "SQL injection via f-string"),
        (r"execute\s*\(\s*[\"'].*\+", "SQL injection via concatenation"),
        (r"cursor\.execute\s*\(\s*[\"'].*\.format\(", "SQL injection via .format()"),
    ]
    for pattern, msg in sql_patterns:
        if re.search(pattern, code):
            issues.append(
                {
                    "type": "sql_injection",
                    "severity": "critical",
                    "message": msg,
                    "recommendation": "Use parameterized queries",
                }
            )
    secret_patterns = [
        (r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']+[\"']", "Hardcoded secret"),
        (r"(AWS_SECRET|PRIVATE_KEY)\s*=\s*[\"']", "Hardcoded cloud credential"),
    ]
    for pattern, msg in secret_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(
                {
                    "type": "hardcoded_secret",
                    "severity": "critical",
                    "message": msg,
                    "recommendation": "Use environment variables",
                }
            )
    if re.search(r"\beval\s*\(", code) or re.search(r"\bexec\s*\(", code):
        issues.append(
            {
                "type": "dangerous_function",
                "severity": "high",
                "message": "Use of eval() or exec()",
                "recommendation": "Avoid eval/exec",
            }
        )
    if re.search(r"os\.system\s*\(", code) or re.search(
        r"subprocess\.\w+\(.*shell\s*=\s*True", code
    ):
        issues.append(
            {
                "type": "command_injection",
                "severity": "high",
                "message": "Potential OS command injection",
                "recommendation": "Use subprocess with shell=False",
            }
        )
    return issues


def suggest_improvements(code: str, language: str = "python") -> list[dict[str, Any]]:
    """Suggest code improvements."""
    suggestions: list[dict[str, Any]] = []
    if not code or not code.strip():
        return suggestions
    lines = code.strip().split("\n")
    if language == "python":
        func_defs = [(i, line) for i, line in enumerate(lines) if re.match(r"\s*def\s+", line)]
        for i, line in func_defs:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    func_name = re.search(r"def\s+(\w+)", line)
                    if func_name:
                        suggestions.append(
                            {
                                "type": "missing_docstring",
                                "severity": "info",
                                "message": f"Function '{func_name.group(1)}' lacks a docstring",
                                "line": i + 1,
                            }
                        )
    analysis = analyze_code(code, language)
    if analysis["complexity_indicators"].get("avg_function_length", 0) > 30:
        suggestions.append(
            {
                "type": "large_functions",
                "severity": "warning",
                "message": "Average function length exceeds 30 lines",
            }
        )
    if analysis["complexity_indicators"].get("max_nesting_depth", 0) > 4:
        suggestions.append(
            {
                "type": "deep_nesting",
                "severity": "warning",
                "message": "Maximum nesting depth exceeds 4",
            }
        )
    return suggestions
