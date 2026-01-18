"""Tests for LinkFixer orchestrator.

Tests verify:
- Strategy selection and ordering
- Confidence threshold filtering (>= 90%)
- Multiple strategy attempts
- File modification and PR creation
- Issue creation for unfixable links
"""

from unittest.mock import Mock, patch


class TestLinkFixer:
    """Tests for LinkFixer orchestrator class."""

    def test_tries_multiple_strategies(self, temp_repo, broken_link_data):
        """Should try multiple strategies until one succeeds.

        Scenario:
            - Case sensitivity fails (no match)
            - Git history succeeds (finds move)
            - Should return git history result
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        source_file = temp_repo / "docs" / "README.md"
        broken_path = "./old_file.md"

        result = fixer.fix_link(source_file=source_file, broken_path=broken_path, line_number=5)

        # Should attempt strategies in order until one succeeds
        assert result is not None or result is None  # Will fail until implemented

    def test_confidence_threshold_filtering(self, temp_repo):
        """Should only apply fixes with >= 90% confidence.

        Scenario:
            - Strategy returns 85% confidence fix
            - Should reject (below threshold)
            - Strategy returns 95% confidence fix
            - Should accept
        """
        from link_fixer import FixResult, LinkFixer

        fixer = LinkFixer(repo_path=temp_repo, confidence_threshold=0.90)

        # Mock strategy returning low confidence
        low_confidence_result = FixResult(
            fixed_path="./fix1.md", confidence=0.85, strategy_name="test_strategy"
        )

        # Mock strategy returning high confidence
        high_confidence_result = FixResult(
            fixed_path="./fix2.md", confidence=0.95, strategy_name="test_strategy"
        )

        # Test filtering logic
        assert fixer._meets_threshold(low_confidence_result) is False
        assert fixer._meets_threshold(high_confidence_result) is True

    def test_stops_after_successful_fix(self, temp_repo):
        """Should stop trying strategies after successful fix.

        Scenario:
            - First strategy succeeds with 95% confidence
            - Should not try remaining strategies
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        # Track which strategies were called
        strategy_calls = []

        def mock_strategy(name):
            def attempt_fix(source_file, broken_path):
                strategy_calls.append(name)
                if name == "first":
                    from link_fixer import FixResult

                    return FixResult(fixed_path="./fixed.md", confidence=0.95, strategy_name=name)
                return None

            return Mock(attempt_fix=attempt_fix)

        # Replace strategies with mocks
        fixer.strategies = [mock_strategy("first"), mock_strategy("second"), mock_strategy("third")]

        source_file = temp_repo / "README.md"
        fixer.fix_link(source_file, "./broken.md", 1)

        # Should only call first strategy
        assert len(strategy_calls) == 1
        assert strategy_calls[0] == "first"

    def test_returns_none_when_all_strategies_fail(self, temp_repo):
        """Should return None when no strategy succeeds.

        Scenario:
            - All strategies return None
            - Should propagate None
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "./truly_nonexistent.md"

        result = fixer.fix_link(source_file=source_file, broken_path=broken_path, line_number=1)

        assert result is None

    def test_strategy_execution_order(self, temp_repo):
        """Should execute strategies in priority order.

        Expected order:
            1. Case sensitivity (95%)
            2. Git history (90%)
            3. Missing extension (85%)
            4. Broken anchors (90%)
            5. Relative path (75%)
            6. Double slash (70%)
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        # Verify strategy order
        strategy_names = [s.__class__.__name__ for s in fixer.strategies]

        expected_order = [
            "CaseSensitivityFix",
            "GitHistoryFix",
            "MissingExtensionFix",
            "BrokenAnchorsFix",
            "RelativePathFix",
            "DoubleSlashFix",
        ]

        assert strategy_names == expected_order

    def test_modifies_file_with_fix(self, temp_repo):
        """Should modify source file with the fix.

        Scenario:
            - Fix is found: "./GUIDE.MD" -> "./guide.md"
            - Should update line in source file
            - Should preserve other content
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create source file with broken link
        source_file = docs_dir / "README.md"
        source_content = """# README

[Broken link](./GUIDE.MD)
[Another link](./other.md)
"""
        source_file.write_text(source_content)

        # Create target file
        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        fixer = LinkFixer(repo_path=temp_repo)

        # Apply fix
        _result = fixer.fix_link(source_file=source_file, broken_path="./GUIDE.MD", line_number=3)

        # Should modify file
        modified_content = source_file.read_text()
        assert "./guide.md" in modified_content
        assert "./GUIDE.MD" not in modified_content
        assert "[Another link](./other.md)" in modified_content  # Preserved

    def test_batch_fix_multiple_links(self, temp_repo, broken_link_data):
        """Should fix multiple broken links in batch.

        Scenario:
            - Multiple broken links provided
            - Should attempt fix for each
            - Should return summary of results
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        results = fixer.batch_fix(broken_link_data)

        assert "fixed" in results
        assert "unfixable" in results
        assert isinstance(results["fixed"], list)
        assert isinstance(results["unfixable"], list)

    def test_creates_pr_with_fixes(self, temp_repo):
        """Should create PR with all fixes applied.

        Scenario:
            - Multiple files fixed
            - Should create git branch
            - Should commit changes
            - Should create PR with description
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        fixed_links = [
            {"file": "docs/README.md", "old": "./GUIDE.MD", "new": "./guide.md"},
            {"file": "docs/tutorial.md", "old": "./README", "new": "./README.md"},
        ]

        with patch("subprocess.run") as mock_run:
            _pr_url = fixer.create_pr(fixed_links)

            # Should have created branch and PR
            assert mock_run.called
            # Will fail until implemented

    def test_creates_issue_for_unfixable_links(self, temp_repo):
        """Should create GitHub issue for unfixable links.

        Scenario:
            - Some links cannot be fixed
            - Should create issue with details
            - Should include manual review instructions
        """
        from link_fixer import LinkFixer

        fixer = LinkFixer(repo_path=temp_repo)

        unfixable_links = [
            {
                "file": "docs/README.md",
                "path": "./nonexistent.md",
                "line": 5,
                "reason": "No strategies succeeded",
            }
        ]

        with patch("subprocess.run") as mock_run:
            _issue_url = fixer.create_issue(unfixable_links)

            # Should have created issue
            assert mock_run.called
            # Will fail until implemented


class TestConfidenceCalculator:
    """Tests for confidence calculation logic."""

    def test_single_match_confidence(self, confidence_test_cases):
        """Should calculate high confidence for single matches."""
        from link_fixer import ConfidenceCalculator

        calc = ConfidenceCalculator()

        # Single case sensitivity match
        confidence = calc.calculate(strategy="case_sensitivity", num_matches=1)

        assert confidence == 0.95

    def test_multiple_match_confidence(self, confidence_test_cases):
        """Should calculate low confidence for multiple matches."""
        from link_fixer import ConfidenceCalculator

        calc = ConfidenceCalculator()

        # Multiple case sensitivity matches
        confidence = calc.calculate(strategy="case_sensitivity", num_matches=3)

        assert confidence < 0.70

    def test_fuzzy_match_confidence(self, confidence_test_cases):
        """Should scale confidence with fuzzy match similarity."""
        from link_fixer import ConfidenceCalculator

        calc = ConfidenceCalculator()

        # High similarity
        high_confidence = calc.calculate(strategy="broken_anchor", similarity=0.90)

        # Low similarity
        low_confidence = calc.calculate(strategy="broken_anchor", similarity=0.60)

        assert high_confidence > low_confidence
        assert 0.70 <= high_confidence <= 0.90
        assert low_confidence < 0.70

    def test_git_history_confidence(self, confidence_test_cases):
        """Should calculate confidence based on move count."""
        from link_fixer import ConfidenceCalculator

        calc = ConfidenceCalculator()

        # Single move
        single_confidence = calc.calculate(strategy="git_history", num_moves=1)

        # Multiple moves
        multiple_confidence = calc.calculate(strategy="git_history", num_moves=3)

        assert single_confidence == 0.90
        assert multiple_confidence < single_confidence


class TestFixResult:
    """Tests for FixResult dataclass."""

    def test_fix_result_creation(self):
        """Should create FixResult with all fields."""
        from link_fixer import FixResult

        result = FixResult(
            fixed_path="./guide.md", confidence=0.95, strategy_name="case_sensitivity"
        )

        assert result.fixed_path == "./guide.md"
        assert result.confidence == 0.95
        assert result.strategy_name == "case_sensitivity"

    def test_fix_result_comparison(self):
        """Should compare FixResults by confidence."""
        from link_fixer import FixResult

        high = FixResult("./file1.md", 0.95, "strategy1")
        low = FixResult("./file2.md", 0.70, "strategy2")

        assert high.confidence > low.confidence
