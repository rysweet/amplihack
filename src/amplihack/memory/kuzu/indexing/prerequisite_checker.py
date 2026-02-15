"""Prerequisite checking for Blarify indexing tools.

Validates that required tools and configurations are available before indexing.
"""

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class LanguageStatus:
    """Status of a language's prerequisites."""

    language: str
    available: bool
    error_message: str | None
    missing_tools: list[str]
    install_instructions: str | None = None  # How to install missing tools


@dataclass
class PrerequisiteResult:
    """Result of prerequisite checking for all languages."""

    can_proceed: bool
    available_languages: list[str]
    unavailable_languages: list[str]
    partial_success: bool
    language_statuses: dict[str, LanguageStatus] | None = None

    def __post_init__(self):
        if self.language_statuses is None:
            self.language_statuses = {}

    def generate_report(self) -> str:
        """Generate human-readable report of prerequisite status."""
        lines = []
        lines.append("Prerequisite Check Report")
        lines.append("=" * 40)

        if self.available_languages:
            lines.append(f"\nAvailable Languages ({len(self.available_languages)}):")
            for lang in self.available_languages:
                lines.append(f"  ✓ {lang}")

        if self.unavailable_languages:
            lines.append(f"\nUnavailable Languages ({len(self.unavailable_languages)}):")
            for lang in self.unavailable_languages:
                if self.language_statuses:
                    status = self.language_statuses.get(lang)
                else:
                    status = None
                if status and status.error_message:
                    lines.append(f"  ✗ {lang}: {status.error_message}")
                    if status.install_instructions:
                        lines.append(f"      Install: {status.install_instructions}")
                else:
                    lines.append(f"  ✗ {lang}")

        lines.append(f"\nCan Proceed: {self.can_proceed}")
        if self.partial_success:
            lines.append("Note: Partial success - some languages unavailable")

        return "\n".join(lines)


class PrerequisiteChecker:
    """Check prerequisites for Blarify indexing tools."""

    # Supported dotnet versions (6 LTS, 7, 8 LTS, 9, 10)
    SUPPORTED_DOTNET_VERSIONS = ["6", "7", "8", "9", "10"]

    def check_language(self, language: str, indexer_type: str | None = None) -> LanguageStatus:
        """Check prerequisites for a specific language.

        Args:
            language: Language to check (python, javascript, typescript, csharp, go, java, php, ruby)
            indexer_type: Optional indexer type (e.g., "jedi" for Python)

        Returns:
            LanguageStatus with availability and error information
        """
        if language == "python":
            return self._check_python(indexer_type)
        if language == "javascript":
            return self._check_javascript()
        if language == "typescript":
            return self._check_typescript()
        if language == "csharp":
            return self._check_csharp()
        if language == "go":
            return self._check_go()
        if language == "java":
            return self._check_java()
        if language == "php":
            return self._check_php()
        if language == "ruby":
            return self._check_ruby()
        return LanguageStatus(
            language=language,
            available=False,
            error_message=f"Unknown language: {language}",
            missing_tools=[],
        )

    def _check_python(self, indexer_type: str | None = None) -> LanguageStatus:
        """Check Python prerequisites with graceful degradation.

        Supports two indexers:
        - scip-python (preferred, faster)
        - jedi-language-server (fallback, always works if Python installed)

        Returns available if EITHER indexer is present.
        """
        if indexer_type == "jedi":
            # Explicitly requested Jedi - check Python binary only
            python_bin = shutil.which("python") or shutil.which("python3")
            if not python_bin:
                return LanguageStatus(
                    language="python",
                    available=False,
                    error_message="Python binary not found in PATH",
                    missing_tools=["python"],
                    install_instructions="Python is required (install from python.org or your package manager)",
                )

            # Config files are now included in the wheel package, so just check Python binary
            return LanguageStatus(
                language="python",
                available=True,
                error_message=None,
                missing_tools=[],
            )

        # Auto-detect: Check for EITHER indexer (graceful degradation)
        scip_python = shutil.which("scip-python")
        python_bin = shutil.which("python") or shutil.which("python3")

        if scip_python:
            # scip-python available - preferred indexer
            return LanguageStatus(
                language="python",
                available=True,
                error_message=None,
                missing_tools=[],
            )
        if python_bin:
            # Fallback to Jedi LSP - always works if Python is installed
            return LanguageStatus(
                language="python",
                available=True,
                error_message=None,
                missing_tools=[],
                install_instructions="Using Jedi LSP fallback (pip install jedi-language-server for optimal experience)",
            )
        # Neither indexer available
        return LanguageStatus(
            language="python",
            available=False,
            error_message="No Python indexer available (need scip-python or Python binary for Jedi)",
            missing_tools=["scip-python", "python"],
            install_instructions="pip install scip-python (preferred) OR pip install jedi-language-server (fallback)",
        )

    def _check_javascript(self) -> LanguageStatus:
        """Check JavaScript prerequisites."""
        node_bin = shutil.which("node")
        if not node_bin:
            return LanguageStatus(
                language="javascript",
                available=False,
                error_message="Node.js binary not found in PATH",
                missing_tools=["node"],
                install_instructions="npm install -g typescript-language-server (requires Node.js)",
            )

        return LanguageStatus(
            language="javascript",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def _check_typescript(self) -> LanguageStatus:
        """Check TypeScript prerequisites."""
        node_bin = shutil.which("node")
        if not node_bin:
            return LanguageStatus(
                language="typescript",
                available=False,
                error_message="Node.js binary not found in PATH",
                missing_tools=["node"],
                install_instructions="npm install -g typescript-language-server (requires Node.js)",
            )

        # Check for runtime_dependencies.json - config now included in package
        # This check is kept for legacy compatibility but should not fail
        # since runtime_dependencies.json is now in the wheel package

        return LanguageStatus(
            language="typescript",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def _check_csharp(self) -> LanguageStatus:
        """Check C# prerequisites."""
        # Check for dotnet binary
        dotnet_bin = shutil.which("dotnet")
        if not dotnet_bin:
            return LanguageStatus(
                language="csharp",
                available=False,
                error_message="dotnet binary not found in PATH",
                missing_tools=["dotnet"],
                install_instructions="Install .NET SDK from https://dotnet.microsoft.com/download (versions 6-10 supported)",
            )

        # Check dotnet version
        try:
            result = subprocess.run(
                ["dotnet", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                major_version = version.split(".")[0]

                # Check if version is supported
                if major_version not in self.SUPPORTED_DOTNET_VERSIONS:
                    return LanguageStatus(
                        language="csharp",
                        available=False,
                        error_message=f"dotnet version {version} is not supported (supported: 6-10)",
                        missing_tools=["dotnet"],
                        install_instructions=f"Install .NET SDK 6, 7, 8, 9, or 10 from https://dotnet.microsoft.com/download (current: {version})",
                    )

                return LanguageStatus(
                    language="csharp",
                    available=True,
                    error_message=None,
                    missing_tools=[],
                )
            return LanguageStatus(
                language="csharp",
                available=False,
                error_message="Failed to check dotnet version",
                missing_tools=["dotnet"],
                install_instructions="Ensure .NET SDK is properly installed from https://dotnet.microsoft.com/download",
            )

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return LanguageStatus(
                language="csharp",
                available=False,
                error_message=f"Error checking dotnet: {e}",
                missing_tools=["dotnet"],
                install_instructions="Install .NET SDK from https://dotnet.microsoft.com/download",
            )

    def _check_go(self) -> LanguageStatus:
        """Check Go prerequisites."""
        go_bin = shutil.which("go")
        if not go_bin:
            return LanguageStatus(
                language="go",
                available=False,
                error_message="Go binary not found in PATH",
                missing_tools=["go"],
                install_instructions="Install Go from https://golang.org/dl/ or via package manager (apt install golang-go)",
            )

        return LanguageStatus(
            language="go",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def _check_java(self) -> LanguageStatus:
        """Check Java prerequisites."""
        java_bin = shutil.which("java")
        if not java_bin:
            return LanguageStatus(
                language="java",
                available=False,
                error_message="Java binary not found in PATH",
                missing_tools=["java"],
                install_instructions="Install JDK from https://adoptium.net/ or via package manager (apt install default-jdk)",
            )

        return LanguageStatus(
            language="java",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def _check_php(self) -> LanguageStatus:
        """Check PHP prerequisites."""
        php_bin = shutil.which("php")
        if not php_bin:
            return LanguageStatus(
                language="php",
                available=False,
                error_message="PHP binary not found in PATH",
                missing_tools=["php"],
                install_instructions="Install PHP from https://www.php.net/ or via package manager (apt install php-cli)",
            )

        return LanguageStatus(
            language="php",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def _check_ruby(self) -> LanguageStatus:
        """Check Ruby prerequisites."""
        ruby_bin = shutil.which("ruby")
        if not ruby_bin:
            return LanguageStatus(
                language="ruby",
                available=False,
                error_message="Ruby binary not found in PATH",
                missing_tools=["ruby"],
                install_instructions="Install Ruby from https://www.ruby-lang.org/ or via package manager (apt install ruby-full)",
            )

        return LanguageStatus(
            language="ruby",
            available=True,
            error_message=None,
            missing_tools=[],
        )

    def check_all(self, languages: list[str]) -> PrerequisiteResult:
        """Check prerequisites for all specified languages.

        Args:
            languages: List of language names to check

        Returns:
            PrerequisiteResult with overall status
        """
        available = []
        unavailable = []
        statuses = {}

        for language in languages:
            status = self.check_language(language)
            statuses[language] = status

            if status.available:
                available.append(language)
            else:
                unavailable.append(language)

        can_proceed = len(available) > 0
        partial_success = can_proceed and len(unavailable) > 0

        return PrerequisiteResult(
            can_proceed=can_proceed,
            available_languages=available,
            unavailable_languages=unavailable,
            partial_success=partial_success,
            language_statuses=statuses,
        )
