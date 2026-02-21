"""Tests for the DomainEvalHarness."""

from __future__ import annotations

from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent
from amplihack.agents.domain_agents.meeting_synthesizer.agent import MeetingSynthesizerAgent
from amplihack.eval.domain_eval_harness import DomainEvalHarness, EvalReport


class TestDomainEvalHarnessCodeReview:
    """Test eval harness with CodeReviewAgent."""

    def test_run_all_levels(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run()

        assert isinstance(report, EvalReport)
        assert report.agent_name == "test_reviewer"
        assert report.domain == "code_review"
        assert len(report.levels) == 4
        assert 0.0 <= report.overall_score <= 1.0

    def test_run_single_level(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        assert len(report.levels) == 1
        assert report.levels[0].level_id == "L1"

    def test_run_multiple_levels(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1", "L2"])

        assert len(report.levels) == 2

    def test_l1_basic_detection(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        l1 = report.levels[0]
        assert l1.level_id == "L1"
        assert len(l1.scenarios) >= 2
        # Agent should detect at least some basic bugs
        assert l1.average_score > 0.0

    def test_l3_security_review(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L3"])

        l3 = report.levels[0]
        assert l3.level_id == "L3"
        # Security issues should be detected by the tools
        assert l3.average_score > 0.0

    def test_report_to_json(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        json_str = report.to_json()
        assert "test_reviewer" in json_str
        assert "code_review" in json_str
        assert "L1" in json_str

    def test_report_to_dict(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        d = report.to_dict()
        assert d["agent_name"] == "test_reviewer"
        assert d["domain"] == "code_review"
        assert "levels" in d
        assert len(d["levels"]) == 1

    def test_metadata_populated(self):
        agent = CodeReviewAgent("test_reviewer")
        harness = DomainEvalHarness(agent)
        report = harness.run()

        assert report.metadata["levels_evaluated"] == 4
        assert report.metadata["total_scenarios"] >= 4


class TestDomainEvalHarnessMeetingSynth:
    """Test eval harness with MeetingSynthesizerAgent."""

    def test_run_all_levels(self):
        agent = MeetingSynthesizerAgent("test_synth")
        harness = DomainEvalHarness(agent)
        report = harness.run()

        assert isinstance(report, EvalReport)
        assert report.domain == "meeting_synthesizer"
        assert len(report.levels) == 4
        assert 0.0 <= report.overall_score <= 1.0

    def test_l1_extraction(self):
        agent = MeetingSynthesizerAgent("test_synth")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        l1 = report.levels[0]
        assert l1.level_id == "L1"
        # Should extract action items and summaries
        assert l1.average_score > 0.0

    def test_l2_attribution(self):
        agent = MeetingSynthesizerAgent("test_synth")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L2"])

        l2 = report.levels[0]
        assert l2.level_id == "L2"
        assert len(l2.scenarios) >= 1

    def test_scenario_results_populated(self):
        agent = MeetingSynthesizerAgent("test_synth")
        harness = DomainEvalHarness(agent)
        report = harness.run(levels=["L1"])

        for scenario in report.levels[0].scenarios:
            assert scenario.scenario_id
            assert scenario.scenario_name
            assert scenario.grading_details
            assert 0.0 <= scenario.score <= 1.0
