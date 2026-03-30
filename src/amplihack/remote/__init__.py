"""Bridge package that exposes the bundle-backed remote implementation from src imports."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

_BUNDLE_REMOTE_DIR = (
    Path(__file__).resolve().parents[3] / "amplifier-bundle" / "tools" / "amplihack" / "remote"
)
if not _BUNDLE_REMOTE_DIR.exists():  # pragma: no cover - defensive install guard
    raise ImportError(f"Bundle-backed remote implementation not found at {_BUNDLE_REMOTE_DIR}")

package_path = globals().get("__path__")
if package_path is not None:
    bundle_remote_str = str(_BUNDLE_REMOTE_DIR)
    if bundle_remote_str not in package_path:
        package_path.append(bundle_remote_str)

_EXPORTS = {
    "execute_remote_workflow": ".cli",
    "main": ".cli",
    "ContextPackager": ".context_packager",
    "SecretMatch": ".context_packager",
    "CleanupError": ".errors",
    "ExecutionError": ".errors",
    "IntegrationError": ".errors",
    "PackagingError": ".errors",
    "ProvisioningError": ".errors",
    "RemoteExecutionError": ".errors",
    "TransferError": ".errors",
    "ExecutionResult": ".executor",
    "Executor": ".executor",
    "BranchInfo": ".integrator",
    "IntegrationSummary": ".integrator",
    "Integrator": ".integrator",
    "VM": ".orchestrator",
    "Orchestrator": ".orchestrator",
    "VMOptions": ".orchestrator",
    "VMPoolEntry": ".vm_pool",
    "VMPoolManager": ".vm_pool",
    "VMSize": ".vm_pool",
}

__all__ = [
    "execute_remote_workflow",
    "main",
    "ContextPackager",
    "Orchestrator",
    "Executor",
    "Integrator",
    "VMPoolManager",
    "VM",
    "VMOptions",
    "VMSize",
    "VMPoolEntry",
    "SecretMatch",
    "ExecutionResult",
    "BranchInfo",
    "IntegrationSummary",
    "RemoteExecutionError",
    "PackagingError",
    "ProvisioningError",
    "TransferError",
    "ExecutionError",
    "IntegrationError",
    "CleanupError",
]


def __getattr__(name: str) -> Any:
    """Lazily resolve exports from the bundle-backed remote implementation."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports for interactive inspection."""
    return sorted(set(globals()) | set(__all__))
