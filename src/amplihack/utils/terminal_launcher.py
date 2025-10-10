"""Cross-platform terminal launcher for file tailing."""

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class TerminalLauncher:
    """Launches terminals with tail commands across different operating systems."""

    @staticmethod
    def detect_os() -> str:
        """Detect the operating system.

        Returns:
            One of: 'windows', 'linux', 'macos'
        """
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        if system == "windows":
            return "windows"
        return "linux"

    @staticmethod
    def launch_tail_terminal(file_path: Path) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Launch a terminal window tailing the specified file.

        Args:
            file_path: Path to the file to tail

        Returns:
            Tuple of (success_bool, process_or_none)
        """
        os_type = TerminalLauncher.detect_os()
        abs_path = file_path.absolute()

        try:
            if os_type == "macos":
                return TerminalLauncher._launch_macos_terminal(abs_path)
            if os_type == "linux":
                return TerminalLauncher._launch_linux_terminal(abs_path)
            if os_type == "windows":
                return TerminalLauncher._launch_windows_terminal(abs_path)
            print(f"Unsupported OS: {os_type}")
            return False, None
        except Exception as e:
            print(f"Failed to launch terminal for {abs_path}: {e}")
            return False, None

    @staticmethod
    def _launch_macos_terminal(file_path: Path) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Launch macOS Terminal with tail command."""
        script = f'tell app "Terminal" to do script "tail -f {file_path}"'
        try:
            process = subprocess.Popen(
                ["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # Give osascript time to execute
            import time

            time.sleep(0.5)
            return True, process
        except Exception as e:
            print(f"Failed to launch macOS terminal: {e}")
            return False, None

    @staticmethod
    def _launch_linux_terminal(file_path: Path) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Launch Linux terminal with tail command."""
        # Try different terminal emulators in order of preference
        terminals = [
            ["x-terminal-emulator", "-e"],
            ["gnome-terminal", "--", "bash", "-c"],
            ["konsole", "-e"],
            ["xfce4-terminal", "-e"],
            ["xterm", "-e"],
            ["mate-terminal", "-e"],
        ]

        for terminal_cmd in terminals:
            if shutil.which(terminal_cmd[0]):
                try:
                    if terminal_cmd[0] == "gnome-terminal":
                        # Special case for gnome-terminal which needs bash -c
                        cmd = terminal_cmd + [f"tail -f {file_path}; exec bash"]
                    else:
                        cmd = terminal_cmd + [f"tail -f {file_path}"]

                    process = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    return True, process
                except Exception:
                    continue

        print("No suitable terminal emulator found")
        return False, None

    @staticmethod
    def _launch_windows_terminal(file_path: Path) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Launch Windows terminal with tail equivalent (Get-Content -Wait)."""
        try:
            # Convert to Windows path format
            windows_path = str(file_path).replace("/", "\\")

            # Try Windows Terminal first, then fall back to PowerShell
            terminals = [
                ["wt", "-p", "Windows PowerShell", "--", "powershell", "-NoExit", "-Command"],
                ["powershell", "-NoExit", "-Command"],
            ]

            command = f"Get-Content '{windows_path}' -Wait"

            for terminal_cmd in terminals:
                if shutil.which(terminal_cmd[0]):
                    try:
                        cmd = terminal_cmd + [command]
                        process = subprocess.Popen(
                            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        return True, process
                    except Exception:
                        continue

            print("No suitable terminal found for Windows")
            return False, None

        except Exception as e:
            print(f"Failed to launch Windows terminal: {e}")
            return False, None
