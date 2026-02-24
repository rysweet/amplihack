"""Convergence tracking for multi-wave audits.

Tracks findings across waves and detects convergence using dual thresholds:
- Absolute: New findings < 10
- Relative: New findings < 5% of Wave 1 findings
"""

from typing import Any


class ConvergenceTracker:
    """Tracks audit findings across waves and detects convergence."""

    def __init__(
        self,
        absolute_threshold: int = 10,
        relative_threshold: float = 0.05,
    ):
        """Initialize convergence tracker.

        Args:
            absolute_threshold: Absolute number of new findings to consider converged
            relative_threshold: Relative percentage (0.05 = 5%) compared to Wave 1
        """
        self.absolute_threshold = absolute_threshold
        self.relative_threshold = relative_threshold
        self.wave_metrics: list[dict[str, int]] = []

    def add_wave(self, wave_number: int, findings_count: int) -> None:
        """Add wave results to tracker.

        Args:
            wave_number: Wave number (1-indexed)
            findings_count: Number of new findings in this wave
        """
        self.wave_metrics.append(
            {
                "wave": wave_number,
                "findings": findings_count,
            }
        )

    def check_convergence(
        self,
        wave_metrics: list[dict[str, int]] | None = None,
        config: dict[str, float] | None = None,
    ) -> tuple[bool, str]:
        """Check if audit has converged based on dual thresholds.

        Args:
            wave_metrics: Optional list of wave metrics (uses tracked if None)
            config: Optional config dict with 'absolute_threshold' and 'relative_threshold'

        Returns:
            Tuple of (converged: bool, reason: str)
        """
        if wave_metrics is None:
            wave_metrics = self.wave_metrics

        if config:
            absolute_threshold = config.get("absolute_threshold", self.absolute_threshold)
            relative_threshold = config.get("relative_threshold", self.relative_threshold)
        else:
            absolute_threshold = self.absolute_threshold
            relative_threshold = self.relative_threshold

        if len(wave_metrics) < 2:
            return False, "Need at least 2 waves to check convergence"

        latest_wave = wave_metrics[-1]
        first_wave = wave_metrics[0]

        latest_findings = latest_wave["findings"]
        first_wave_findings = first_wave["findings"]

        if first_wave_findings == 0:
            if latest_findings == 0:
                return True, "No findings in Wave 1 or current wave"
            return False, f"Wave 1 had 0 findings but current wave has {latest_findings}"

        relative_count = latest_findings / first_wave_findings

        if latest_findings < absolute_threshold:
            return True, f"Absolute threshold met: {latest_findings} < {absolute_threshold}"

        if relative_count < relative_threshold:
            percentage = relative_count * 100
            return True, f"Relative threshold met: {percentage:.1f}% < {relative_threshold * 100}%"

        return (
            False,
            f"Not converged: {latest_findings} findings ({relative_count * 100:.1f}% of Wave 1)",
        )

    def get_convergence_ratio(self) -> float:
        """Get convergence ratio (latest / first wave).

        Returns:
            Ratio of latest wave findings to first wave findings
        """
        if len(self.wave_metrics) < 2:
            return 1.0

        first_wave = self.wave_metrics[0]["findings"]
        latest_wave = self.wave_metrics[-1]["findings"]

        if first_wave == 0:
            return 0.0 if latest_wave == 0 else 1.0

        return latest_wave / first_wave

    def generate_convergence_plot(self) -> str:
        """Generate ASCII plot of convergence progress.

        Returns:
            Multi-line string with ASCII bar chart
        """
        if not self.wave_metrics:
            return "No wave data to plot"

        max_findings = max(w["findings"] for w in self.wave_metrics)
        if max_findings == 0:
            max_findings = 1

        lines = ["Convergence Progress:", ""]

        for wave in self.wave_metrics:
            wave_num = wave["wave"]
            findings = wave["findings"]

            bar_length = int((findings / max_findings) * 50)
            bar = "█" * bar_length

            percentage = ""
            if wave_num > 1:
                first_wave_findings = self.wave_metrics[0]["findings"]
                if first_wave_findings > 0:
                    pct = (findings / first_wave_findings) * 100
                    percentage = f" ({pct:.1f}% of Wave 1)"

            lines.append(f"Wave {wave_num:2d}: {bar} {findings}{percentage}")

        lines.append("")

        converged, reason = self.check_convergence()
        status = "✓ CONVERGED" if converged else "✗ NOT CONVERGED"
        lines.append(f"Status: {status}")
        lines.append(f"Reason: {reason}")

        return "\n".join(lines)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all wave metrics.

        Returns:
            Dictionary with convergence statistics
        """
        if not self.wave_metrics:
            return {
                "total_waves": 0,
                "converged": False,
                "convergence_ratio": 0.0,
            }

        converged, reason = self.check_convergence()

        return {
            "total_waves": len(self.wave_metrics),
            "first_wave_findings": self.wave_metrics[0]["findings"],
            "latest_wave_findings": self.wave_metrics[-1]["findings"],
            "total_findings": sum(w["findings"] for w in self.wave_metrics),
            "converged": converged,
            "convergence_ratio": self.get_convergence_ratio(),
            "convergence_reason": reason,
        }


def check_convergence(
    wave_metrics: list[dict[str, int]],
    config: dict[str, float] | None = None,
) -> tuple[bool, str]:
    """Convenience function to check convergence.

    Args:
        wave_metrics: List of wave metrics
        config: Optional config with thresholds

    Returns:
        Tuple of (converged: bool, reason: str)
    """
    tracker = ConvergenceTracker()
    return tracker.check_convergence(wave_metrics, config)


def generate_convergence_plot(wave_metrics: list[dict[str, int]]) -> str:
    """Convenience function to generate convergence plot.

    Args:
        wave_metrics: List of wave metrics

    Returns:
        ASCII plot string
    """
    tracker = ConvergenceTracker()
    for metric in wave_metrics:
        tracker.add_wave(metric["wave"], metric["findings"])
    return tracker.generate_convergence_plot()
