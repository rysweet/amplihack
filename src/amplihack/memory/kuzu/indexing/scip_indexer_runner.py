"""SCIP Indexer Runner - Executes language-specific SCIP indexers to create index.scip files.

This module runs the appropriate SCIP indexer tool for each language:
- Python: scip-python
- TypeScript/JavaScript: scip-typescript
- Go: scip-go
- Rust: rust-analyzer scip
- C#: scip-dotnet
- C++: scip-clang
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ScipIndexResult:
    """Result of running a SCIP indexer."""

    language: str
    success: bool
    index_path: Path | None
    index_size_bytes: int
    duration_seconds: float
    error_message: str | None = None


class ScipIndexerRunner:
    """Runs SCIP indexers to create index.scip files for code intelligence."""

    def __init__(self, quiet: bool = False):
        """Initialize runner.

        Args:
            quiet: If True, suppress progress messages
        """
        self.quiet = quiet

    def _log(self, message: str) -> None:
        """Log message if not in quiet mode."""
        if not self.quiet:
            print(message)

    def _run_indexer(
        self,
        command: list[str],
        cwd: Path,
        language: str,
        timeout: int = 600,
    ) -> ScipIndexResult:
        """Run a SCIP indexer command.

        Args:
            command: Command to run (e.g., ["scip-python", "index"])
            cwd: Working directory to run from
            language: Language being indexed
            timeout: Timeout in seconds

        Returns:
            ScipIndexResult with outcome
        """
        import time

        start_time = time.time()
        index_path = cwd / "index.scip"

        # Remove existing index if present
        if index_path.exists():
            index_path.unlink()

        try:
            self._log(f"  🔧 Running {' '.join(command)}...")

            # Ensure PATH includes Go bin, dotnet tools, and local bin (for built scip-dotnet)
            env = os.environ.copy()
            go_bin = Path.home() / "go" / "bin"
            dotnet_tools = Path.home() / ".dotnet" / "tools"
            local_bin = Path.home() / ".local" / "bin"
            env["PATH"] = f"{local_bin}:{go_bin}:{dotnet_tools}:{env.get('PATH', '')}"

            result = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            duration = time.time() - start_time

            # Check if index.scip was created
            if index_path.exists():
                size = index_path.stat().st_size
                self._log(f"  ✅ Created index.scip ({size:,} bytes)")
                return ScipIndexResult(
                    language=language,
                    success=True,
                    index_path=index_path,
                    index_size_bytes=size,
                    duration_seconds=duration,
                )
            error_msg = f"index.scip not created. Stderr: {result.stderr[:500]}"
            logger.error(error_msg)
            self._log("  ❌ Failed: index.scip not created")
            return ScipIndexResult(
                language=language,
                success=False,
                index_path=None,
                index_size_bytes=0,
                duration_seconds=duration,
                error_message=error_msg,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ScipIndexResult(
                language=language,
                success=False,
                index_path=None,
                index_size_bytes=0,
                duration_seconds=duration,
                error_message=f"Indexer timeout after {timeout}s",
            )
        except FileNotFoundError as e:
            duration = time.time() - start_time
            return ScipIndexResult(
                language=language,
                success=False,
                index_path=None,
                index_size_bytes=0,
                duration_seconds=duration,
                error_message=f"Indexer command not found: {e}",
            )
        except Exception as e:
            duration = time.time() - start_time
            return ScipIndexResult(
                language=language,
                success=False,
                index_path=None,
                index_size_bytes=0,
                duration_seconds=duration,
                error_message=str(e),
            )

    def run_python_indexer(self, codebase_path: Path) -> ScipIndexResult:
        """Run scip-python indexer.

        Args:
            codebase_path: Path to Python codebase

        Returns:
            ScipIndexResult
        """
        return self._run_indexer(
            ["scip-python", "index"],
            cwd=codebase_path,
            language="python",
            timeout=600,
        )

    def run_typescript_indexer(
        self, codebase_path: Path, is_javascript: bool = False
    ) -> ScipIndexResult:
        """Run scip-typescript indexer.

        Args:
            codebase_path: Path to TypeScript/JavaScript codebase
            is_javascript: If True, create minimal tsconfig.json for pure JS projects

        Returns:
            ScipIndexResult
        """
        # For JavaScript projects, ensure tsconfig.json exists
        tsconfig_path = codebase_path / "tsconfig.json"
        jsconfig_path = codebase_path / "jsconfig.json"
        created_config = False

        if is_javascript and not tsconfig_path.exists():
            # Check if jsconfig.json exists and rename it
            if jsconfig_path.exists():
                jsconfig_path.rename(tsconfig_path)
                created_config = True
                self._log("  📝 Renamed jsconfig.json → tsconfig.json")
            else:
                # Create minimal tsconfig.json for JavaScript indexing
                minimal_config = """{
  "compilerOptions": {
    "target": "es2020",
    "module": "commonjs",
    "allowJs": true,
    "checkJs": false,
    "skipLibCheck": true
  },
  "include": ["**/*.js", "**/*.jsx"],
  "exclude": ["node_modules", "dist", "build", "coverage"]
}
"""
                tsconfig_path.write_text(minimal_config)
                created_config = True
                self._log("  📝 Created minimal tsconfig.json for JavaScript indexing")

        result = self._run_indexer(
            ["scip-typescript", "index"],
            cwd=codebase_path,
            language="javascript" if is_javascript else "typescript",
            timeout=600,
        )

        # Clean up auto-created config if indexing failed
        if created_config and not result.success:
            try:
                tsconfig_path.unlink()
            except Exception:
                pass

        return result

    def run_go_indexer(self, codebase_path: Path) -> ScipIndexResult:
        """Run scip-go indexer.

        Args:
            codebase_path: Path to Go codebase

        Returns:
            ScipIndexResult
        """
        return self._run_indexer(
            ["scip-go"],
            cwd=codebase_path,
            language="go",
            timeout=600,
        )

    def run_rust_indexer(self, codebase_path: Path) -> ScipIndexResult:
        """Run rust-analyzer scip command.

        Args:
            codebase_path: Path to Rust codebase

        Returns:
            ScipIndexResult
        """
        return self._run_indexer(
            ["rust-analyzer", "scip", str(codebase_path)],
            cwd=codebase_path,
            language="rust",
            timeout=600,
        )

    def run_csharp_indexer(self, codebase_path: Path) -> ScipIndexResult:
        """Run scip-dotnet indexer.

        Args:
            codebase_path: Path to C# codebase

        Returns:
            ScipIndexResult
        """
        return self._run_indexer(
            ["scip-dotnet", "index"],
            cwd=codebase_path,
            language="csharp",
            timeout=600,
        )

    def run_cpp_indexer(self, codebase_path: Path) -> ScipIndexResult:
        """Run scip-clang indexer.

        Args:
            codebase_path: Path to C++ codebase

        Returns:
            ScipIndexResult
        """
        # scip-clang reads compile_commands.json automatically
        return self._run_indexer(
            ["scip-clang"],
            cwd=codebase_path,
            language="cpp",
            timeout=600,
        )

    def run_indexer_for_language(
        self,
        language: str,
        codebase_path: Path,
    ) -> ScipIndexResult:
        """Run the appropriate SCIP indexer for the given language.

        Args:
            language: Language name (python, typescript, javascript, go, rust, csharp, cpp)
            codebase_path: Path to codebase

        Returns:
            ScipIndexResult with outcome
        """
        language_lower = language.lower()

        if language_lower == "python":
            return self.run_python_indexer(codebase_path)
        if language_lower == "typescript":
            return self.run_typescript_indexer(codebase_path, is_javascript=False)
        if language_lower == "javascript":
            return self.run_typescript_indexer(codebase_path, is_javascript=True)
        if language_lower == "go":
            return self.run_go_indexer(codebase_path)
        if language_lower == "rust":
            return self.run_rust_indexer(codebase_path)
        if language_lower == "csharp":
            return self.run_csharp_indexer(codebase_path)
        if language_lower in ("cpp", "c++", "c"):
            return self.run_cpp_indexer(codebase_path)
        return ScipIndexResult(
            language=language,
            success=False,
            index_path=None,
            index_size_bytes=0,
            duration_seconds=0.0,
            error_message=f"Unknown language: {language}",
        )
