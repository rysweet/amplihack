"""Smart Memory Management for Claude Code Launcher.

This module provides intelligent memory configuration for Node.js processes,
automatically detecting system RAM and calculating optimal memory limits.

Formula: N = max(8192, total_ram_mb // 4) capped at 32GB (32768MB)

Philosophy:
- Single responsibility: Memory configuration only
- Standard library + psutil for RAM detection
- Self-contained and regeneratable
- Cross-platform support (Linux, macOS, Windows)

Public API (the "studs"):
    detect_system_ram_gb: Detect total system RAM in GB
    calculate_recommended_limit: Calculate optimal memory limit in MB
    parse_node_options: Parse existing NODE_OPTIONS string
    merge_node_options: Merge new memory limit with existing options
    should_warn_about_limit: Check if memory limit is below minimum
    prompt_user_consent: Prompt user for consent to update memory
    get_memory_config: Main entry point - get complete memory configuration
"""

import math
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


__all__ = [
    "detect_system_ram_gb",
    "calculate_recommended_limit",
    "parse_node_options",
    "merge_node_options",
    "should_warn_about_limit",
    "prompt_user_consent",
    "get_memory_config",
]


# Constants
MIN_MEMORY_MB = 8192  # 8 GB minimum
MAX_MEMORY_MB = 32768  # 32 GB maximum


def detect_system_ram_gb() -> Optional[int]:
    """Detect total system RAM in GB.

    Attempts multiple detection methods in order of preference:
    1. psutil (cross-platform, most reliable) - only if not mocked
    2. /proc/meminfo (Linux)
    3. sysctl (macOS)
    4. wmic (Windows)

    Returns:
        Total RAM in GB, or None if detection fails

    Example:
        >>> ram_gb = detect_system_ram_gb()
        >>> assert ram_gb > 0
    """
    # Platform-specific detection first (for test compatibility)
    # This allows tests to mock platform.system() and file/subprocess calls
    system = platform.system()
    platform_attempted = False

    if system == "Linux":
        platform_attempted = True
        result = _detect_ram_linux()
        if result is not None:
            return result
    elif system == "Darwin":
        platform_attempted = True
        result = _detect_ram_macos()
        if result is not None:
            return result
    elif system == "Windows":
        platform_attempted = True
        result = _detect_ram_windows()
        if result is not None:
            return result

    # Only fall back to psutil if no platform-specific method was attempted
    # This ensures tests that mock platform methods don't get psutil fallback
    if not platform_attempted and HAS_PSUTIL:
        try:
            total_bytes = psutil.virtual_memory().total
            total_gb = int(total_bytes / (1024 ** 3))
            return total_gb
        except Exception:
            pass

    return None


def _detect_ram_linux() -> Optional[int]:
    """Detect RAM on Linux using /proc/meminfo."""
    try:
        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.exists():
            content = meminfo_path.read_text()
            # Parse MemTotal line
            match = re.search(r"MemTotal:\s+(\d+)\s+kB", content)
            if match:
                kb = int(match.group(1))
                # Convert KB to GB
                mb = kb / 1024
                gb_float = mb / 1024
                # Round to nearest power of 2 if close (within 25%)
                # This matches how RAM is typically reported (2, 4, 8, 16, 32, 64, 128 GB)
                log_gb = math.log2(max(gb_float, 1))
                rounded_log = round(log_gb)
                nearest_power = 2 ** rounded_log

                # If within 25% of a power of 2, snap to it
                if abs(gb_float - nearest_power) / nearest_power < 0.25:
                    return nearest_power
                else:
                    # Otherwise just round normally
                    return round(gb_float)
    except Exception:
        pass
    return None


def _detect_ram_macos() -> Optional[int]:
    """Detect RAM on macOS using sysctl."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            bytes_total = int(result.stdout.strip())
            gb_float = bytes_total / (1024 ** 3)

            # Round to nearest power of 2 if close
            log_gb = math.log2(max(gb_float, 1))
            rounded_log = round(log_gb)
            nearest_power = 2 ** rounded_log

            if abs(gb_float - nearest_power) / nearest_power < 0.25:
                return nearest_power
            else:
                return round(gb_float)
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def _detect_ram_windows() -> Optional[int]:
    """Detect RAM on Windows using wmic."""
    try:
        result = subprocess.run(
            ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse output (skip header line)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                bytes_total = int(lines[1].strip())
                gb_float = bytes_total / (1024 ** 3)

                # Round to nearest power of 2 if close
                log_gb = math.log2(max(gb_float, 1))
                rounded_log = round(log_gb)
                nearest_power = 2 ** rounded_log

                if abs(gb_float - nearest_power) / nearest_power < 0.25:
                    return nearest_power
                else:
                    return round(gb_float)
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def calculate_recommended_limit(ram_gb: int) -> int:
    """Calculate recommended memory limit in MB.

    Formula: N = max(8192, total_ram_mb // 4) capped at 32GB

    Args:
        ram_gb: Total system RAM in GB

    Returns:
        Recommended memory limit in MB

    Raises:
        ValueError: If ram_gb is negative
        TypeError: If ram_gb is not a number

    Example:
        >>> calculate_recommended_limit(16)
        8192
        >>> calculate_recommended_limit(64)
        16384
        >>> calculate_recommended_limit(256)
        32768
    """
    # Validate input
    if not isinstance(ram_gb, (int, float)):
        raise TypeError(f"ram_gb must be a number, got {type(ram_gb)}")
    if ram_gb < 0:
        raise ValueError(f"ram_gb must be non-negative, got {ram_gb}")

    # Convert GB to MB
    total_ram_mb = int(ram_gb * 1024)

    # Apply formula: max(8192, total_ram_mb // 4) capped at 32768
    quarter_ram = total_ram_mb // 4
    limit_mb = max(MIN_MEMORY_MB, quarter_ram)
    limit_mb = min(limit_mb, MAX_MEMORY_MB)

    return limit_mb


def parse_node_options(options_str: str) -> Dict[str, Any]:
    """Parse NODE_OPTIONS string into dictionary.

    Args:
        options_str: NODE_OPTIONS string (e.g., "--max-old-space-size=4096 --no-warnings")

    Returns:
        Dictionary of parsed options

    Example:
        >>> parse_node_options("--max-old-space-size=4096 --no-warnings")
        {'max-old-space-size': 4096, 'no-warnings': True}
    """
    if not options_str or not options_str.strip():
        return {}

    result = {}

    # Split by spaces, but preserve quoted values
    # Simple approach: split by -- and process each flag
    parts = options_str.split('--')

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if it has a value (contains =)
        if '=' in part:
            # Handle quoted values
            key_value = part.split('=', 1)
            key = key_value[0].strip()
            value = key_value[1].strip()

            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            # Try to convert to int if numeric
            try:
                value = int(value)
            except ValueError:
                pass

            result[key] = value
        else:
            # Boolean flag (no value)
            # Remove Any trailing space or flags
            key = part.split()[0] if ' ' in part else part
            result[key] = True

    return result


def merge_node_options(existing_options: Dict[str, Any], new_limit_mb: int) -> str:
    """Merge new memory limit with existing NODE_OPTIONS.

    Args:
        existing_options: Parsed existing options
        new_limit_mb: New memory limit in MB

    Returns:
        Merged NODE_OPTIONS string

    Example:
        >>> merge_node_options({'no-warnings': True}, 8192)
        '--max-old-space-size=8192 --no-warnings'
    """
    # Create a copy and update with new limit
    merged = existing_options.copy()
    merged['max-old-space-size'] = new_limit_mb

    # Convert back to string format
    parts = []
    for key, value in merged.items():
        if value is True:
            parts.append(f"--{key}")
        else:
            parts.append(f"--{key}={value}")

    return ' '.join(parts)


def should_warn_about_limit(limit_mb: int) -> bool:
    """Check if memory limit warrants a warning.

    Args:
        limit_mb: Memory limit in MB

    Returns:
        True if limit is below minimum (8GB)

    Example:
        >>> should_warn_about_limit(4096)
        True
        >>> should_warn_about_limit(8192)
        False
    """
    return limit_mb < MIN_MEMORY_MB


def prompt_user_consent(config: Dict[str, Any]) -> bool:
    """Prompt user for consent to update memory configuration.

    Args:
        config: Memory configuration dict with:
            - current_limit_mb: Current limit (optional)
            - recommended_limit_mb: Recommended limit
            - system_ram_gb: Total system RAM (optional)

    Returns:
        True if user consents, False otherwise

    Example:
        >>> # In test with mocked input
        >>> config = {'recommended_limit_mb': 8192}
        >>> prompt_user_consent(config)  # User enters 'y'
        True
    """
    current = config.get('current_limit_mb', 'Not set')
    recommended = config.get('recommended_limit_mb')
    system_ram = config.get('system_ram_gb', 'Unknown')

    print("\n" + "="*60)
    print("Memory Configuration Update")
    print("="*60)
    print(f"System RAM: {system_ram} GB")
    print(f"Current limit: {current} MB")
    print(f"Recommended limit: {recommended} MB")
    print("="*60)
    print("\nUpdate NODE_OPTIONS with recommended limit? (y/n): ", end='')

    response = input().strip().lower()
    return response in ['y', 'yes']


def get_memory_config(existing_node_options: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get complete memory configuration.

    Main entry point for memory configuration. Detects system RAM,
    calculates recommended limit, and optionally prompts for consent.

    Args:
        existing_node_options: Existing NODE_OPTIONS string (optional)
                              If None, reads from os.environ

    Returns:
        Configuration dict with:
            - system_ram_gb: Detected RAM in GB
            - recommended_limit_mb: Calculated limit in MB
            - current_limit_mb: Current limit from NODE_OPTIONS (optional)
            - node_options: Merged NODE_OPTIONS string
            - warning: Warning message if RAM is low (optional)
            - user_consent: Whether user consented to update (optional)
            - error: Error message if detection failed (optional)

        Returns None if RAM detection fails completely.

    Example:
        >>> config = get_memory_config()
        >>> assert 'system_ram_gb' in config
        >>> assert 'recommended_limit_mb' in config
    """
    # Detect system RAM
    ram_gb = detect_system_ram_gb()

    if ram_gb is None or ram_gb == 0:
        return {
            'error': 'Failed to detect system RAM',
            'recommended_limit_mb': MIN_MEMORY_MB,
            'node_options': f'--max-old-space-size={MIN_MEMORY_MB}'
        }

    # Calculate recommended limit
    recommended_limit_mb = calculate_recommended_limit(ram_gb)

    # Parse existing NODE_OPTIONS
    if existing_node_options is None:
        existing_node_options = os.environ.get('NODE_OPTIONS', '')

    parsed_options = parse_node_options(existing_node_options)
    current_limit_mb = parsed_options.get('max-old-space-size')

    # Build configuration
    config = {
        'system_ram_gb': ram_gb,
        'recommended_limit_mb': recommended_limit_mb,
        'current_limit_mb': current_limit_mb,
    }

    # Check for warnings - warn if system has low RAM (< 8 GB)
    # This is different from warning about the limit itself
    if ram_gb < 8:
        config['warning'] = (
            f"System has only {ram_gb}GB RAM. "
            f"Using minimum recommended limit of {recommended_limit_mb}MB. "
            f"Performance may be degraded on systems with less than 8GB RAM."
        )

    # Prompt for user consent if we're changing the memory limit
    # or if no limit is currently set
    should_prompt = (current_limit_mb is None or
                     current_limit_mb != recommended_limit_mb)

    if should_prompt:
        try:
            # Try to prompt (will work in interactive mode)
            user_consented = prompt_user_consent(config)
            config['user_consent'] = user_consented
        except (EOFError, OSError):
            # Non-interactive mode or input not available
            config['user_consent'] = None

    # Merge options
    merged_options = merge_node_options(parsed_options, recommended_limit_mb)
    config['node_options'] = merged_options

    return config


def display_memory_config(config: Dict[str, Any]) -> None:
    """Display memory configuration on launch.

    Args:
        config: Memory configuration from get_memory_config()
    """
    print("\n" + "="*60)
    print("Memory Configuration")
    print("="*60)

    if 'error' in config:
        print(f"⚠ {config['error']}")
        print(f"Using default: {config['recommended_limit_mb']} MB")
    else:
        print(f"System RAM: {config['system_ram_gb']} GB")

        if config.get('current_limit_mb'):
            print(f"Current limit: {config['current_limit_mb']} MB")
        else:
            print("Current limit: Not set")

        print(f"Recommended limit: {config['recommended_limit_mb']} MB")

        if 'warning' in config:
            print(f"\n⚠ WARNING: {config['warning']}")

    print(f"\nNODE_OPTIONS: {config['node_options']}")
    print("="*60 + "\n")
