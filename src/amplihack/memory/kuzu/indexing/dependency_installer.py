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
        """Install scip-python via pip."""
        if shutil.which("scip-python"):
            return InstallResult(
                tool="scip-python",
                success=True,
                already_installed=True,
            )

        # Try pip install
        success = self._run_command(
            [sys.executable, "-m", "pip", "install", "scip-python"],
            "scip-python",
        )

        return InstallResult(
            tool="scip-python",
            success=success,
            already_installed=False,
            error_message=None if success else "pip install failed",
        )

    def install_jedi_language_server(self) -> InstallResult:
        """Install jedi-language-server via pip."""
        # Check if already installed by trying to import
        try:
            import jedi_language_server  # noqa: F401

            return InstallResult(
                tool="jedi-language-server",
                success=True,
                already_installed=True,
            )
        except ImportError:
            pass

        # Try pip install
        success = self._run_command(
            [sys.executable, "-m", "pip", "install", "jedi-language-server"],
            "jedi-language-server",
        )

        return InstallResult(
            tool="jedi-language-server",
            success=success,
            already_installed=False,
            error_message=None if success else "pip install failed",
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
        """Install all auto-installable Python dependencies.

        Returns:
            List of install results
        """
        results = []

        # Try scip-python first (preferred)
        result = self.install_scip_python()
        results.append(result)

        # If scip-python failed, install jedi-language-server as fallback
        if not result.success:
            self._log("⚠️  scip-python failed, installing jedi-language-server as fallback...")
            result = self.install_jedi_language_server()
            results.append(result)

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
        result = self.install_typescript_language_server()
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
