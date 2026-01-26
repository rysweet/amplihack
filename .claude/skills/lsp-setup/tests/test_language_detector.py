"""
Unit tests for language_detector.py (60% - Unit Tests)

Tests language detection from file extensions and project structure.
All tests should FAIL initially (TDD red phase).
"""

from pathlib import Path


class TestLanguageDetector:
    """Test suite for LanguageDetector class."""

    def test_detect_single_python_project(self, mock_project_root, sample_python_files):
        """Test detecting a Python-only project."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "python" in languages
        assert len(languages) == 1

    def test_detect_single_typescript_project(self, mock_project_root, sample_typescript_files):
        """Test detecting a TypeScript-only project."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "typescript" in languages
        assert len(languages) == 1

    def test_detect_mixed_language_project(self, mock_project_root, sample_mixed_language_files):
        """Test detecting a project with multiple languages."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "python" in languages
        assert "typescript" in languages
        assert "javascript" in languages
        assert "rust" in languages
        assert len(languages) == 4

    def test_detect_javascript_files(self, mock_project_root):
        """Test detecting JavaScript files."""
        from lsp_setup.language_detector import LanguageDetector

        # Create .js files
        (mock_project_root / "app.js").write_text("// JS code")
        (mock_project_root / "utils.js").write_text("// JS code")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "javascript" in languages

    def test_detect_rust_project_with_cargo_toml(self, mock_project_root):
        """Test detecting Rust project via Cargo.toml."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Cargo.toml
        (mock_project_root / "Cargo.toml").write_text("[package]\nname = 'test'")
        (mock_project_root / "src" / "main.rs").parent.mkdir(parents=True, exist_ok=True)
        (mock_project_root / "src" / "main.rs").write_text("fn main() {}")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "rust" in languages

    def test_detect_go_project_with_go_mod(self, mock_project_root):
        """Test detecting Go project via go.mod."""
        from lsp_setup.language_detector import LanguageDetector

        # Create go.mod
        (mock_project_root / "go.mod").write_text("module test\n\ngo 1.20")
        (mock_project_root / "main.go").write_text("package main")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "go" in languages

    def test_detect_java_project_with_maven(self, mock_project_root):
        """Test detecting Java project via pom.xml."""
        from lsp_setup.language_detector import LanguageDetector

        # Create pom.xml
        (mock_project_root / "pom.xml").write_text("<project></project>")
        (mock_project_root / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        (mock_project_root / "src" / "main" / "java" / "Main.java").write_text(
            "public class Main {}"
        )

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "java" in languages

    def test_detect_cpp_project(self, mock_project_root):
        """Test detecting C++ project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create C++ files
        (mock_project_root / "main.cpp").write_text("#include <iostream>")
        (mock_project_root / "utils.hpp").write_text("#ifndef UTILS_H")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "cpp" in languages

    def test_detect_ruby_project(self, mock_project_root):
        """Test detecting Ruby project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Ruby files
        (mock_project_root / "Gemfile").write_text("source 'https://rubygems.org'")
        (mock_project_root / "app.rb").write_text("puts 'Hello'")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "ruby" in languages

    def test_detect_php_project(self, mock_project_root):
        """Test detecting PHP project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create PHP files
        (mock_project_root / "index.php").write_text("<?php echo 'Hello'; ?>")
        (mock_project_root / "composer.json").write_text("{}")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "php" in languages

    def test_detect_csharp_project(self, mock_project_root):
        """Test detecting C# project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create C# files
        (mock_project_root / "Program.cs").write_text("using System;")
        (mock_project_root / "test.csproj").write_text("<Project></Project>")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "csharp" in languages

    def test_detect_kotlin_project(self, mock_project_root):
        """Test detecting Kotlin project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Kotlin files
        (mock_project_root / "Main.kt").write_text("fun main() {}")
        (mock_project_root / "build.gradle.kts").write_text("plugins {}")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "kotlin" in languages

    def test_detect_swift_project(self, mock_project_root):
        """Test detecting Swift project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Swift files
        (mock_project_root / "Package.swift").write_text("// swift-tools-version:5.5")
        (mock_project_root / "main.swift").write_text('print("Hello")')

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "swift" in languages

    def test_detect_scala_project(self, mock_project_root):
        """Test detecting Scala project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Scala files
        (mock_project_root / "build.sbt").write_text('name := "test"')
        (mock_project_root / "src" / "main" / "scala").mkdir(parents=True, exist_ok=True)
        (mock_project_root / "src" / "main" / "scala" / "Main.scala").write_text("object Main {}")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "scala" in languages

    def test_detect_lua_project(self, mock_project_root):
        """Test detecting Lua project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Lua files
        (mock_project_root / "init.lua").write_text("print('Hello')")
        (mock_project_root / "config.lua").write_text("return {}")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "lua" in languages

    def test_detect_elixir_project(self, mock_project_root):
        """Test detecting Elixir project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Elixir files
        (mock_project_root / "mix.exs").write_text("defmodule Test.MixProject do")
        (mock_project_root / "lib" / "test.ex").parent.mkdir(parents=True, exist_ok=True)
        (mock_project_root / "lib" / "test.ex").write_text("defmodule Test do")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "elixir" in languages

    def test_detect_haskell_project(self, mock_project_root):
        """Test detecting Haskell project."""
        from lsp_setup.language_detector import LanguageDetector

        # Create Haskell files
        (mock_project_root / "test.cabal").write_text("name: test")
        (mock_project_root / "Main.hs").write_text('main = putStrLn "Hello"')

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert "haskell" in languages

    def test_ignore_common_directories(self, mock_project_root):
        """Test that common directories are ignored (node_modules, .git, etc.)."""
        from lsp_setup.language_detector import LanguageDetector

        # Create files in directories that should be ignored
        ignored_dirs = ["node_modules", ".git", "venv", "__pycache__", "build"]

        for dir_name in ignored_dirs:
            dir_path = mock_project_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / "test.py").write_text("# Should be ignored")

        # Create a valid Python file in root
        (mock_project_root / "main.py").write_text("# Valid Python")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        # Should only detect the root main.py, not files in ignored dirs
        assert "python" in languages

    def test_empty_project_returns_empty_list(self, mock_project_root):
        """Test that an empty project returns no languages."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert len(languages) == 0

    def test_language_confidence_scores(self, mock_project_root, sample_mixed_language_files):
        """Test that languages are sorted by confidence (file count)."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages_with_scores = detector.detect_languages_with_confidence()

        # All languages should have equal file counts (2 each)
        assert len(languages_with_scores) == 4
        for lang, score in languages_with_scores.items():
            assert score == 2

    def test_get_file_extensions_for_language(self):
        """Test getting file extensions for a specific language."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(Path("/tmp"))

        python_exts = detector.get_extensions_for_language("python")
        assert ".py" in python_exts

        ts_exts = detector.get_extensions_for_language("typescript")
        assert ".ts" in ts_exts
        assert ".tsx" in ts_exts

    def test_is_language_file(self, mock_project_root):
        """Test checking if a file belongs to a specific language."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)

        python_file = mock_project_root / "test.py"
        assert detector.is_language_file(python_file, "python")

        ts_file = mock_project_root / "test.ts"
        assert detector.is_language_file(ts_file, "typescript")

        assert not detector.is_language_file(python_file, "rust")

    def test_detect_with_max_languages_limit(self, mock_project_root, sample_mixed_language_files):
        """Test limiting the number of detected languages."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root, max_languages=2)
        languages = detector.detect_languages()

        assert len(languages) <= 2

    def test_detect_respects_gitignore(self, mock_project_root):
        """Test that detection respects .gitignore patterns."""
        from lsp_setup.language_detector import LanguageDetector

        # Create .gitignore
        (mock_project_root / ".gitignore").write_text("ignored/\n*.tmp.py")

        # Create ignored files
        (mock_project_root / "ignored").mkdir()
        (mock_project_root / "ignored" / "test.py").write_text("# Ignored")
        (mock_project_root / "test.tmp.py").write_text("# Ignored")

        # Create valid file
        (mock_project_root / "main.py").write_text("# Valid")

        detector = LanguageDetector(mock_project_root)
        languages_with_scores = detector.detect_languages_with_confidence()

        # Should only count main.py
        assert languages_with_scores.get("python", 0) == 1
