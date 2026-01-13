"""Pytest configuration and shared fixtures for dynamic-debugger tests.

Following testing pyramid:
- 60% Unit tests
- 30% Integration tests
- 10% E2E tests
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def python_project(temp_project_dir):
    """Create a minimal Python project structure."""
    # Create manifest files
    (temp_project_dir / "requirements.txt").write_text("pytest>=7.0.0\nrequests>=2.28.0\n")
    (temp_project_dir / "pyproject.toml").write_text("""
[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"
""")

    # Create Python files
    src_dir = temp_project_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def main():\n    print('Hello World')\n")
    (src_dir / "utils.py").write_text("def helper():\n    return 42\n")

    # Create test files
    tests_dir = temp_project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_main():\n    assert True\n")

    return temp_project_dir


@pytest.fixture
def javascript_project(temp_project_dir):
    """Create a minimal JavaScript/Node.js project structure."""
    # Create package.json
    package_json = {
        "name": "test-project",
        "version": "1.0.0",
        "main": "index.js",
        "scripts": {"test": "jest"},
        "dependencies": {"express": "^4.18.0"},
    }
    (temp_project_dir / "package.json").write_text(json.dumps(package_json, indent=2))

    # Create JavaScript files
    (temp_project_dir / "index.js").write_text("console.log('Hello World');\n")
    (temp_project_dir / "utils.js").write_text("module.exports = { helper: () => 42 };\n")

    # Create test files
    tests_dir = temp_project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "app.test.js").write_text("test('works', () => { expect(true).toBe(true); });\n")

    return temp_project_dir


@pytest.fixture
def go_project(temp_project_dir):
    """Create a minimal Go project structure."""
    # Create go.mod
    (temp_project_dir / "go.mod").write_text("""module example.com/test

go 1.21

require (
    github.com/stretchr/testify v1.8.0
)
""")

    # Create Go files
    (temp_project_dir / "main.go").write_text("""package main

import "fmt"

func main() {
    fmt.Println("Hello World")
}
""")
    (temp_project_dir / "utils.go").write_text("""package main

func Helper() int {
    return 42
}
""")

    # Create test files
    (temp_project_dir / "main_test.go").write_text("""package main

import "testing"

func TestHelper(t *testing.T) {
    if Helper() != 42 {
        t.Error("Expected 42")
    }
}
""")

    return temp_project_dir


@pytest.fixture
def rust_project(temp_project_dir):
    """Create a minimal Rust project structure."""
    # Create Cargo.toml
    (temp_project_dir / "Cargo.toml").write_text("""[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
""")

    # Create src directory
    src_dir = temp_project_dir / "src"
    src_dir.mkdir()

    # Create Rust files
    (src_dir / "main.rs").write_text("""fn main() {
    println!("Hello World");
}

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4);
    }
}
""")

    return temp_project_dir


@pytest.fixture
def cpp_project(temp_project_dir):
    """Create a minimal C++ project structure."""
    # Create CMakeLists.txt
    (temp_project_dir / "CMakeLists.txt").write_text("""cmake_minimum_required(VERSION 3.10)
project(TestProject)

set(CMAKE_CXX_STANDARD 17)

add_executable(main main.cpp)
""")

    # Create C++ files
    (temp_project_dir / "main.cpp").write_text("""#include <iostream>

int main() {
    std::cout << "Hello World" << std::endl;
    return 0;
}
""")
    (temp_project_dir / "utils.cpp").write_text("""int helper() {
    return 42;
}
""")
    (temp_project_dir / "utils.h").write_text("""#ifndef UTILS_H
#define UTILS_H

int helper();

#endif
""")

    return temp_project_dir


@pytest.fixture
def java_project(temp_project_dir):
    """Create a minimal Java project structure."""
    # Create pom.xml (Maven)
    (temp_project_dir / "pom.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
    </properties>
</project>
""")

    # Create Java directory structure
    src_main = temp_project_dir / "src" / "main" / "java" / "com" / "example"
    src_main.mkdir(parents=True)

    # Create Java files
    (src_main / "Main.java").write_text("""package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
""")

    # Create test directory
    src_test = temp_project_dir / "src" / "test" / "java" / "com" / "example"
    src_test.mkdir(parents=True)
    (src_test / "MainTest.java").write_text("""package com.example;

import org.junit.Test;
import static org.junit.Assert.*;

public class MainTest {
    @Test
    public void testMain() {
        assertTrue(true);
    }
}
""")

    return temp_project_dir


@pytest.fixture
def multi_language_project(temp_project_dir):
    """Create a project with multiple languages (Python dominant)."""
    # Python files (majority)
    for i in range(5):
        (temp_project_dir / f"script_{i}.py").write_text(f"# Python script {i}\n")

    # JavaScript files (minority)
    for i in range(2):
        (temp_project_dir / f"script_{i}.js").write_text(f"// JavaScript script {i}\n")

    # Add Python manifest
    (temp_project_dir / "requirements.txt").write_text("requests>=2.28.0\n")

    return temp_project_dir


@pytest.fixture
def empty_project(temp_project_dir):
    """Create an empty project directory."""
    return temp_project_dir


@pytest.fixture
def sample_dap_config():
    """Sample DAP configuration for testing."""
    return {
        "name": "Python: Debug Current File",
        "type": "python",
        "request": "launch",
        "program": "${project_dir}/main.py",
        "console": "integratedTerminal",
        "cwd": "${project_dir}",
        "pythonPath": "python3",
    }


@pytest.fixture
def mock_pid_file(tmp_path):
    """Create a mock PID file for testing."""
    pid_file = tmp_path / ".dap_mcp.pid"
    pid_file.write_text("12345\n")
    return pid_file


@pytest.fixture
def skill_dir():
    """Return the skill directory path."""
    return Path(__file__).parent.parent


@pytest.fixture
def configs_dir(skill_dir):
    """Return the configs directory path."""
    return skill_dir / "configs"


@pytest.fixture
def scripts_dir(skill_dir):
    """Return the scripts directory path."""
    return skill_dir / "scripts"
