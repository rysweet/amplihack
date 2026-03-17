"""Tests for security_log_eval.py — data generation and grading."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import random

from amplihack.eval.security_log_eval import (
    SecurityLogEval,
    SecurityQuestion,
    _generate_campaign_events,
    _generate_campaigns,
    _generate_noise_events,
    _generate_questions,
    _grade_answer,
    _objective_keyword,
    _technique_keyword,
)


class TestCampaignGeneration:
    def test_deterministic(self):
        c1 = _generate_campaigns(random.Random(42), 6)
        c2 = _generate_campaigns(random.Random(42), 6)
        assert [c.campaign_id for c in c1] == [c.campaign_id for c in c2]
        assert [c.threat_actor for c in c1] == [c.threat_actor for c in c2]

    def test_num_campaigns(self):
        campaigns = _generate_campaigns(random.Random(42), 12)
        assert len(campaigns) == 12

    def test_campaign_has_required_fields(self):
        campaigns = _generate_campaigns(random.Random(42), 3)
        for c in campaigns:
            assert c.campaign_id.startswith("CAMP-")
            assert len(c.target_devices) >= 3
            assert len(c.target_users) >= 1
            assert len(c.techniques) >= 3
            assert len(c.iocs["ip"]) >= 2
            assert len(c.malware_hashes) >= 1
            assert c.objective in (
                "data_exfiltration",
                "ransomware",
                "espionage",
                "cryptomining",
                "supply_chain",
            )

    def test_unique_campaign_ids(self):
        campaigns = _generate_campaigns(random.Random(42), 12)
        ids = [c.campaign_id for c in campaigns]
        assert len(ids) == len(set(ids))


class TestEventGeneration:
    def test_campaign_produces_events(self):
        campaigns = _generate_campaigns(random.Random(42), 1)
        events = _generate_campaign_events(random.Random(42), campaigns[0])
        assert len(events) >= 5  # at least initial access + exec + c2 + file + noise

    def test_events_have_mde_format(self):
        campaigns = _generate_campaigns(random.Random(42), 1)
        events = _generate_campaign_events(random.Random(42), campaigns[0])
        campaign_events = [e for e in events if e["phase"] != "noise"]
        for e in campaign_events:
            assert "[MDE " in e["content"]
            assert "DeviceName:" in e["content"] or "AlertId:" in e["content"]

    def test_events_have_ground_truth(self):
        campaigns = _generate_campaigns(random.Random(42), 1)
        events = _generate_campaign_events(random.Random(42), campaigns[0])
        facts = [f for e in events for f in e["facts"]]
        assert len(facts) >= 3

    def test_campaign_events_include_actor_attribution(self):
        campaign = _generate_campaigns(random.Random(42), 1)[0]
        actor_name = campaign.threat_actor.split("(")[0].strip()
        events = _generate_campaign_events(random.Random(42), campaign)

        attribution_events = [e for e in events if f"ThreatActor: {actor_name}" in e["content"]]

        assert attribution_events
        assert any(
            f"CampaignId: {campaign.campaign_id}" in e["content"] for e in attribution_events
        )
        assert any(
            f"{campaign.campaign_id} threat actor {actor_name}" in e["facts"]
            for e in attribution_events
        )

    def test_campaign_events_include_benchmark_summary_metadata(self):
        campaign = _generate_campaigns(random.Random(42), 1)[0]
        events = _generate_campaign_events(random.Random(42), campaign)

        summary_events = [
            e for e in events if f"AlertId: SUM-{campaign.campaign_id}" in e["content"]
        ]

        assert summary_events
        summary = summary_events[0]
        assert f"Objective: {_objective_keyword(campaign.objective)}" in summary["content"]
        for ip in campaign.iocs["ip"][:2]:
            assert ip in summary["content"]
        assert campaign.malware_hashes[0] in summary["content"]
        for technique in campaign.techniques[:4]:
            assert _technique_keyword(technique) in summary["content"]

    def test_noise_events_have_no_facts(self):
        events = _generate_noise_events(random.Random(42), 50, 30)
        for e in events:
            assert e["facts"] == []
            assert e["phase"] == "noise"
            assert e["campaign_id"] == "BENIGN"

    def test_noise_event_count(self):
        events = _generate_noise_events(random.Random(42), 100, 30)
        assert len(events) == 100


class TestQuestionGeneration:
    def test_generates_questions(self):
        campaigns = _generate_campaigns(random.Random(42), 6)
        questions = _generate_questions(campaigns, random.Random(42), 50)
        assert len(questions) <= 50
        assert len(questions) >= 20  # at least 5 per campaign x 4 types

    def test_question_categories(self):
        campaigns = _generate_campaigns(random.Random(42), 6)
        questions = _generate_questions(campaigns, random.Random(42), 100)
        categories = {q.category for q in questions}
        assert "alert_retrieval" in categories
        assert "attack_chain" in categories
        assert "ioc_correlation" in categories
        assert "temporal" in categories

    def test_question_has_ground_truth(self):
        campaigns = _generate_campaigns(random.Random(42), 3)
        questions = _generate_questions(campaigns, random.Random(42), 20)
        for q in questions:
            assert len(q.required_keywords) >= 1
            assert len(q.campaign_ids) >= 1

    def test_seeded_actor_attribution_questions_are_backed_by_generated_events(self):
        eval_harness = SecurityLogEval(num_turns=300, num_questions=50, num_campaigns=12, seed=42)
        eval_harness.generate()

        actor_questions = [
            q
            for q in eval_harness.questions
            if q.category == "cross_campaign" and "attributed to " in q.question
        ]
        assert actor_questions

        contents = [
            event["content"] for event in eval_harness.events if event["campaign_id"] != "BENIGN"
        ]
        for question in actor_questions:
            actor_name = question.question.split("attributed to ", 1)[1].split("?", 1)[0]
            for campaign_id in question.required_keywords:
                assert any(
                    f"CampaignId: {campaign_id}" in content
                    and f"ThreatActor: {actor_name}" in content
                    for content in contents
                )

    def test_seeded_required_keywords_are_backed_by_generated_events(self):
        eval_harness = SecurityLogEval(num_turns=300, num_questions=50, num_campaigns=12, seed=42)
        eval_harness.generate()

        telemetry = "\n".join(
            event["content"] for event in eval_harness.events if event["campaign_id"] != "BENIGN"
        ).lower()
        missing = []
        for question in eval_harness.questions:
            missing_keywords = [
                kw for kw in question.required_keywords if kw.lower() not in telemetry
            ]
            if missing_keywords:
                missing.append((question.question_id, missing_keywords))

        assert missing == []


class TestGrading:
    def test_perfect_answer(self):
        q = SecurityQuestion(
            question_id="SEC-0001",
            question="What devices were targeted?",
            category="alert_retrieval",
            ground_truth_facts=["CAMP-2024-001 on WS-FIN-001"],
            required_keywords=["WS-FIN-001", "WS-ENG-002"],
            campaign_ids=["CAMP-2024-001"],
            difficulty="easy",
        )
        answer = "Campaign CAMP-2024-001 targeted WS-FIN-001 and WS-ENG-002."
        result = _grade_answer(q, answer)
        assert result.recall == 1.0
        assert result.score > 0.9

    def test_partial_answer(self):
        q = SecurityQuestion(
            question_id="SEC-0002",
            question="What IPs were used?",
            category="ioc_correlation",
            ground_truth_facts=[],
            required_keywords=["185.100.1.1", "185.200.2.2", "hash123"],
            campaign_ids=["CAMP-2024-001"],
            difficulty="medium",
        )
        answer = "The attack used IP 185.100.1.1 for C2 communication."
        result = _grade_answer(q, answer)
        assert result.recall == pytest.approx(1 / 3, abs=0.01)
        assert len(result.matched_keywords) == 1
        assert len(result.missing_keywords) == 2

    def test_empty_answer(self):
        q = SecurityQuestion(
            question_id="SEC-0003",
            question="What happened?",
            category="alert_retrieval",
            ground_truth_facts=[],
            required_keywords=["WS-FIN-001"],
            campaign_ids=["CAMP-2024-001"],
            difficulty="easy",
        )
        result = _grade_answer(q, "I don't know.")
        assert result.recall == 0.0
        assert result.score == 0.0


class TestSecurityLogEval:
    def test_generate_creates_data(self):
        eval_harness = SecurityLogEval(num_turns=500, num_questions=20, num_campaigns=3, seed=42)
        eval_harness.generate()
        assert len(eval_harness.events) == 500
        assert len(eval_harness.questions) <= 20
        assert len(eval_harness.campaigns) == 3

    def test_deterministic_generation(self):
        e1 = SecurityLogEval(num_turns=200, num_questions=10, num_campaigns=3, seed=99)
        e1.generate()
        e2 = SecurityLogEval(num_turns=200, num_questions=10, num_campaigns=3, seed=99)
        e2.generate()
        assert [e["content"][:50] for e in e1.events] == [e["content"][:50] for e in e2.events]

    def test_events_have_mde_prefix(self):
        e = SecurityLogEval(num_turns=100, num_questions=5, num_campaigns=2, seed=42)
        e.generate()
        mde_events = [ev for ev in e.events if "[MDE " in ev["content"]]
        assert len(mde_events) == len(e.events)

    def test_report_to_dict(self):
        from amplihack.eval.security_log_eval import SecurityEvalReport

        report = SecurityEvalReport(
            overall_score=0.85,
            overall_precision=0.90,
            overall_recall=0.80,
            overall_f1=0.85,
            num_questions=100,
            num_turns=10000,
            num_campaigns=12,
        )
        d = report.to_dict()
        assert d["eval_type"] == "security_log_mde"
        assert d["overall_score"] == 0.85
        assert d["num_campaigns"] == 12

    def test_scale_to_50k(self):
        """Verify we can generate 50K events without issues."""
        e = SecurityLogEval(num_turns=50000, num_questions=100, num_campaigns=12, seed=42)
        e.generate()
        assert len(e.events) == 50000
        # Check campaign events are present (not all noise)
        campaign_events = [ev for ev in e.events if ev["campaign_id"] != "BENIGN"]
        assert len(campaign_events) >= 100  # at least some campaign events survived shuffling
