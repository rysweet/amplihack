"""Tests for security domain data generation at scale.

Tests 5000-turn generation, security log blocks, multi-hop questions,
problem-solving tasks, and progressive summarization hooks.
All tests are deterministic and run without LLM calls.
"""

from __future__ import annotations

import time

import pytest

from amplihack.eval.long_horizon_data import (
    INCIDENTS,
    INFRASTRUCTURE,
    PROBLEM_TASKS,
    SECURITY_EVENTS,
    Question,
    generate_dialogue,
    generate_questions,
)


class TestFiveThousandTurnGeneration:
    """Tests for 5000-turn generation performance and correctness."""

    @pytest.fixture(scope="class")
    def gt_5000(self):
        """Generate 5000-turn dialogue once for the test class."""
        return generate_dialogue(num_turns=5000, seed=42)

    def test_5000_turn_count(self, gt_5000):
        """5000-turn generation produces exactly 5000 turns."""
        assert len(gt_5000.turns) == 5000

    def test_5000_turn_generation_performance(self):
        """5000-turn generation completes in under 30 seconds."""
        start = time.time()
        gt = generate_dialogue(num_turns=5000, seed=42)
        elapsed = time.time() - start
        assert elapsed < 30.0, f"Generation took {elapsed:.1f}s, expected < 30s"
        assert len(gt.turns) == 5000

    def test_all_12_blocks_present(self, gt_5000):
        """All 12 blocks are present at 5000 turns."""
        blocks = {t.block for t in gt_5000.turns}
        assert blocks == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}

    def test_block_names_at_5000(self, gt_5000):
        """All block names are present at 5000 turns."""
        names = {t.block_name for t in gt_5000.turns}
        expected = {
            "people", "projects", "technical", "evolving_story",
            "numerical", "contradictory", "callbacks", "distractors",
            "security_logs", "incidents", "infrastructure", "problem_solving",
        }
        assert names == expected

    def test_sequential_turn_numbers(self, gt_5000):
        """Turn numbers are sequential 0 to 4999."""
        for i, turn in enumerate(gt_5000.turns):
            assert turn.turn_number == i, f"Turn {i} has number {turn.turn_number}"

    def test_ground_truth_handles_5000_facts(self, gt_5000):
        """Ground truth tracking works at 5000+ facts without issues."""
        total_facts = sum(len(t.facts) for t in gt_5000.turns)
        assert total_facts > 500, f"Expected 500+ facts, got {total_facts}"
        assert len(gt_5000.facts_by_entity) > 100, "Expected 100+ entity keys"
        assert len(gt_5000.current_values) > 100, "Expected 100+ current values"

    def test_reproducibility_at_5000(self):
        """Same seed produces identical 5000-turn dialogue."""
        gt1 = generate_dialogue(num_turns=5000, seed=42)
        gt2 = generate_dialogue(num_turns=5000, seed=42)
        assert len(gt1.turns) == len(gt2.turns)
        # Check a sample of turns
        for i in range(0, 5000, 100):
            assert gt1.turns[i].content == gt2.turns[i].content
            assert gt1.turns[i].block == gt2.turns[i].block

    def test_question_generation_at_5000(self, gt_5000):
        """Question generation works with 5000-turn ground truth."""
        questions = generate_questions(gt_5000, num_questions=100)
        assert len(questions) == 100
        # All questions should have valid fields
        for q in questions:
            assert q.question_id
            assert q.text
            assert q.expected_answer
            assert q.category
            assert len(q.scoring_dimensions) >= 1

    def test_max_question_pool_size(self, gt_5000):
        """Question pool has 100+ unique questions at 5000 turns."""
        # Request more than pool size to get all available
        questions = generate_questions(gt_5000, num_questions=500)
        assert len(questions) >= 100, f"Expected 100+ questions, got {len(questions)}"

    def test_all_question_categories_at_5000(self, gt_5000):
        """All 12 question categories present at 5000 turns."""
        # Request max to get all categories
        questions = generate_questions(gt_5000, num_questions=500)
        categories = {q.category for q in questions}
        expected = {
            "needle_in_haystack", "temporal_evolution", "numerical_precision",
            "source_attribution", "cross_reference", "distractor_resistance",
            "meta_memory", "security_log_analysis", "incident_tracking",
            "infrastructure_knowledge", "problem_solving", "multi_hop_reasoning",
        }
        assert expected.issubset(categories), f"Missing: {expected - categories}"


class TestSecurityLogBlocks:
    """Tests for security log block data and patterns."""

    def test_security_events_count(self):
        """Security events data has 50+ entries."""
        assert len(SECURITY_EVENTS) >= 50

    def test_security_events_have_required_fields(self):
        """Every security event has required fields."""
        required = {"timestamp", "source_ip", "event", "user", "severity"}
        for i, evt in enumerate(SECURITY_EVENTS):
            missing = required - set(evt.keys())
            assert not missing, f"Event {i} missing fields: {missing}"

    def test_security_events_have_valid_severities(self):
        """All security events have valid severity levels."""
        valid_severities = {"low", "medium", "high", "critical"}
        for i, evt in enumerate(SECURITY_EVENTS):
            assert evt["severity"] in valid_severities, (
                f"Event {i} has invalid severity: {evt['severity']}"
            )

    def test_brute_force_pattern_present(self):
        """Security events contain a brute force pattern (multiple failed logins from same IP)."""
        from collections import Counter
        failed_by_ip: dict[str, int] = Counter()
        for evt in SECURITY_EVENTS:
            if "failed" in evt["event"].lower():
                failed_by_ip[evt["source_ip"]] += 1
        # At least one IP should have 5+ failed attempts
        max_failures = max(failed_by_ip.values()) if failed_by_ip else 0
        assert max_failures >= 5, f"Expected brute force pattern (5+ failures), max was {max_failures}"

    def test_data_exfiltration_pattern_present(self):
        """Security events contain data exfiltration indicators."""
        exfil_events = [e for e in SECURITY_EVENTS if "exfil" in e["event"].lower() or "data transfer" in e["event"].lower()]
        assert len(exfil_events) >= 1, "Expected data exfiltration events"

    def test_port_scan_pattern_present(self):
        """Security events contain port scanning."""
        scan_events = [e for e in SECURITY_EVENTS if "port scan" in e["event"].lower()]
        assert len(scan_events) >= 1, "Expected port scan events"

    def test_lateral_movement_pattern_present(self):
        """Security events contain lateral movement."""
        lateral_events = [e for e in SECURITY_EVENTS if "lateral" in e["event"].lower()]
        assert len(lateral_events) >= 1, "Expected lateral movement events"

    def test_security_events_in_dialogue(self):
        """Security log block contains security events in the dialogue."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        sec_turns = [t for t in gt.turns if t.block == 9]
        assert len(sec_turns) > 0, "No security log turns found"
        # Check that security events contain IP addresses
        sec_content = " ".join(t.content for t in sec_turns)
        assert "192.168.1.45" in sec_content, "Brute force IP not in security logs"
        assert "Cobalt Strike" in sec_content or "cobalt" in sec_content.lower(), "Malware not in security logs"


class TestIncidentReports:
    """Tests for incident report data and status evolution."""

    def test_incidents_count(self):
        """There are 5-10 incidents."""
        assert 5 <= len(INCIDENTS) <= 10

    def test_incidents_have_required_fields(self):
        """Every incident has required fields."""
        required = {"id", "title", "status", "severity", "affected_systems", "iocs", "timeline"}
        for inc in INCIDENTS:
            missing = required - set(inc.keys())
            assert not missing, f"Incident {inc['id']} missing fields: {missing}"

    def test_incidents_have_updates(self):
        """Incidents have status update progressions."""
        for inc in INCIDENTS:
            assert len(inc.get("updates", [])) >= 1, (
                f"Incident {inc['id']} has no updates"
            )

    def test_incident_status_evolves_in_dialogue(self):
        """Incident status changes are reflected in dialogue turns."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        inc_turns = [t for t in gt.turns if t.block == 10]
        assert len(inc_turns) > 0, "No incident turns found"
        # Check for status change content
        all_content = " ".join(t.content for t in inc_turns)
        assert "Status changed" in all_content or "status" in all_content.lower()

    def test_incidents_have_iocs(self):
        """Each incident has at least one IOC."""
        for inc in INCIDENTS:
            assert len(inc["iocs"]) >= 1, f"Incident {inc['id']} has no IOCs"

    def test_incidents_have_timelines(self):
        """Each incident has a timeline with at least 2 entries."""
        for inc in INCIDENTS:
            assert len(inc["timeline"]) >= 2, (
                f"Incident {inc['id']} has too few timeline entries"
            )

    def test_superseded_values_for_incidents(self):
        """Incident status updates create superseded values in ground truth."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        inc_superseded = {k: v for k, v in gt.superseded_values.items() if k.startswith("INC-")}
        assert len(inc_superseded) > 0, "Expected superseded values for incident status changes"


class TestInfrastructureData:
    """Tests for infrastructure inventory data."""

    def test_infrastructure_has_all_categories(self):
        """Infrastructure data covers subnets, LBs, K8s, FW, DNS, DBs."""
        assert "subnets" in INFRASTRUCTURE
        assert "load_balancers" in INFRASTRUCTURE
        assert "kubernetes_clusters" in INFRASTRUCTURE
        assert "firewall_rules" in INFRASTRUCTURE
        assert "dns_records" in INFRASTRUCTURE
        assert "databases" in INFRASTRUCTURE

    def test_subnets_have_required_fields(self):
        """Every subnet has name, cidr, purpose."""
        for subnet in INFRASTRUCTURE["subnets"]:
            assert "name" in subnet
            assert "cidr" in subnet
            assert "purpose" in subnet

    def test_kubernetes_clusters_have_details(self):
        """K8s clusters have version, nodes, pod_count."""
        for k8s in INFRASTRUCTURE["kubernetes_clusters"]:
            assert "name" in k8s
            assert "version" in k8s
            assert "nodes" in k8s
            assert "pod_count" in k8s

    def test_firewall_rules_have_action(self):
        """Firewall rules have source, dest, ports, action."""
        for fw in INFRASTRUCTURE["firewall_rules"]:
            assert "source" in fw
            assert "dest" in fw
            assert "ports" in fw
            assert fw["action"] in ("allow", "deny")

    def test_infrastructure_in_dialogue(self):
        """Infrastructure block appears in dialogue."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        infra_turns = [t for t in gt.turns if t.block == 11]
        assert len(infra_turns) > 0, "No infrastructure turns found"
        content = " ".join(t.content for t in infra_turns)
        assert "subnet" in content.lower() or "Subnet" in content
        assert "kubernetes" in content.lower() or "Kubernetes" in content


class TestProblemSolvingTasks:
    """Tests for problem-solving task data."""

    def test_problem_tasks_count(self):
        """There are 10+ problem-solving tasks."""
        assert len(PROBLEM_TASKS) >= 10

    def test_problem_tasks_have_required_fields(self):
        """Every task has task, expected_approach, context_facts."""
        for i, task in enumerate(PROBLEM_TASKS):
            assert "task" in task, f"Task {i} missing 'task' field"
            assert "expected_approach" in task, f"Task {i} missing 'expected_approach' field"
            assert "context_facts" in task, f"Task {i} missing 'context_facts' field"
            assert len(task["context_facts"]) >= 1, f"Task {i} has no context facts"

    def test_problem_tasks_include_expected_approach(self):
        """Tasks describe the expected approach methodology."""
        for task in PROBLEM_TASKS:
            assert len(task["expected_approach"]) > 10, (
                f"Expected approach too short: {task['expected_approach']}"
            )

    def test_problem_solving_in_dialogue(self):
        """Problem-solving block appears in dialogue."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        ps_turns = [t for t in gt.turns if t.block == 12]
        assert len(ps_turns) > 0, "No problem-solving turns found"


class TestMultiHopQuestions:
    """Tests for multi-hop question generation."""

    @pytest.fixture(scope="class")
    def questions_5000(self):
        """Generate questions from 5000-turn dialogue (request max pool)."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        return generate_questions(gt, num_questions=500)

    def test_multi_hop_questions_exist(self, questions_5000):
        """Multi-hop questions are generated."""
        multi_hop = [q for q in questions_5000 if q.category == "multi_hop_reasoning"]
        assert len(multi_hop) >= 3, f"Expected 3+ multi-hop questions, got {len(multi_hop)}"

    def test_multi_hop_have_chain_lengths(self, questions_5000):
        """Multi-hop questions have chain_length > 1."""
        multi_hop = [q for q in questions_5000 if q.category == "multi_hop_reasoning"]
        for q in multi_hop:
            assert q.chain_length >= 2, (
                f"Multi-hop question {q.question_id} should have chain_length >= 2, got {q.chain_length}"
            )

    def test_2_hop_questions_present(self, questions_5000):
        """2-hop questions are present."""
        two_hop = [q for q in questions_5000 if q.chain_length == 2]
        assert len(two_hop) >= 2, f"Expected 2+ two-hop questions, got {len(two_hop)}"

    def test_3_hop_questions_present(self, questions_5000):
        """3-hop questions are present (requires security blocks)."""
        three_hop = [q for q in questions_5000 if q.chain_length == 3]
        assert len(three_hop) >= 1, f"Expected 1+ three-hop questions, got {len(three_hop)}"

    def test_multi_hop_valid_chains(self, questions_5000):
        """Multi-hop questions have expected answers referencing multiple entities."""
        multi_hop = [q for q in questions_5000 if q.category == "multi_hop_reasoning"]
        for q in multi_hop:
            # Each multi-hop answer should contain multiple specific details
            answer_length = len(q.expected_answer)
            assert answer_length > 50, (
                f"Multi-hop answer too short ({answer_length} chars): {q.question_id}"
            )

    def test_single_hop_questions_have_chain_length_1(self, questions_5000):
        """Non-multi-hop questions default to chain_length 1."""
        single_hop = [q for q in questions_5000 if q.category != "multi_hop_reasoning"]
        for q in single_hop:
            assert q.chain_length == 1, (
                f"Non-multi-hop question {q.question_id} should have chain_length 1, got {q.chain_length}"
            )


class TestNewQuestionCategories:
    """Tests for new security-domain question categories."""

    @pytest.fixture(scope="class")
    def questions_5000(self):
        """Generate questions from 5000-turn dialogue (request max pool)."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        return generate_questions(gt, num_questions=500)

    def test_security_log_analysis_questions(self, questions_5000):
        """Security log analysis questions are generated."""
        sec = [q for q in questions_5000 if q.category == "security_log_analysis"]
        assert len(sec) >= 3, f"Expected 3+ security log questions, got {len(sec)}"

    def test_incident_tracking_questions(self, questions_5000):
        """Incident tracking questions are generated."""
        inc = [q for q in questions_5000 if q.category == "incident_tracking"]
        assert len(inc) >= 3, f"Expected 3+ incident tracking questions, got {len(inc)}"

    def test_infrastructure_knowledge_questions(self, questions_5000):
        """Infrastructure knowledge questions are generated."""
        infra = [q for q in questions_5000 if q.category == "infrastructure_knowledge"]
        assert len(infra) >= 3, f"Expected 3+ infrastructure questions, got {len(infra)}"

    def test_problem_solving_questions(self, questions_5000):
        """Problem solving questions are generated."""
        ps = [q for q in questions_5000 if q.category == "problem_solving"]
        assert len(ps) >= 2, f"Expected 2+ problem solving questions, got {len(ps)}"

    def test_question_ids_unique(self, questions_5000):
        """All question IDs remain unique with new categories."""
        ids = [q.question_id for q in questions_5000]
        assert len(ids) == len(set(ids)), "Duplicate question IDs found"

    def test_questions_have_expected_answers(self, questions_5000):
        """All new category questions have non-empty expected answers."""
        new_cats = {"security_log_analysis", "incident_tracking", "infrastructure_knowledge", "problem_solving", "multi_hop_reasoning"}
        new_qs = [q for q in questions_5000 if q.category in new_cats]
        for q in new_qs:
            assert q.expected_answer, f"Question {q.question_id} has no expected answer"
            assert len(q.expected_answer) > 10, (
                f"Question {q.question_id} expected answer too short"
            )


class TestBlockDistributionAt5000:
    """Tests for proper block distribution at 5000 turns."""

    @pytest.fixture(scope="class")
    def gt_5000(self):
        """Generate 5000-turn dialogue."""
        return generate_dialogue(num_turns=5000, seed=42)

    def test_security_logs_block_size(self, gt_5000):
        """Security logs block has a reasonable number of turns."""
        sec_turns = sum(1 for t in gt_5000.turns if t.block == 9)
        # Should be roughly 10% of 5000 = 500 turns
        assert sec_turns >= 100, f"Security logs block too small: {sec_turns}"

    def test_incidents_block_size(self, gt_5000):
        """Incidents block has a reasonable number of turns."""
        inc_turns = sum(1 for t in gt_5000.turns if t.block == 10)
        assert inc_turns >= 50, f"Incidents block too small: {inc_turns}"

    def test_infrastructure_block_size(self, gt_5000):
        """Infrastructure block has a reasonable number of turns."""
        infra_turns = sum(1 for t in gt_5000.turns if t.block == 11)
        assert infra_turns >= 50, f"Infrastructure block too small: {infra_turns}"

    def test_problem_solving_block_size(self, gt_5000):
        """Problem solving block has a reasonable number of turns."""
        ps_turns = sum(1 for t in gt_5000.turns if t.block == 12)
        assert ps_turns >= 20, f"Problem solving block too small: {ps_turns}"

    def test_original_blocks_still_significant(self, gt_5000):
        """Original blocks (1-8) still have representation at 5000 turns."""
        for block_num in range(1, 9):
            count = sum(1 for t in gt_5000.turns if t.block == block_num)
            # Block 1 (people) may be small since it's content-limited (10 people = 10 turns)
            min_expected = 5 if block_num == 1 else 20
            assert count >= min_expected, f"Block {block_num} too small at 5000 turns: {count}"

    def test_no_empty_content_turns(self, gt_5000):
        """No turns have empty content."""
        for turn in gt_5000.turns:
            assert turn.content.strip(), f"Turn {turn.turn_number} has empty content"


class TestScalePerformance:
    """Tests for scaling behavior at various turn counts."""

    @pytest.mark.parametrize("num_turns", [100, 500, 1000, 2000, 5000])
    def test_generation_at_various_scales(self, num_turns):
        """Generation works correctly at multiple scales."""
        gt = generate_dialogue(num_turns=num_turns, seed=42)
        assert len(gt.turns) == num_turns
        # Verify sequential numbering
        for i, turn in enumerate(gt.turns):
            assert turn.turn_number == i

    def test_question_scaling(self):
        """Question count scales proportionally within pool limits."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        for num_q in [20, 50, 100]:
            questions = generate_questions(gt, num_questions=num_q)
            assert len(questions) == num_q
