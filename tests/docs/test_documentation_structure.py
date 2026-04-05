"""
Documentation Structure Validation Tests (TDD Approach)

These tests verify the documentation reorganization is successful following TDD methodology.
Tests should FAIL before reorganization and PASS after.

Testing pyramid:
- 60% Unit tests (link validation, orphan detection)
- 30% Integration tests (navigation depth, coverage)
- 10% E2E tests (complete user journeys)

Philosophy:
- No stubs or placeholders
- Fast execution (< 10 seconds total)
- Clear failure messages
- Reusable for future validation
"""

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pytest
import yaml


FENCED_CODE_BLOCK_RE = re.compile(
    r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^\s*(?P=fence)\s*$"
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\[([^\]]+)\]:\s*(.+)$", re.MULTILINE)
PLACEHOLDER_LINK_RE = re.compile(r"^\{[^}]+\}$")
IGNORED_LINK_TARGETS = {"link", "url", "{url}", "{homepageUrl}", "{pr_url}", "{docs_url}"}
FILESYSTEM_LINK_PREFIXES = ("~/", "/Users/", "/home/")


def _strip_non_navigational_content(content: str) -> str:
    """Remove content that can contain example-only links."""
    content = FENCED_CODE_BLOCK_RE.sub("", content)
    content = HTML_COMMENT_RE.sub("", content)
    return content


def _extract_markdown_links(content: str) -> list[str]:
    """Extract markdown links after removing non-navigational content."""
    cleaned = _strip_non_navigational_content(content)
    inline_links = INLINE_LINK_RE.findall(cleaned)
    reference_links = REFERENCE_LINK_RE.findall(cleaned)
    return [link for _, link in inline_links + reference_links]


def _normalize_link_target(link: str) -> str:
    """Normalize a link target for resolution checks."""
    return link.strip().removeprefix("<").removesuffix(">")


def _should_skip_link_target(link: str) -> bool:
    """Skip placeholder or environment-specific links that are not publishable docs targets."""
    normalized_link = _normalize_link_target(link)
    if normalized_link.startswith(("http://", "https://", "mailto:", "#")):
        return True
    if normalized_link.startswith(FILESYSTEM_LINK_PREFIXES):
        return True
    if normalized_link in IGNORED_LINK_TARGETS:
        return True
    return bool(PLACEHOLDER_LINK_RE.fullmatch(normalized_link))


def _resolve_existing_markdown_target(target: Path) -> Path:
    """Resolve directory targets to README.md or index.md when present."""
    if target.is_dir():
        for candidate_name in ("README.md", "index.md"):
            candidate = target / candidate_name
            if candidate.exists():
                return candidate
    return target


def _extract_mkdocs_nav_text(config_path: Path) -> str | None:
    """Extract the nav block from mkdocs.yml so it can be parsed independently."""
    if not config_path.exists():
        return None

    lines = config_path.read_text(encoding="utf-8").splitlines()
    nav_start = next((i for i, line in enumerate(lines) if line.startswith("nav:")), None)
    if nav_start is None:
        return None

    nav_end = len(lines)
    for i, line in enumerate(lines[nav_start + 1 :], nav_start + 1):
        if line and not line.startswith((" ", "#")):
            nav_end = i
            break

    return "\n".join(lines[nav_start:nav_end])


@lru_cache(maxsize=4)
def _load_mkdocs_nav_docs(docs_dir: Path) -> tuple[Path, ...]:
    """Return the markdown documents that are part of the published MkDocs site."""
    nav_text = _extract_mkdocs_nav_text(docs_dir.parent / "mkdocs.yml")
    if not nav_text:
        return ()

    nav_block = yaml.safe_load(nav_text) or {}
    nav = nav_block.get("nav", [])
    docs: set[Path] = set()

    def walk(node: object) -> None:
        if isinstance(node, str):
            if node.endswith(".md"):
                candidate = (docs_dir / node).resolve()
                if candidate.exists():
                    docs.add(candidate)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    walk(nav)
    return tuple(sorted(docs))


def _find_published_docs(docs_dir: Path) -> list[Path]:
    """Use MkDocs navigation as the source of truth when available."""
    published_docs = list(_load_mkdocs_nav_docs(docs_dir))
    if published_docs:
        return published_docs
    return list(docs_dir.rglob("*.md"))


def _resolve_internal_link(source_file: Path, docs_dir: Path, link: str) -> Path:
    """Resolve an internal docs link to a repository path."""
    if link.startswith("/"):
        if link.startswith("/.claude/"):
            target = Path(docs_dir.parent) / link.lstrip("/")
        else:
            target = docs_dir / link.lstrip("/")
    else:
        target = (source_file.parent / link).resolve()
    return _resolve_existing_markdown_target(target)


class DocLinkValidator:
    """Validates all links in documentation files."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.all_docs = set(self._find_all_docs())
        self.broken_links: list[tuple[Path, str, str]] = []

    def _find_all_docs(self) -> list[Path]:
        """Find all markdown files in docs directory."""
        return _find_published_docs(self.docs_dir)

    def _extract_links(self, content: str) -> list[str]:
        """Extract all markdown links from content."""
        return _extract_markdown_links(content)

    def _resolve_link(self, source_file: Path, link: str) -> tuple[bool, str]:
        """
        Resolve a link and check if target exists.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Skip external links
        normalized_link = _normalize_link_target(link)

        if _should_skip_link_target(normalized_link):
            return (True, "")

        # Remove anchor fragments
        link_without_anchor = normalized_link.split("#")[0]
        if not link_without_anchor:
            return (True, "")

        # Resolve relative path
        target = _resolve_internal_link(source_file, self.docs_dir, link_without_anchor)

        # Check if target exists
        if not target.exists():
            return (False, f"Target not found: {target}")

        return (True, "")

    def validate_all_links(self) -> dict[str, list[tuple[str, str]]]:
        """
        Validate all links in all documentation files.

        Returns:
            Dictionary mapping file paths to list of (broken_link, reason) tuples
        """
        broken_links_by_file = defaultdict(list)

        for doc_file in self.all_docs:
            content = doc_file.read_text(encoding="utf-8")
            links = self._extract_links(content)

            for link in links:
                is_valid, reason = self._resolve_link(doc_file, link)
                if not is_valid:
                    broken_links_by_file[str(doc_file)].append((link, reason))
                    self.broken_links.append((doc_file, link, reason))

        return dict(broken_links_by_file)

    def get_summary(self) -> str:
        """Get a human-readable summary of validation results."""
        if not self.broken_links:
            return f"✓ All links valid across {len(self.all_docs)} documents"

        summary = [f"✗ Found {len(self.broken_links)} broken links:", ""]
        for doc_file, link, reason in self.broken_links[:10]:  # Show first 10
            relative_path = doc_file.relative_to(self.docs_dir)
            summary.append(f"  {relative_path}")
            summary.append(f"    Link: {link}")
            summary.append(f"    Issue: {reason}")
            summary.append("")

        if len(self.broken_links) > 10:
            summary.append(f"  ... and {len(self.broken_links) - 10} more")

        return "\n".join(summary)


class OrphanDetector:
    """Detects documentation files not reachable from index.md."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.index_file = docs_dir / "index.md"
        self.reachable: set[Path] = set()
        self.all_docs = set(self._find_all_docs())

    def _find_all_docs(self) -> list[Path]:
        """Find all markdown files in docs directory."""
        return _find_published_docs(self.docs_dir)

    def _extract_internal_links(self, content: str) -> list[str]:
        """Extract internal (non-http) links from content."""
        all_links = _extract_markdown_links(content)

        # Filter to internal links only
        internal = []
        for link in all_links:
            normalized_link = _normalize_link_target(link)
            if not _should_skip_link_target(normalized_link):
                # Remove anchor fragments
                link_without_anchor = normalized_link.split("#")[0]
                if link_without_anchor:
                    internal.append(link_without_anchor)

        return internal

    def _resolve_link_to_file(self, source_file: Path, link: str) -> Path | None:
        """Resolve a link to an actual file path."""
        target = _resolve_internal_link(source_file, self.docs_dir, link)

        return target if target.exists() else None

    def build_link_graph(self) -> set[Path]:
        """
        Build graph of reachable documents starting from index.md.

        Returns:
            Set of reachable document paths
        """
        if not self.index_file.exists():
            return set()

        published_docs = _load_mkdocs_nav_docs(self.docs_dir)
        if published_docs:
            self.reachable = set(published_docs)
            return self.reachable

        to_visit = [self.index_file]
        visited = set()

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue

            visited.add(current)
            self.reachable.add(current)

            # Read content and extract links
            try:
                content = current.read_text(encoding="utf-8")
                links = self._extract_internal_links(content)

                for link in links:
                    target = self._resolve_link_to_file(current, link)
                    if target and target.suffix == ".md" and target not in visited:
                        to_visit.append(target)
            except Exception:
                # Skip files that can't be read
                continue

        return self.reachable

    def find_orphans(self) -> list[Path]:
        """
        Find documents not reachable from index.md.

        Returns:
            List of orphaned document paths
        """
        self.build_link_graph()
        orphans = []

        for doc in self.all_docs:
            # Only consider files in docs/ directory
            if self.docs_dir in doc.parents or doc.parent == self.docs_dir:
                if doc not in self.reachable:
                    orphans.append(doc)

        return sorted(orphans)

    def get_summary(self) -> str:
        """Get human-readable summary of orphan detection."""
        orphans = self.find_orphans()

        if not orphans:
            return f"✓ All {len(self.all_docs)} documents reachable from index.md"

        summary = [f"✗ Found {len(orphans)} orphaned documents:", ""]
        for orphan in orphans[:20]:  # Show first 20
            relative_path = orphan.relative_to(self.docs_dir.parent)
            summary.append(f"  {relative_path}")

        if len(orphans) > 20:
            summary.append(f"  ... and {len(orphans) - 20} more")

        return "\n".join(summary)


class CoverageChecker:
    """Checks that major feature categories have documentation."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.index_file = docs_dir / "index.md"

        # Major features that MUST be documented
        self.required_features = {
            "goal-seeking agents": [
                "goal_agent_generator",
                "GOAL_AGENT_GENERATOR",
                "autonomous agents",
            ],
            "workflows": ["DEFAULT_WORKFLOW", "INVESTIGATION_WORKFLOW", "workflow"],
            "agents": ["agents/amplihack", "architect", "builder", "tester"],
            "commands": ["/ultrathink", "/analyze", "/improve"],
            "memory": ["neo4j", "memory system", "agent memory"],
        }

    def check_coverage(self) -> dict[str, bool]:
        """
        Check if all major features are documented.

        Returns:
            Dictionary mapping feature name to whether it's covered
        """
        if not self.index_file.exists():
            return dict.fromkeys(self.required_features, False)

        index_content = self.index_file.read_text(encoding="utf-8").lower()

        coverage = {}
        for feature, keywords in self.required_features.items():
            # Check if any keyword appears in index
            covered = any(keyword.lower() in index_content for keyword in keywords)
            coverage[feature] = covered

        return coverage

    def get_summary(self) -> str:
        """Get human-readable coverage summary."""
        coverage = self.check_coverage()
        missing = [feature for feature, covered in coverage.items() if not covered]

        if not missing:
            return f"✓ All {len(self.required_features)} major features documented"

        summary = [f"✗ Missing documentation for {len(missing)} features:", ""]
        for feature in missing:
            summary.append(f"  - {feature}")

        return "\n".join(summary)


class NavigationDepthChecker:
    """Checks that all docs are reachable within 3 clicks from index."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.index_file = docs_dir / "index.md"
        self.depths: dict[Path, int] = {}

    def _extract_internal_links(self, content: str) -> list[str]:
        """Extract internal links from content."""
        all_links = _extract_markdown_links(content)

        internal = []
        for link in all_links:
            normalized_link = _normalize_link_target(link)
            if not _should_skip_link_target(normalized_link):
                link_without_anchor = normalized_link.split("#")[0]
                if link_without_anchor:
                    internal.append(link_without_anchor)

        return internal

    def _resolve_link_to_file(self, source_file: Path, link: str) -> Path | None:
        """Resolve a link to an actual file path."""
        target = _resolve_internal_link(source_file, self.docs_dir, link)

        return target if target.exists() and target.suffix == ".md" else None

    def calculate_depths(self, max_depth: int = 5) -> dict[Path, int]:
        """
        Calculate navigation depth for each document.

        Args:
            max_depth: Maximum depth to search (prevents infinite loops)

        Returns:
            Dictionary mapping document paths to their depth from index
        """
        if not self.index_file.exists():
            return {}

        self.depths = {self.index_file: 0}
        current_depth = 0
        current_level = {self.index_file}

        while current_level and current_depth < max_depth:
            next_level = set()

            for doc in current_level:
                try:
                    content = doc.read_text(encoding="utf-8")
                    links = self._extract_internal_links(content)

                    for link in links:
                        target = self._resolve_link_to_file(doc, link)
                        if target and target not in self.depths:
                            self.depths[target] = current_depth + 1
                            next_level.add(target)
                except Exception:
                    continue

            current_level = next_level
            current_depth += 1

        return self.depths

    def find_deep_docs(self, threshold: int = 3) -> list[tuple[Path, int]]:
        """
        Find documents deeper than threshold clicks from index.

        Args:
            threshold: Maximum acceptable depth

        Returns:
            List of (document_path, depth) tuples for docs beyond threshold
        """
        self.calculate_depths()

        published_docs = set(_load_mkdocs_nav_docs(self.docs_dir))
        deep_docs = [
            (doc, depth)
            for doc, depth in self.depths.items()
            if depth > threshold and (not published_docs or doc in published_docs)
        ]

        return sorted(deep_docs, key=lambda x: x[1], reverse=True)

    def get_summary(self, threshold: int = 3) -> str:
        """Get human-readable navigation depth summary."""
        deep_docs = self.find_deep_docs(threshold)

        if not deep_docs:
            total_docs = len(self.depths)
            return f"✓ All {total_docs} documents reachable within {threshold} clicks"

        summary = [f"✗ Found {len(deep_docs)} documents beyond {threshold} clicks:", ""]
        for doc, depth in deep_docs[:15]:
            relative_path = doc.relative_to(self.docs_dir.parent)
            summary.append(f"  [{depth} clicks] {relative_path}")

        if len(deep_docs) > 15:
            summary.append(f"  ... and {len(deep_docs) - 15} more")

        return "\n".join(summary)


# ============================================================================
# UNIT TESTS (60% - Fast, isolated)
# ============================================================================


class TestLinkValidation:
    """Unit tests for link validation."""

    @pytest.fixture
    def docs_dir(self):
        return Path(__file__).parent.parent.parent / "docs"

    def test_link_validator_initialization(self, docs_dir):
        """Test that link validator can be initialized."""
        validator = DocLinkValidator(docs_dir)
        assert validator.docs_dir == docs_dir
        assert len(validator.all_docs) > 0

    def test_extract_inline_links(self):
        """Test extraction of inline markdown links."""
        content = "[link1](file1.md) and [link2](file2.md)"
        validator = DocLinkValidator(Path("/tmp"))
        links = validator._extract_links(content)
        assert "file1.md" in links
        assert "file2.md" in links

    def test_extract_reference_links(self):
        """Test extraction of reference-style links."""
        content = "[link1]: file1.md\n[link2]: file2.md"
        validator = DocLinkValidator(Path("/tmp"))
        links = validator._extract_links(content)
        assert "file1.md" in links
        assert "file2.md" in links

    def test_skip_external_links(self):
        """Test that external links are considered valid."""
        validator = DocLinkValidator(Path("/tmp"))
        is_valid, _ = validator._resolve_link(Path("/tmp/test.md"), "https://example.com")
        assert is_valid is True

    def test_skip_anchor_only_links(self):
        """Test that anchor-only links are considered valid."""
        validator = DocLinkValidator(Path("/tmp"))
        is_valid, _ = validator._resolve_link(Path("/tmp/test.md"), "#section")
        assert is_valid is True


class TestOrphanDetection:
    """Unit tests for orphan detection."""

    @pytest.fixture
    def docs_dir(self):
        return Path(__file__).parent.parent.parent / "docs"

    def test_orphan_detector_initialization(self, docs_dir):
        """Test that orphan detector can be initialized."""
        detector = OrphanDetector(docs_dir)
        assert detector.docs_dir == docs_dir
        assert len(detector.all_docs) > 0

    def test_extract_internal_links_filters_external(self):
        """Test that external links are filtered out."""
        content = "[internal](file.md) [external](https://example.com)"
        detector = OrphanDetector(Path("/tmp"))
        links = detector._extract_internal_links(content)
        assert "file.md" in links
        assert "https://example.com" not in links

    def test_extract_internal_links_removes_anchors(self):
        """Test that anchor fragments are removed."""
        content = "[link](file.md#section)"
        detector = OrphanDetector(Path("/tmp"))
        links = detector._extract_internal_links(content)
        assert "file.md" in links
        assert "file.md#section" not in links


# ============================================================================
# INTEGRATION TESTS (30% - Multi-component)
# ============================================================================


class TestDocumentationIntegration:
    """Integration tests combining multiple validation components."""

    @pytest.fixture
    def docs_dir(self):
        return Path(__file__).parent.parent.parent / "docs"

    def test_link_validation_on_real_docs(self, docs_dir):
        """Test link validation on actual documentation."""
        validator = DocLinkValidator(docs_dir)
        broken_links = validator.validate_all_links()

        # This WILL fail before reorganization - that's expected!
        # After reorganization, all links should be valid
        summary = validator.get_summary()
        print(f"\n{summary}")

        # Strict test: no broken links allowed
        assert len(broken_links) == 0, f"Found broken links:\n{summary}"

    def test_orphan_detection_on_real_docs(self, docs_dir):
        """Test orphan detection on actual documentation."""
        detector = OrphanDetector(docs_dir)
        orphans = detector.find_orphans()

        summary = detector.get_summary()
        print(f"\n{summary}")

        # Strict test: no orphans allowed
        assert len(orphans) == 0, f"Found orphaned docs:\n{summary}"

    def test_feature_coverage(self, docs_dir):
        """Test that all major features are documented."""
        checker = CoverageChecker(docs_dir)
        coverage = checker.check_coverage()

        summary = checker.get_summary()
        print(f"\n{summary}")

        missing = [feature for feature, covered in coverage.items() if not covered]
        assert len(missing) == 0, f"Missing feature documentation:\n{summary}"

    def test_navigation_depth(self, docs_dir):
        """Test that all docs are within 3 clicks of index."""
        checker = NavigationDepthChecker(docs_dir)
        deep_docs = checker.find_deep_docs(threshold=3)

        summary = checker.get_summary()
        print(f"\n{summary}")

        assert len(deep_docs) == 0, f"Found docs too deep in navigation:\n{summary}"


# ============================================================================
# E2E TESTS (10% - Complete workflows)
# ============================================================================


class TestDocumentationE2E:
    """End-to-end tests for complete documentation validation."""

    @pytest.fixture
    def docs_dir(self):
        return Path(__file__).parent.parent.parent / "docs"

    def test_complete_documentation_health(self, docs_dir):
        """
        Complete validation of documentation structure.

        This is the main E2E test that validates:
        1. All links are valid
        2. No orphaned documents
        3. All major features covered
        4. Navigation depth acceptable
        """
        results = {"links": None, "orphans": None, "coverage": None, "depth": None}

        # Run all validators
        link_validator = DocLinkValidator(docs_dir)
        results["links"] = link_validator.validate_all_links()

        orphan_detector = OrphanDetector(docs_dir)
        results["orphans"] = orphan_detector.find_orphans()

        coverage_checker = CoverageChecker(docs_dir)
        coverage = coverage_checker.check_coverage()
        results["coverage"] = [f for f, c in coverage.items() if not c]

        depth_checker = NavigationDepthChecker(docs_dir)
        results["depth"] = depth_checker.find_deep_docs(threshold=3)

        # Generate comprehensive report
        report = [
            "\n" + "=" * 70,
            "DOCUMENTATION HEALTH REPORT",
            "=" * 70,
            "",
            link_validator.get_summary(),
            "",
            orphan_detector.get_summary(),
            "",
            coverage_checker.get_summary(),
            "",
            depth_checker.get_summary(),
            "",
            "=" * 70,
        ]

        print("\n".join(report))

        # All checks must pass
        failures = []
        if results["links"]:
            failures.append(f"Found {len(results['links'])} files with broken links")
        if results["orphans"]:
            failures.append(f"Found {len(results['orphans'])} orphaned documents")
        if results["coverage"]:
            failures.append(f"Missing coverage for: {', '.join(results['coverage'])}")
        if results["depth"]:
            failures.append(f"Found {len(results['depth'])} documents beyond navigation depth")

        assert not failures, "Documentation health check failed:\n" + "\n".join(
            f"  - {f}" for f in failures
        )

    def test_user_journey_new_user(self, docs_dir):
        """
        Test new user journey: landing page → quick start → first feature.

        Validates that a new user can navigate from index.md to implementing
        their first feature without broken links.
        """
        index = docs_dir / "index.md"
        assert index.exists(), "index.md must exist"

        content = index.read_text(encoding="utf-8")

        # New user journey requirements
        required_paths = ["Get Started", "Quick Start", "Prerequisites", "Installation"]

        missing = []
        for path in required_paths:
            if path.lower() not in content.lower():
                missing.append(path)

        assert not missing, f"New user journey incomplete. Missing: {', '.join(missing)}"

    def test_user_journey_goal_seeking_agents(self, docs_dir):
        """
        Test specific user request: finding goal-seeking agent documentation.

        User's explicit requirement: "goal-seeking agents are linked"
        """
        index = docs_dir / "index.md"
        assert index.exists(), "index.md must exist"

        content = index.read_text(encoding="utf-8")

        # Must be directly linked from index (user's explicit requirement)
        assert "goal" in content.lower(), "Goal-seeking agents not mentioned in index.md"
        assert "autonomous" in content.lower() or "iterate" in content.lower(), (
            "Goal-seeking agent characteristics not described"
        )

        # Extract links to goal-related docs
        goal_links = [
            link
            for link in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            if "goal" in link[0].lower() or "goal" in link[1].lower()
        ]

        assert len(goal_links) > 0, "No direct links to goal-seeking agent documentation"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
