# File: supply_chain_audit/checkers/dotnet.py
"""Dimension 7: NuGet/.NET dependency integrity checks."""

import re
from pathlib import Path

from ..schema import Finding
from ._utils import _relative_path


def check_nuget_lock(root: Path) -> list[Finding]:
    """Dim 7: Check NuGet lock files, locked-mode, and source mapping.

    Findings:
    - High: .csproj present without packages.lock.json (no lock file)
    - High: NuGet.Config with multiple sources but no packageSourceMapping (dependency confusion)
    - Medium: NuGet.Config with external source without <clear /> (scope risk)
    - Info: RestoreLockedMode not set in .csproj
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    # Find .csproj files
    csproj_files = list(root.rglob("*.csproj"))

    for csproj in csproj_files:
        rel = _relative_path(root, csproj)
        proj_dir = csproj.parent

        # Check for packages.lock.json in project dir or repo root
        has_lock = (proj_dir / "packages.lock.json").exists() or (
            root / "packages.lock.json"
        ).exists()

        if not has_lock:
            counters["High"] += 1
            seq = str(counters["High"]).zfill(3)
            findings.append(
                Finding(
                    id=f"HIGH-{seq}",
                    dimension=7,
                    severity="High",
                    file=rel,
                    line=0,  # file-level finding
                    current_value=f"No packages.lock.json found for {csproj.name}",
                    expected_value=(
                        "Add to .csproj: <RestoreLockedMode>true</RestoreLockedMode>\n"
                        "Run: dotnet restore --locked-mode to generate packages.lock.json"
                    ),
                    rationale=(
                        "Without a lock file, NuGet resolves to the latest compatible version "
                        "on each restore, enabling silent dependency substitution attacks."
                    ),
                    offline_detectable=True,
                )
            )

        # Check RestoreLockedMode
        try:
            csproj_content = csproj.read_text(errors="replace")
            if "RestoreLockedMode" not in csproj_content:
                counters["Info"] += 1
                seq = str(counters["Info"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"INFO-{seq}",
                        dimension=7,
                        severity="Info",
                        file=rel,
                        line=0,
                        current_value="RestoreLockedMode not set",
                        expected_value="<RestoreLockedMode>true</RestoreLockedMode>",
                        rationale=(
                            "Add RestoreLockedMode=true to enforce lock file usage in CI. "
                            "Prevents accidental resolution of newer versions."
                        ),
                        offline_detectable=True,
                    )
                )
        except (OSError, PermissionError):
            pass

    # Check NuGet.Config
    for nuget_config_name in ("NuGet.Config", "nuget.config", "NuGet.config"):
        nuget_config = root / nuget_config_name
        if nuget_config.exists():
            rel = _relative_path(root, nuget_config)
            try:
                cfg_content = nuget_config.read_text(errors="replace")
            except (OSError, PermissionError):
                continue

            has_clear = "<clear" in cfg_content.lower()
            has_pkg_source_mapping = "packagesourcemapping" in cfg_content.lower()
            # Count external sources (nuget.org or non-internal)
            source_adds = re.findall(r"<add\s+key=", cfg_content, re.IGNORECASE)
            has_multiple_sources = len(source_adds) > 1

            if has_multiple_sources and not has_pkg_source_mapping:
                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=7,
                        severity="High",
                        file=rel,
                        line=1,
                        current_value=f"NuGet.Config has {len(source_adds)} sources without packageSourceMapping",
                        expected_value=(
                            "Add <packageSourceMapping> to map packages to specific sources:\n"
                            "  <packageSourceMapping>\n"
                            "    <packageSource key='internal'><package pattern='*' /></packageSource>\n"
                            "  </packageSourceMapping>"
                        ),
                        rationale=(
                            "Multiple NuGet sources without packageSourceMapping enables "
                            "dependency confusion attacks — an attacker can publish a higher-versioned "
                            "package on nuget.org to override internal packages."
                        ),
                        offline_detectable=True,
                    )
                )

            if not has_clear and has_multiple_sources:
                counters["Medium"] += 1
                seq = str(counters["Medium"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"MEDIUM-{seq}",
                        dimension=7,
                        severity="Medium",
                        file=rel,
                        line=1,
                        current_value="NuGet.Config missing <clear /> before source list",
                        expected_value=(
                            "<packageSources><clear /><add key='internal' value='...' /></packageSources>"
                        ),
                        rationale=(
                            "Without <clear />, machine-level NuGet sources (including nuget.org) "
                            "are inherited and may resolve packages from unintended sources."
                        ),
                        offline_detectable=True,
                    )
                )
            break  # Only process the first NuGet.Config found

    return findings
