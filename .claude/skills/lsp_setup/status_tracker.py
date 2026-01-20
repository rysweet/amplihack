"""
Status Tracker for LSP three-layer architecture.

Philosophy:
- Checks all three layers: System binaries, Claude plugins, .env config
- Generates actionable user guidance for missing components
- Platform-specific installation instructions
- Zero-BS: Real checks, no fake status

Public API:
    StatusTracker: Tracks LSP configuration status across three layers
    check_layer_1: Check system LSP binaries
    check_layer_2: Check Claude Code plugins
    check_layer_3: Check .env configuration
    get_full_status: Get complete status across all layers
    generate_user_guidance: Create actionable setup instructions
"""

import shutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

__all__ = ["StatusTracker", "LayerStatus"]


@dataclass
class LayerStatus:
    """Status for a single layer."""
    installed: bool
    details: Optional[str] = None
    install_guide: Optional[str] = None


class StatusTracker:
    """Tracks LSP configuration status across three layers."""

    # Mapping of languages to system binaries
    LANGUAGE_TO_BINARY = {
        "python": "pyright",
        "typescript": "vtsls",
        "javascript": "vtsls",
        "rust": "rust-analyzer",
        "go": "gopls",
        "java": "jdtls",
        "cpp": "clangd",
        "c": "clangd",
        "ruby": "ruby-lsp",
        "php": "phpactor",
        "csharp": "omnisharp",
        "kotlin": "kotlin-language-server",
        "swift": "sourcekit-lsp",
        "scala": "metals",
        "lua": "lua-language-server",
        "elixir": "elixir-ls",
        "haskell": "haskell-language-server",
    }

    # Platform-specific install commands
    INSTALL_COMMANDS = {
        "python": {
            "darwin": "npm install -g pyright",
            "linux": "npm install -g pyright",
        },
        "typescript": {
            "darwin": "npm install -g @vtsls/language-server",
            "linux": "npm install -g @vtsls/language-server",
        },
        "javascript": {
            "darwin": "npm install -g @vtsls/language-server",
            "linux": "npm install -g @vtsls/language-server",
        },
        "rust": {
            "darwin": "rustup component add rust-analyzer",
            "linux": "rustup component add rust-analyzer",
        },
        "go": {
            "darwin": "go install golang.org/x/tools/gopls@latest",
            "linux": "go install golang.org/x/tools/gopls@latest",
        },
        "java": {
            "darwin": "brew install jdtls",
            "linux": "Download from eclipse.org/jdtls",
        },
        "cpp": {
            "darwin": "brew install llvm",
            "linux": "sudo apt install clangd",
        },
        "c": {
            "darwin": "brew install llvm",
            "linux": "sudo apt install clangd",
        },
        "ruby": {
            "darwin": "gem install ruby-lsp",
            "linux": "gem install ruby-lsp",
        },
        "php": {
            "darwin": "composer global require phpactor/phpactor",
            "linux": "composer global require phpactor/phpactor",
        },
    }

    def __init__(self, project_root: Path, languages: List[str]):
        """
        Initialize status tracker.

        Args:
            project_root: Path to project root directory
            languages: List of language names to track
        """
        self.project_root = Path(project_root)
        self.languages = languages
        self.env_file = self.project_root / ".env"

    def check_layer_1(self) -> Dict[str, Dict]:
        """
        Check Layer 1: System LSP binaries.

        Returns:
            Dict mapping language -> status info
        """
        status = {}

        for lang in self.languages:
            binary = self.LANGUAGE_TO_BINARY.get(lang)
            if not binary:
                status[lang] = {
                    "installed": False,
                    "error": f"Unknown language: {lang}"
                }
                continue

            # Check if binary exists
            binary_path = shutil.which(binary)
            is_installed = binary_path is not None

            status[lang] = {
                "installed": is_installed,
                "binary": binary,
                "path": binary_path if is_installed else None,
            }

            # Add install guide if missing
            if not is_installed:
                status[lang]["install_guide"] = self._get_install_command(lang)

        return status

    def check_layer_2(self) -> Dict[str, Dict]:
        """
        Check Layer 2: Claude Code plugins.

        Returns:
            Dict mapping language -> plugin status
        """
        from .plugin_manager import PluginManager

        manager = PluginManager()
        installed_plugins = manager.list_installed_plugins()

        status = {}
        for lang in self.languages:
            is_installed = lang in installed_plugins

            status[lang] = {
                "installed": is_installed,
                "plugin_name": lang,
            }

            if not is_installed:
                status[lang]["install_guide"] = f"npx cclsp install {lang}"

        return status

    def check_layer_3(self) -> Dict[str, Any]:
        """
        Check Layer 3: .env configuration.

        Returns:
            Dict with enabled status and config details
        """
        if not self.env_file.exists():
            return {
                "enabled": False,
                "env_file_exists": False,
                "install_guide": "Run: echo 'ENABLE_LSP_TOOL=1' >> .env"
            }

        # Check if ENABLE_LSP_TOOL=1 is set
        content = self.env_file.read_text()
        enabled = "ENABLE_LSP_TOOL=1" in content

        return {
            "enabled": enabled,
            "env_file_exists": True,
            "path": str(self.env_file),
            "install_guide": "Add 'ENABLE_LSP_TOOL=1' to .env file" if not enabled else None
        }

    def get_full_status(self) -> Dict[str, Any]:
        """
        Get complete status across all three layers.

        Returns:
            Dict with status for all layers plus overall readiness
        """
        layer_1 = self.check_layer_1()
        layer_2 = self.check_layer_2()
        layer_3 = self.check_layer_3()

        # Check if all layers are ready
        all_layer_1_ready = all(
            lang_status["installed"]
            for lang_status in layer_1.values()
        )
        all_layer_2_ready = all(
            lang_status["installed"]
            for lang_status in layer_2.values()
        )
        layer_3_ready = layer_3["enabled"]

        overall_ready = all_layer_1_ready and all_layer_2_ready and layer_3_ready

        return {
            "layer_1": layer_1,
            "layer_2": layer_2,
            "layer_3": layer_3,
            "overall_ready": overall_ready,
        }

    def generate_user_guidance(self) -> str:
        """
        Generate actionable setup guidance based on current status.

        Returns:
            Formatted string with setup instructions
        """
        status = self.get_full_status()

        if status["overall_ready"]:
            return "✅ All LSP layers configured! No action needed."

        guidance_parts = ["LSP Setup Status:\n"]

        # Layer 1 guidance
        layer_1_issues = [
            (lang, info)
            for lang, info in status["layer_1"].items()
            if not info["installed"]
        ]

        if layer_1_issues:
            guidance_parts.append("\n🔴 Layer 1: Missing System LSP Binaries")
            for lang, info in layer_1_issues:
                guidance_parts.append(f"  • {lang}: {info.get('install_guide', 'See docs')}")

        # Layer 2 guidance
        layer_2_issues = [
            (lang, info)
            for lang, info in status["layer_2"].items()
            if not info["installed"]
        ]

        if layer_2_issues:
            guidance_parts.append("\n🟡 Layer 2: Missing Claude Code Plugins")
            for lang, info in layer_2_issues:
                guidance_parts.append(f"  • {lang}: {info.get('install_guide', 'See docs')}")

        # Layer 3 guidance
        if not status["layer_3"]["enabled"]:
            guidance_parts.append("\n🟠 Layer 3: .env Configuration Missing")
            guidance_parts.append(f"  • {status['layer_3'].get('install_guide', 'See docs')}")

        return "\n".join(guidance_parts)

    def _get_install_command(self, language: str) -> str:
        """Get platform-specific install command for a language."""
        system = platform.system().lower()
        if system == "darwin":
            platform_key = "darwin"
        else:
            platform_key = "linux"

        commands = self.INSTALL_COMMANDS.get(language, {})
        return commands.get(platform_key, f"Install {language} LSP server manually")

    def get_setup_progress(self) -> Dict[str, Any]:
        """
        Get setup progress metrics.

        Returns:
            Dict with progress percentages for each layer
        """
        status = self.get_full_status()

        total_langs = len(self.languages)
        if total_langs == 0:
            return {
                "layer_1_progress": 100,
                "layer_2_progress": 100,
                "layer_3_progress": 100,
                "overall_progress": 100,
            }

        # Layer 1 progress
        layer_1_installed = sum(
            1 for info in status["layer_1"].values()
            if info["installed"]
        )
        layer_1_progress = (layer_1_installed / total_langs) * 100

        # Layer 2 progress
        layer_2_installed = sum(
            1 for info in status["layer_2"].values()
            if info["installed"]
        )
        layer_2_progress = (layer_2_installed / total_langs) * 100

        # Layer 3 progress (binary: 0 or 100)
        layer_3_progress = 100 if status["layer_3"]["enabled"] else 0

        # Overall progress (weighted average)
        overall_progress = (
            layer_1_progress * 0.4 +
            layer_2_progress * 0.4 +
            layer_3_progress * 0.2
        )

        return {
            "layer_1_progress": round(layer_1_progress, 1),
            "layer_2_progress": round(layer_2_progress, 1),
            "layer_3_progress": round(layer_3_progress, 1),
            "overall_progress": round(overall_progress, 1),
        }

    def get_next_action(self) -> Optional[str]:
        """Get the next recommended action for setup."""
        status = self.get_full_status()
        if status["overall_ready"]:
            return None

        # Priority: Layer 3 -> Layer 1 -> Layer 2
        if not status["layer_3"]["enabled"]:
            return status["layer_3"].get("install_guide", "Configure .env")

        for lang, info in status["layer_1"].items():
            if not info["installed"]:
                return info.get("install_guide", f"Install {lang} LSP binary")

        for lang, info in status["layer_2"].items():
            if not info["installed"]:
                return info.get("install_guide", f"Install {lang} plugin")

        return None

    def get_missing_components(self) -> List[str]:
        """Get list of missing components."""
        status = self.get_full_status()
        missing = []

        for lang, info in status["layer_1"].items():
            if not info["installed"]:
                missing.append(f"Layer 1: {lang} binary")

        for lang, info in status["layer_2"].items():
            if not info["installed"]:
                missing.append(f"Layer 2: {lang} plugin")

        if not status["layer_3"]["enabled"]:
            missing.append("Layer 3: .env configuration")

        return missing

    def get_completion_percentage(self) -> float:
        """Get overall completion percentage."""
        progress = self.get_setup_progress()
        return progress["overall_progress"]

    def validate_layer_dependencies(self) -> Dict[str, bool]:
        """Validate dependencies between layers."""
        status = self.get_full_status()
        return {
            "layer_2_requires_layer_1": True,  # Plugins need binaries
            "layer_3_independent": True,  # .env is independent
        }

    def export_status_report(self, format: str = "text") -> str:
        """Export status report in specified format."""
        if format == "json":
            import json
            return json.dumps(self.get_full_status(), indent=2)
        return self.generate_user_guidance()

    def get_troubleshooting_tips(self) -> List[str]:
        """Get troubleshooting tips based on current status."""
        status = self.get_full_status()
        tips = []

        if not status["overall_ready"]:
            tips.append("Check that npx is installed: npx --version")
            tips.append("Verify PATH includes LSP binaries: echo $PATH")
            tips.append("Check .env file syntax")

        return tips

    def get_platform_requirements(self) -> Dict[str, List[str]]:
        """Get platform-specific requirements."""
        system = platform.system().lower()
        platform_name = "darwin" if system == "darwin" else "linux"

        requirements = {}
        for lang in self.languages:
            cmd = self._get_install_command(lang)
            requirements[lang] = [cmd]

        return requirements

    def get_install_commands(self) -> Dict[str, str]:
        """Get install commands for all languages."""
        commands = {}
        for lang in self.languages:
            commands[lang] = self._get_install_command(lang)
        return commands

    def estimate_setup_time(self) -> int:
        """Estimate setup time in minutes."""
        status = self.get_full_status()
        missing_count = len(self.get_missing_components())

        # Rough estimate: 2 minutes per missing component
        return missing_count * 2
