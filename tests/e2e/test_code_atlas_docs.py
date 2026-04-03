"""Playwright E2E tests for the Code Atlas documentation pages.

Verifies:
1. Atlas index page loads with a readable layer overview table
2. All 8 layer sub-pages are reachable from the index
3. Nav sidebar links to sub-pages return 200 (no 404s)
4. Cross-reference links within sub-pages resolve correctly

Requires: mkdocs site built to site/ and served on localhost.
Usage:
    # Build and serve:
    uv run mkdocs build && python3 -m http.server 8123 --directory site
    # Run tests:
    uv run python -m pytest tests/e2e/test_code_atlas_docs.py -v
"""

import pytest

BASE_URL = "http://127.0.0.1:8123"

ATLAS_LAYERS = [
    "repo-surface",
    "ast-lsp-bindings",
    "compile-deps",
    "runtime-topology",
    "api-contracts",
    "data-flow",
    "service-components",
    "user-journeys",
]

LAYER_NAMES = [
    "Repository Surface",
    "AST + LSP Bindings",
    "Compile-time Dependencies",
    "Runtime Topology",
    "API Contracts",
    "Data Flow",
    "Service Components",
    "User Journeys",
]


class TestAtlasIndexPage:
    """Tests for the main atlas index page."""

    def test_index_page_loads(self, page):
        """Atlas index page returns 200 and has correct title."""
        response = page.goto(f"{BASE_URL}/atlas/index.html")
        assert response.status == 200
        assert "Code Atlas" in page.title() or "Code Atlas" in page.content()

    def test_index_has_layer_table(self, page):
        """Index page renders a table with all 8 layers."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        tables = page.locator("table")
        assert tables.count() >= 1, "No tables found on index page"

        # The first table should be the layer overview
        first_table = tables.first
        rows = first_table.locator("tbody tr")
        assert rows.count() >= 8, f"Expected 8+ layer rows, found {rows.count()}"

    def test_index_has_layer_links(self, page):
        """Each layer row has a clickable link to its sub-page."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        # All links to layer sub-pages in the first table
        layer_links = page.locator("table").first.locator("a")
        assert layer_links.count() >= 8, f"Expected 8+ layer links, found {layer_links.count()}"

    def test_index_layer_names_readable(self, page):
        """Each layer has readable name text, not raw markdown."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        content = page.text_content("body")

        for name in LAYER_NAMES:
            assert name in content, f"Missing layer text: {name}"

    def test_index_no_raw_markdown(self, page):
        """Index page should not show raw markdown artifacts."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        content = page.text_content("body")
        # Material icon shortcodes should be rendered as SVGs, not raw text
        assert ":material-folder-outline:" not in content, "Material icon shortcodes not rendered"

    def test_languages_table_readable(self, page):
        """The languages table renders with Python row."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        content = page.text_content("body")
        assert "Python" in content
        # Verify a numeric code line count is present (exact value varies with atlas rebuilds)
        assert (
            "120,895" in content
            or "745,870" in content
            or "120895" in content
            or "745870" in content
        )

    def test_layer_links_have_correct_hrefs(self, page):
        """Layer links point to the correct sub-page paths."""
        page.goto(f"{BASE_URL}/atlas/index.html")
        layer_table = page.locator("table").first
        links = layer_table.locator("a")

        hrefs = []
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if href:
                hrefs.append(href)

        # Each layer slug should appear in at least one href
        for layer in ATLAS_LAYERS:
            assert any(layer in h for h in hrefs), f"No link found for layer {layer}"


class TestAtlasSubPages:
    """Tests for the 8 layer sub-pages."""

    @pytest.mark.parametrize("layer", ATLAS_LAYERS)
    def test_subpage_loads(self, page, layer):
        """Each layer sub-page returns 200."""
        response = page.goto(f"{BASE_URL}/atlas/{layer}/index.html")
        assert response.status == 200, f"Layer {layer} returned {response.status}"

    @pytest.mark.parametrize("layer", ATLAS_LAYERS)
    def test_subpage_has_heading(self, page, layer):
        """Each sub-page has an h1 heading."""
        page.goto(f"{BASE_URL}/atlas/{layer}/index.html")
        h1 = page.locator("h1")
        assert h1.count() > 0, f"Layer {layer} page has no h1"
        assert h1.first.text_content().strip() != "", f"Layer {layer} h1 is empty"

    @pytest.mark.parametrize("layer", ATLAS_LAYERS)
    def test_subpage_has_breadcrumb(self, page, layer):
        """Each sub-page has breadcrumb navigation back to atlas root."""
        page.goto(f"{BASE_URL}/atlas/{layer}/index.html")
        breadcrumb = page.locator(".atlas-breadcrumb")
        assert breadcrumb.count() > 0, f"Layer {layer} missing breadcrumb nav"


class TestAtlasNavigation:
    """Tests for navigation between atlas pages."""

    def test_index_links_resolve_to_subpages(self, page):
        """Links on the index page navigate to sub-pages without 404."""
        page.goto(f"{BASE_URL}/atlas/index.html")

        layer_table = page.locator("table").first
        links = layer_table.locator("a")

        # Collect all hrefs first (before navigating away)
        hrefs = []
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if href:
                hrefs.append(href)

        assert len(hrefs) >= 8, f"Expected 8+ layer links, found {len(hrefs)}"

        # Now navigate to each
        for href in hrefs:
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"{BASE_URL}{href}"
            else:
                url = f"{BASE_URL}/atlas/{href}"

            resp = page.goto(url)
            assert resp.status == 200, f"Link {href} returned {resp.status}"

    @pytest.mark.parametrize("layer", ATLAS_LAYERS)
    def test_crossref_links_resolve(self, page, layer):
        """Cross-reference links in sub-pages resolve to valid pages."""
        page.goto(f"{BASE_URL}/atlas/{layer}/index.html")

        crossref = page.locator(".atlas-crossref a")
        count = crossref.count()
        if count == 0:
            pytest.skip(f"Layer {layer} has no cross-references")

        # Collect all hrefs first before navigating
        hrefs = []
        for i in range(count):
            href = crossref.nth(i).get_attribute("href")
            if href:
                hrefs.append(href)

        # Now navigate to each collected href
        for href in hrefs:
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"{BASE_URL}{href}"
            else:
                url = f"{BASE_URL}/atlas/{layer}/{href}"

            resp = page.goto(url)
            assert resp.status == 200, f"Cross-ref {href} from {layer} returned {resp.status}"


class TestAtlasHealthAndGlossary:
    """Tests for supplementary atlas pages."""

    def test_health_page_loads(self, page):
        response = page.goto(f"{BASE_URL}/atlas/health/index.html")
        assert response.status == 200
        assert "Health" in page.text_content("h1")

    def test_glossary_page_loads(self, page):
        response = page.goto(f"{BASE_URL}/atlas/glossary/index.html")
        assert response.status == 200
        assert "Glossary" in page.text_content("h1")
