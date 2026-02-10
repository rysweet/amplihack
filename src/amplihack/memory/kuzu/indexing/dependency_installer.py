"""Automatic dependency installer for blarify indexing tools.

Auto-installs missing Python and Node.js dependencies at CLI startup.
For system dependencies (dotnet, go, java, php, ruby), shows clear install instructions.
"""

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    """Result of dependency installation attempt."""

    tool: str
    success: bool
    already_installed: bool
    error_message: str | None = None


class DependencyInstaller:
    """Auto-installs missing dependencies for blarify indexing."""

    def __init__(self, quiet: bool = False):
        """Initialize installer.

        Args:
            quiet: If True, suppress progress messages (for tests)
        """
        self.quiet = quiet

    def _log(self, message: str) -> None:
        """Log message if not in quiet mode."""
        if not self.quiet:
            print(message, file=sys.stderr)

    def _run_command(self, cmd: list[str], description: str) -> bool:
        """Run installation command with error handling.

        Args:
            cmd: Command to run
            description: Human-readable description for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            self._log(f"🔧 Installing: {description}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False,
            )

            if result.returncode == 0:
                self._log(f"✅ Installed {description}")
                return True

            logger.error(f"Failed to install {description}: {result.stderr}")
            self._log(f"❌ Failed to install {description}")
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout installing {description}")
            self._log(f"❌ Timeout installing {description}")
            return False
        except Exception as e:
            logger.error(f"Error installing {description}: {e}")
            self._log(f"❌ Error installing {description}: {e}")
            return False

    def install_scip_python(self) -> InstallResult:
        """Install scip-python via npm (it's a Sourcegraph npm package, not pip)."""
        if shutil.which("scip-python"):
            return InstallResult(
                tool="scip-python",
                success=True,
                already_installed=True,
            )

        # Check if npm is available
        if not shutil.which("npm"):
            return InstallResult(
                tool="scip-python",
                success=False,
                already_installed=False,
                error_message="npm not found - install Node.js first",
            )

        # Install via npm (scip-python is @sourcegraph/scip-python on npm)
        success = self._run_command(
            ["npm", "install", "-g", "@sourcegraph/scip-python"],
            "scip-python",
        )

        return InstallResult(
            tool="scip-python",
            success=success,
            already_installed=False,
            error_message=None if success else "npm install failed",
        )

    def install_scip_typescript(self) -> InstallResult:
        """Install scip-typescript via npm (Sourcegraph npm package)."""
        if shutil.which("scip-typescript"):
            return InstallResult(
                tool="scip-typescript",
                success=True,
                already_installed=True,
            )

        # Check if npm is available
        if not shutil.which("npm"):
            return InstallResult(
                tool="scip-typescript",
                success=False,
                already_installed=False,
                error_message="npm not found - install Node.js first",
            )

        # Install via npm (scip-typescript is @sourcegraph/scip-typescript on npm)
        success = self._run_command(
            ["npm", "install", "-g", "@sourcegraph/scip-typescript"],
            "scip-typescript",
        )

        return InstallResult(
            tool="scip-typescript",
            success=success,
            already_installed=False,
            error_message=None if success else "npm install failed",
        )

    def install_typescript_language_server(self) -> InstallResult:
        """Install typescript-language-server via npm."""
        if shutil.which("typescript-language-server"):
            return InstallResult(
                tool="typescript-language-server",
                success=True,
                already_installed=True,
            )

        # Check if npm is available
        if not shutil.which("npm"):
            return InstallResult(
                tool="typescript-language-server",
                success=False,
                already_installed=False,
                error_message="npm not found - install Node.js first",
            )

        # Try npm install
        success = self._run_command(
            ["npm", "install", "-g", "typescript-language-server"],
            "typescript-language-server",
        )

        return InstallResult(
            tool="typescript-language-server",
            success=success,
            already_installed=False,
            error_message=None if success else "npm install failed",
        )

    def install_python_dependencies(self) -> list[InstallResult]:
        """Install scip-python for Python code indexing.

        Returns:
            List of install results
        """
        results = []

        # Install scip-python (required for Python indexing)
        result = self.install_scip_python()
        results.append(result)

        if not result.success:
            self._log("⚠️  scip-python installation failed")
            if "npm not found" in (result.error_message or ""):
                self._log("    Node.js is required - install from https://nodejs.org/")

        return results

    def install_typescript_dependencies(self) -> list[InstallResult]:
        """Install scip-typescript and typescript-language-server for TypeScript/JavaScript indexing.

        Returns:
            List of install results
        """
        results = []

        # Install scip-typescript (required for TypeScript/JavaScript indexing)
        result = self.install_scip_typescript()
        results.append(result)

        if not result.success:
            self._log("⚠️  scip-typescript installation failed")
            if "npm not found" in (result.error_message or ""):
                self._log("    Node.js is required - install from https://nodejs.org/")

        # Install typescript-language-server (for LSP support)
        result = self.install_typescript_language_server()
        results.append(result)

        if not result.success:
            self._log("⚠️  typescript-language-server installation failed")

        return results

    def install_go_dependencies(self) -> list[InstallResult]:
        """Install scip-go and gopls for Go code indexing.

        Returns:
            List of install results
        """
        results = []

        # Check if Go is installed
        if not shutil.which("go"):
            results.append(
                InstallResult(
                    tool="scip-go",
                    success=False,
                    already_installed=False,
                    error_message="Go not installed - install from https://golang.org/dl/",
                )
            )
            return results

        # Install scip-go
        if shutil.which("scip-go"):
            results.append(InstallResult(tool="scip-go", success=True, already_installed=True))
        else:
            success = self._run_command(
                ["go", "install", "github.com/sourcegraph/scip-go/cmd/scip-go@latest"],
                "scip-go",
            )
            results.append(
                InstallResult(
                    tool="scip-go",
                    success=success,
                    already_installed=False,
                    error_message=None if success else "go install failed",
                )
            )

        # Install gopls (Go language server)
        if shutil.which("gopls"):
            results.append(InstallResult(tool="gopls", success=True, already_installed=True))
        else:
            success = self._run_command(
                ["go", "install", "golang.org/x/tools/gopls@latest"],
                "gopls",
            )
            results.append(
                InstallResult(
                    tool="gopls",
                    success=success,
                    already_installed=False,
                    error_message=None if success else "go install failed",
                )
            )

        return results

    def install_rust_dependencies(self) -> list[InstallResult]:
        """Verify rust-analyzer is installed for Rust SCIP indexing.

        rust-analyzer has built-in SCIP support via 'rust-analyzer scip' command.

        Returns:
            List of install results
        """
        results = []

        # Check if rust-analyzer is installed (usually via rustup)
        if shutil.which("rust-analyzer"):
            results.append(
                InstallResult(tool="rust-analyzer", success=True, already_installed=True)
            )
        else:
            # Try to install via rustup
            if shutil.which("rustup"):
                success = self._run_command(
                    ["rustup", "component", "add", "rust-analyzer"],
                    "rust-analyzer",
                )
                results.append(
                    InstallResult(
                        tool="rust-analyzer",
                        success=success,
                        already_installed=False,
                        error_message=None if success else "rustup component add failed",
                    )
                )
            else:
                results.append(
                    InstallResult(
                        tool="rust-analyzer",
                        success=False,
                        already_installed=False,
                        error_message="rustup not installed - install from https://rustup.rs/",
                    )
                )

        return results

    def install_csharp_dependencies(self) -> list[InstallResult]:
        """Install scip-dotnet for C# code indexing.

        NOTE: Due to .NET 10 compatibility issues with the published scip-dotnet package,
        this now builds scip-dotnet from source for .NET 10.

        Returns:
            List of install results
        """
        import tempfile
        from pathlib import Path

        results = []

        # Check if .NET is installed
        if not shutil.which("dotnet"):
            results.append(
                InstallResult(
                    tool="scip-dotnet",
                    success=False,
                    already_installed=False,
                    error_message=".NET SDK not installed - install from https://dotnet.microsoft.com/download",
                )
            )
            return results

        # Check if scip-dotnet is already built and available
        scip_dotnet_path = Path.home() / ".local" / "bin" / "scip-dotnet"
        if scip_dotnet_path.exists():
            results.append(InstallResult(tool="scip-dotnet", success=True, already_installed=True))
            return results

        # Build scip-dotnet from source for .NET 10 compatibility
        self._log("🔧 Building scip-dotnet from source for .NET 10...")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                build_dir = Path(tmpdir) / "scip-dotnet"

                # Clone repository
                clone_result = subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "https://github.com/sourcegraph/scip-dotnet.git",
                        str(build_dir),
                    ],
                    capture_output=True,
                    timeout=120,
                )

                if clone_result.returncode != 0:
                    results.append(
                        InstallResult(
                            tool="scip-dotnet",
                            success=False,
                            already_installed=False,
                            error_message="Failed to clone scip-dotnet repository",
                        )
                    )
                    return results

                # Build for .NET 10
                build_result = subprocess.run(
                    ["dotnet", "build", "-c", "Release"],
                    cwd=str(build_dir),
                    capture_output=True,
                    timeout=300,
                )

                if build_result.returncode != 0:
                    results.append(
                        InstallResult(
                            tool="scip-dotnet",
                            success=False,
                            already_installed=False,
                            error_message="Failed to build scip-dotnet",
                        )
                    )
                    return results

                # Find the net10.0 binary and copy to local bin
                net10_binary = (
                    build_dir / "ScipDotnet.Tests" / "bin" / "Release" / "net10.0" / "scip-dotnet"
                )

                if not net10_binary.exists():
                    # Try the main ScipDotnet project output
                    net10_binary = (
                        build_dir / "ScipDotnet" / "bin" / "Release" / "net10.0" / "scip-dotnet"
                    )

                if net10_binary.exists():
                    # Create ~/.local/bin if it doesn't exist
                    local_bin = Path.home() / ".local" / "bin"
                    local_bin.mkdir(parents=True, exist_ok=True)

                    # Copy the entire output directory (includes DLLs)
                    import shutil as shutil_module

                    scip_dotnet_output = net10_binary.parent
                    dest_dir = local_bin / "scip-dotnet-net10"
                    if dest_dir.exists():
                        shutil_module.rmtree(dest_dir)
                    shutil_module.copytree(scip_dotnet_output, dest_dir)

                    # Create wrapper script
                    wrapper_script = local_bin / "scip-dotnet"
                    wrapper_script.write_text(
                        f"""#!/bin/bash
exec dotnet {dest_dir / "ScipDotnet.dll"} "$@"
"""
                    )
                    wrapper_script.chmod(0o755)

                    self._log(f"✅ Built and installed scip-dotnet to {wrapper_script}")

                    results.append(
                        InstallResult(
                            tool="scip-dotnet",
                            success=True,
                            already_installed=False,
                        )
                    )
                else:
                    results.append(
                        InstallResult(
                            tool="scip-dotnet",
                            success=False,
                            already_installed=False,
                            error_message="Built binary not found in expected location",
                        )
                    )

        except Exception as e:
            logger.error(f"Failed to build scip-dotnet from source: {e}")
            results.append(
                InstallResult(
                    tool="scip-dotnet",
                    success=False,
                    already_installed=False,
                    error_message=str(e),
                )
            )

        return results

    def install_all_auto_installable(self) -> dict[str, InstallResult]:
        """Install all dependencies that can be auto-installed.

        Returns:
            Dict mapping tool name to install result
        """
        results = {}

        if not self.quiet:
            self._log("🔍 Checking blarify dependencies...")

        # Python dependencies
        for result in self.install_python_dependencies():
            results[result.tool] = result

        # TypeScript dependencies
        for result in self.install_typescript_dependencies():
            results[result.tool] = result

        # Go dependencies
        for result in self.install_go_dependencies():
            results[result.tool] = result

        # Rust dependencies
        for result in self.install_rust_dependencies():
            results[result.tool] = result

        # C# dependencies
        for result in self.install_csharp_dependencies():
            results[result.tool] = result

        # Summary
        installed_count = sum(1 for r in results.values() if r.success and not r.already_installed)
        already_installed_count = sum(1 for r in results.values() if r.already_installed)
        failed_count = sum(1 for r in results.values() if not r.success)

        if not self.quiet:
            if installed_count > 0:
                self._log(f"✨ Installed {installed_count} dependencies")
            if already_installed_count > 0:
                self._log(f"✅ {already_installed_count} dependencies already installed")
            if failed_count > 0:
                self._log(f"⚠️  {failed_count} dependencies could not be auto-installed")

        return results

    def show_system_dependency_help(self) -> None:
        """Show help for system dependencies that cannot be auto-installed."""
        messages = []

        # Check .NET
        if not shutil.which("dotnet"):
            messages.append(
                "📦 C# support: Install .NET SDK from https://dotnet.microsoft.com/download (versions 6-10 supported)"
            )

        # Check Go
        if not shutil.which("go"):
            messages.append(
                "📦 Go support: Install Go from https://golang.org/dl/ or via package manager (apt install golang-go)"
            )

        # Check Java
        if not shutil.which("java"):
            messages.append(
                "📦 Java support: Install JDK from https://adoptium.net/ or via package manager (apt install default-jdk)"
            )

        # Check PHP
        if not shutil.which("php"):
            messages.append(
                "📦 PHP support: Install PHP from https://www.php.net/ or via package manager (apt install php-cli)"
            )

        # Check Ruby
        if not shutil.which("ruby"):
            messages.append(
                "📦 Ruby support: Install Ruby from https://www.ruby-lang.org/ or via package manager (apt install ruby-full)"
            )

        if messages and not self.quiet:
            self._log("\n💡 Optional language support:")
            for msg in messages:
                self._log(f"   {msg}")
