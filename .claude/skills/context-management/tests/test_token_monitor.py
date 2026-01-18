"""Unit tests for TokenMonitor brick."""

import pytest

from context_management.token_monitor import DEFAULT_MAX_TOKENS, TokenMonitor


class TestTokenMonitor:
    """Test suite for TokenMonitor class."""

    def test_initialization_default(self):
        """Test TokenMonitor initializes with default values."""
        monitor = TokenMonitor()
        assert monitor.max_tokens == DEFAULT_MAX_TOKENS
        assert monitor.current_usage == 0

    def test_initialization_custom(self):
        """Test TokenMonitor initializes with custom max_tokens."""
        monitor = TokenMonitor(max_tokens=500_000)
        assert monitor.max_tokens == 500_000

    def test_check_usage_ok_threshold(self):
        """Test usage check at 50% (OK threshold)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(450_000)

        assert stats.current_tokens == 450_000
        assert stats.percentage == 45.0
        assert stats.threshold_status == "ok"
        assert "healthy" in stats.recommendation.lower()

    def test_check_usage_consider_threshold(self):
        """Test usage check at 70% (consider threshold)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(750_000)

        assert stats.current_tokens == 750_000
        assert stats.percentage == 75.0
        assert stats.threshold_status == "consider"
        assert "consider" in stats.recommendation.lower()

    def test_check_usage_recommended_threshold(self):
        """Test usage check at 85% (recommended threshold)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(870_000)

        assert stats.current_tokens == 870_000
        assert stats.percentage == 87.0
        assert stats.threshold_status == "recommended"
        assert "recommended" in stats.recommendation.lower()

    def test_check_usage_urgent_threshold(self):
        """Test usage check at 95% (urgent threshold)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(960_000)

        assert stats.current_tokens == 960_000
        assert stats.percentage == 96.0
        assert stats.threshold_status == "urgent"
        assert "urgent" in stats.recommendation.lower()

    def test_check_usage_zero_tokens(self):
        """Test usage check with zero tokens (edge case)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(0)

        assert stats.current_tokens == 0
        assert stats.percentage == 0.0
        assert stats.threshold_status == "ok"

    def test_check_usage_max_tokens(self):
        """Test usage check at exactly max tokens (edge case)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(1_000_000)

        assert stats.current_tokens == 1_000_000
        assert stats.percentage == 100.0
        assert stats.threshold_status == "urgent"

    def test_check_usage_over_max(self):
        """Test usage check above max tokens (edge case)."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(1_100_000)

        assert stats.current_tokens == 1_100_000
        assert stats.percentage == 110.0
        assert stats.threshold_status == "urgent"

    def test_get_recommendation_low_usage(self):
        """Test recommendation for low usage."""
        monitor = TokenMonitor()
        rec = monitor.get_recommendation(30.0)
        assert "healthy" in rec.lower()

    def test_get_recommendation_medium_usage(self):
        """Test recommendation for medium usage."""
        monitor = TokenMonitor()
        rec = monitor.get_recommendation(72.0)
        assert "consider" in rec.lower()

    def test_get_recommendation_high_usage(self):
        """Test recommendation for high usage."""
        monitor = TokenMonitor()
        rec = monitor.get_recommendation(88.0)
        assert "recommended" in rec.lower()

    def test_get_recommendation_critical_usage(self):
        """Test recommendation for critical usage."""
        monitor = TokenMonitor()
        rec = monitor.get_recommendation(97.0)
        assert "urgent" in rec.lower()

    def test_get_tokens_until_threshold_consider(self):
        """Test tokens remaining until consider threshold."""
        monitor = TokenMonitor()
        monitor.check_usage(500_000)
        remaining = monitor.get_tokens_until_threshold("consider")
        assert remaining == 200_000  # 700k - 500k

    def test_get_tokens_until_threshold_recommended(self):
        """Test tokens remaining until recommended threshold."""
        monitor = TokenMonitor()
        monitor.check_usage(700_000)
        remaining = monitor.get_tokens_until_threshold("recommended")
        assert remaining == 150_000  # 850k - 700k

    def test_get_tokens_until_threshold_urgent(self):
        """Test tokens remaining until urgent threshold."""
        monitor = TokenMonitor()
        monitor.check_usage(800_000)
        remaining = monitor.get_tokens_until_threshold("urgent")
        assert remaining == 150_000  # 950k - 800k

    def test_get_tokens_until_threshold_already_exceeded(self):
        """Test tokens until threshold when already exceeded."""
        monitor = TokenMonitor()
        monitor.check_usage(980_000)
        remaining = monitor.get_tokens_until_threshold("consider")
        assert remaining == 0  # Already past threshold

    def test_get_tokens_until_threshold_invalid(self):
        """Test invalid threshold name raises ValueError."""
        monitor = TokenMonitor()
        with pytest.raises(ValueError, match="Invalid threshold"):
            monitor.get_tokens_until_threshold("invalid")

    def test_usage_stats_to_dict(self):
        """Test UsageStats can be converted to dict."""
        monitor = TokenMonitor()
        stats = monitor.check_usage(500_000)
        stats_dict = stats.to_dict()

        assert isinstance(stats_dict, dict)
        assert stats_dict["current_tokens"] == 500_000
        assert stats_dict["percentage"] == 50.0
        assert "threshold_status" in stats_dict
        assert "recommendation" in stats_dict
