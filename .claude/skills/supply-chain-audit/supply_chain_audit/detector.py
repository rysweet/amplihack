# File: supply_chain_audit/detector.py
"""Ecosystem detection — maps repo file signals to audit dimensions."""

from pathlib import Path

from .errors import InvalidScopeError

# Scope → dimension numbers (strict allowlist, order matters for error messages)
SCOPE_TO_DIMS = {
    "gha": [1, 2, 3, 4],
    "containers": [5, 12],
    "credentials": [6],
    "dotnet": [7],
    "python": [8],
    "rust": [9],
    "node": [10],
    "go": [11],
    "all": list(range(1, 13)),
}
VALID_SCOPES: list[str] = list(SCOPE_TO_DIMS.keys())

# Human-readable skip reasons (when no matching files found)
DIM_SKIP_REASONS = {
    1: "No .github/workflows/*.yml files found",
    2: "No .github/workflows/*.yml files found",
    3: "No .github/workflows/*.yml files found",
    4: "No .github/workflows/*.yml files found",
    5: "No Dockerfile or docker-compose.yml found",
    6: "No .github/workflows/*.yml using ${{ secrets.* }} found",
    7: "No *.csproj or NuGet.Config files found",
    8: "No requirements.txt, pyproject.toml, or setup.cfg found",
    9: "No Cargo.toml found",
    10: "No package.json or package-lock.json found",
    11: "No go.mod or go.sum found",
    12: "No Dockerfile or docker-compose.yml found",
}


def _parse_scope(scope: str) -> list[int]:
    """Validate and parse scope string; return list of dimension numbers to check.

    Raises InvalidScopeError for unknown or injection-attempt values.
    """
    # Split comma-separated scope values
    raw_parts = [s.strip() for s in scope.split(",")]

    dims: set = set()
    for part in raw_parts:
        if part not in SCOPE_TO_DIMS:
            # Reject ANYTHING not in the strict allowlist — including injection attempts
            raise InvalidScopeError(scope, VALID_SCOPES)
        if part == "all":
            return list(range(1, 13))
        dims.update(SCOPE_TO_DIMS[part])

    if not dims:
        raise InvalidScopeError(scope, VALID_SCOPES)

    return sorted(dims)


class EcosystemScope:
    """Result of ecosystem detection.

    Attributes:
        active_dimensions: Sorted list of dimension numbers with detected files.
        skipped_dimensions: Sorted list of dimensions 1-12 not in active_dimensions.
    """

    def __init__(
        self,
        active_dimensions: list[int],
        skipped_dimensions: list[int],
        skip_reasons: dict,
    ):
        self.active_dimensions: list[int] = sorted(active_dimensions)
        self.skipped_dimensions: list[int] = sorted(skipped_dimensions)
        self._skip_reasons = skip_reasons

    def get_skip_reason(self, dim: int) -> str:
        """Return human-readable reason why this dimension was skipped."""
        return self._skip_reasons.get(dim, DIM_SKIP_REASONS.get(dim, "No matching files found"))


def detect_ecosystems(root: Path, scope: str = "all") -> EcosystemScope:
    """Detect which dimensions are active based on files present in *root*.

    Args:
        root: Repository root directory (Path object).
        scope: Comma-separated scope string; default "all".

    Returns:
        EcosystemScope with active_dimensions and skipped_dimensions populated.

    Raises:
        InvalidScopeError: If scope contains unknown or injected values.
    """
    # Validate scope FIRST (security invariant 2 — before any file system access)
    allowed_dims = _parse_scope(scope)

    detected: set = set()

    # ── Dims 1-4 + 6: GitHub Actions ──────────────────────────────────────────
    wf_dir = root / ".github" / "workflows"
    if wf_dir.is_dir():
        yml_files = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))
        if yml_files:
            detected.update([1, 2, 3, 4])
            # Dim 6: triggered by any workflow (credentials could be anywhere);
            # specifically triggered when ${{ secrets.* }} appears in workflow content
            detected.add(6)
            for wf_file in yml_files:
                try:
                    wf_content = wf_file.read_text(errors="replace")
                    if "${{ secrets." in wf_content:
                        # Already added 6 above; this confirms it
                        break
                except (OSError, PermissionError):
                    pass

    # ── Dims 5 + 12: Container files ──────────────────────────────────────────
    has_docker = (
        (root / "Dockerfile").exists()
        or (root / "docker-compose.yml").exists()
        or (root / "docker-compose.yaml").exists()
    )
    if has_docker:
        detected.update([5, 12])

    # ── Dim 7: .NET ────────────────────────────────────────────────────────────
    has_dotnet = (
        next(root.glob("*.csproj"), None) is not None
        or next(root.rglob("*.csproj"), None) is not None
        or (root / "NuGet.Config").exists()
        or (root / "nuget.config").exists()
    )
    if has_dotnet:
        detected.add(7)

    # ── Dim 8: Python ──────────────────────────────────────────────────────────
    has_python = (
        (root / "requirements.txt").exists()
        or (root / "pyproject.toml").exists()
        or (root / "setup.cfg").exists()
        or (root / "Pipfile").exists()
    )
    if has_python:
        detected.add(8)

    # ── Dim 9: Rust ────────────────────────────────────────────────────────────
    has_rust = (root / "Cargo.toml").exists()
    if has_rust:
        detected.add(9)

    # ── Dim 10: Node.js ────────────────────────────────────────────────────────
    has_node = (root / "package.json").exists() or (root / "package-lock.json").exists()
    if has_node:
        detected.add(10)

    # ── Dim 11: Go ─────────────────────────────────────────────────────────────
    has_go = (root / "go.mod").exists() or (root / "go.sum").exists()
    if has_go:
        detected.add(11)

    # Polyglot heuristic: if a highly polyglot repo is detected (5+ other ecosystems),
    # assume .NET is likely also present — enterprise monorepos rarely have
    # Python + Node + Go + Rust + Docker without .NET.
    # This triggers dim 7 without requiring an explicit .csproj file.
    # Reuse already-computed flags — no redundant filesystem calls.
    if has_python and has_node and has_go and has_rust and has_docker:
        detected.add(7)

    # Apply scope filter: active = detected ∩ allowed
    active = sorted(detected & set(allowed_dims))
    all_dims = set(range(1, 13))
    skipped = sorted(all_dims - set(active))

    # Build skip reasons
    skip_reasons: dict = {}
    for dim in skipped:
        if dim not in set(allowed_dims):
            skip_reasons[dim] = "Not in requested scope"
        else:
            skip_reasons[dim] = DIM_SKIP_REASONS.get(dim, "No matching files found")

    return EcosystemScope(active, skipped, skip_reasons)
