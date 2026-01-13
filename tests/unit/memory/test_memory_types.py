"""Unit tests fer memory type classification and validation.

Tests memory type enums, classification logic, and schema validation
fer the 5 psychological memory types.

Philosophy:
- Test type classification logic in isolation
- Validate schemas fer each memory type
- Test memory type conversions and comparisons
"""

from datetime import datetime, timedelta

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.types import (
        EpisodicMemory,
        MemorySchema,
        MemoryType,
        ProceduralMemory,
        ProspectiveMemory,
        SemanticMemory,
        WorkingMemory,
        classify_memory_type,
    )
except ImportError:
    pytest.skip("Memory types not implemented yet", allow_module_level=True)


class TestMemoryTypeEnum:
    """Test MemoryType enum values and behavior."""

    def test_memory_type_enum_has_five_types(self):
        """Verify all five psychological memory types are defined."""
        assert MemoryType.EPISODIC
        assert MemoryType.SEMANTIC
        assert MemoryType.PROSPECTIVE
        assert MemoryType.PROCEDURAL
        assert MemoryType.WORKING

    def test_memory_type_enum_values_are_unique(self):
        """Ensure no duplicate enum values."""
        types = [
            MemoryType.EPISODIC,
            MemoryType.SEMANTIC,
            MemoryType.PROSPECTIVE,
            MemoryType.PROCEDURAL,
            MemoryType.WORKING,
        ]
        assert len(types) == len(set(types))


class TestEpisodicMemory:
    """Test episodic memory schema and validation (What happened when)."""

    def test_episodic_memory_requires_timestamp(self):
        """Episodic memories must have timestamp fer when they occurred."""
        with pytest.raises(ValueError, match="timestamp"):
            EpisodicMemory(
                content="User asked about auth",
                participants=["user", "claude"],
                context="authentication discussion",
                outcome="explained JWT tokens",
            )

    def test_episodic_memory_requires_participants(self):
        """Episodic memories must track who was involved."""
        with pytest.raises(ValueError, match="participants"):
            EpisodicMemory(
                timestamp=datetime.now(),
                content="User asked about auth",
                context="authentication discussion",
                outcome="explained JWT tokens",
            )

    def test_episodic_memory_valid_creation(self):
        """Valid episodic memory can be created with all required fields."""
        memory = EpisodicMemory(
            timestamp=datetime.now(),
            participants=["user", "claude"],
            content="User asked about auth",
            context="authentication discussion",
            outcome="explained JWT tokens",
        )
        assert memory.timestamp
        assert len(memory.participants) == 2
        assert memory.memory_type == MemoryType.EPISODIC

    def test_episodic_memory_time_range_query(self):
        """Episodic memories can be queried by time range."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        memory = EpisodicMemory(
            timestamp=now,
            participants=["user", "claude"],
            content="Recent discussion",
            context="today",
            outcome="resolved",
        )

        assert memory.is_in_time_range(yesterday, now + timedelta(hours=1))
        assert not memory.is_in_time_range(now + timedelta(hours=1), now + timedelta(hours=2))


class TestSemanticMemory:
    """Test semantic memory schema (Important learnings)."""

    def test_semantic_memory_requires_concept(self):
        """Semantic memories must define what concept they represent."""
        with pytest.raises(ValueError, match="concept"):
            SemanticMemory(
                description="Always validate input",
                examples=["validate_email()", "validate_password()"],
                confidence=0.9,
            )

    def test_semantic_memory_requires_confidence_score(self):
        """Semantic memories need confidence score fer quality."""
        with pytest.raises(ValueError, match="confidence"):
            SemanticMemory(
                concept="Input Validation Pattern",
                description="Always validate input",
                examples=["validate_email()", "validate_password()"],
            )

    def test_semantic_memory_confidence_bounded(self):
        """Confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValueError, match="0.0 and 1.0"):
            SemanticMemory(
                concept="Input Validation",
                description="Always validate",
                examples=[],
                confidence=1.5,
            )

    def test_semantic_memory_valid_creation(self):
        """Valid semantic memory with all fields."""
        memory = SemanticMemory(
            concept="Input Validation Pattern",
            description="Always validate user input before processing",
            examples=["validate_email()", "sanitize_sql()"],
            confidence=0.85,
        )
        assert memory.concept
        assert 0.0 <= memory.confidence <= 1.0
        assert memory.memory_type == MemoryType.SEMANTIC


class TestProspectiveMemory:
    """Test prospective memory schema (Future intentions)."""

    def test_prospective_memory_requires_task(self):
        """Prospective memories must define the task."""
        with pytest.raises(ValueError, match="task"):
            ProspectiveMemory(
                trigger="after fixing bug #123",
                deadline=datetime.now() + timedelta(days=1),
            )

    def test_prospective_memory_requires_trigger(self):
        """Prospective memories need trigger condition."""
        with pytest.raises(ValueError, match="trigger"):
            ProspectiveMemory(
                task="Update documentation",
                deadline=datetime.now() + timedelta(days=1),
            )

    def test_prospective_memory_deadline_optional(self):
        """Deadline is optional fer prospective memories."""
        memory = ProspectiveMemory(
            task="Refactor auth module",
            trigger="after team review",
        )
        assert memory.task
        assert memory.trigger
        assert memory.deadline is None

    def test_prospective_memory_is_overdue_check(self):
        """Can check if prospective memory is overdue."""
        past_deadline = datetime.now() - timedelta(days=1)
        future_deadline = datetime.now() + timedelta(days=1)

        overdue = ProspectiveMemory(
            task="Fix critical bug",
            trigger="immediately",
            deadline=past_deadline,
        )

        not_overdue = ProspectiveMemory(
            task="Add feature",
            trigger="next sprint",
            deadline=future_deadline,
        )

        assert overdue.is_overdue()
        assert not not_overdue.is_overdue()


class TestProceduralMemory:
    """Test procedural memory schema (How to do something)."""

    def test_procedural_memory_requires_procedure_name(self):
        """Procedural memories must have descriptive name."""
        with pytest.raises(ValueError, match="procedure_name"):
            ProceduralMemory(
                steps=["step1", "step2"],
                success_criteria="tests pass",
            )

    def test_procedural_memory_requires_steps(self):
        """Procedural memories must define steps."""
        with pytest.raises(ValueError, match="steps"):
            ProceduralMemory(
                procedure_name="Fix CI failures",
                success_criteria="all checks green",
            )

    def test_procedural_memory_steps_must_be_nonempty(self):
        """Steps list cannot be empty."""
        with pytest.raises(ValueError, match="at least one step"):
            ProceduralMemory(
                procedure_name="Fix CI failures",
                steps=[],
                success_criteria="all checks green",
            )

    def test_procedural_memory_usage_count_tracking(self):
        """Procedural memories track how often they're used."""
        memory = ProceduralMemory(
            procedure_name="Handle CI failures",
            steps=["Check logs", "Fix issue", "Re-run tests"],
            success_criteria="All tests pass",
        )

        assert memory.usage_count == 0

        memory.record_usage()
        assert memory.usage_count == 1

        memory.record_usage()
        assert memory.usage_count == 2

    def test_procedural_memory_strengthening(self):
        """Procedural memories strengthen with usage."""
        memory = ProceduralMemory(
            procedure_name="Deploy to production",
            steps=["Run tests", "Build", "Deploy"],
            success_criteria="Service running",
        )

        initial_strength = memory.strength

        # Simulate multiple uses
        for _ in range(5):
            memory.record_usage()

        # Strength should increase with usage
        assert memory.strength > initial_strength


class TestWorkingMemory:
    """Test working memory schema (Active task details)."""

    def test_working_memory_requires_task_id(self):
        """Working memories must link to task."""
        with pytest.raises(ValueError, match="task_id"):
            WorkingMemory(
                context={"current_file": "auth.py"},
                dependencies=["user-service"],
            )

    def test_working_memory_requires_context(self):
        """Working memories need context variables."""
        with pytest.raises(ValueError, match="context"):
            WorkingMemory(
                task_id="implement-auth-123",
                dependencies=["user-service"],
            )

    def test_working_memory_lifecycle_cleared_on_completion(self):
        """Working memories are cleared when task completes."""
        memory = WorkingMemory(
            task_id="implement-auth-123",
            context={"current_file": "auth.py", "line": 42},
            dependencies=["user-service", "token-service"],
        )

        assert not memory.is_cleared

        memory.mark_task_complete()

        assert memory.is_cleared
        # Context should be cleared
        assert len(memory.context) == 0

    def test_working_memory_valid_creation(self):
        """Valid working memory with all fields."""
        memory = WorkingMemory(
            task_id="implement-auth-123",
            context={
                "current_file": "auth.py",
                "function": "validate_token",
                "line": 42,
            },
            dependencies=["user-service", "token-service"],
        )

        assert memory.task_id
        assert memory.context
        assert len(memory.dependencies) == 2
        assert memory.memory_type == MemoryType.WORKING


class TestMemoryTypeClassification:
    """Test automatic memory type classification."""

    def test_classify_conversation_as_episodic(self):
        """Conversations should be classified as episodic."""
        content = "User asked about authentication implementation"
        context = {"type": "conversation", "participants": ["user", "claude"]}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.EPISODIC

    def test_classify_learning_as_semantic(self):
        """Discovered patterns should be semantic."""
        content = "Always validate input before database queries"
        context = {"type": "pattern", "confidence": 0.9}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.SEMANTIC

    def test_classify_todo_as_prospective(self):
        """TODOs and reminders are prospective."""
        content = "Refactor auth module after code review"
        context = {"type": "todo", "trigger": "code review complete"}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.PROSPECTIVE

    def test_classify_workflow_as_procedural(self):
        """Workflows and procedures are procedural."""
        content = "How to fix CI failures: check logs, fix issues, rerun"
        context = {"type": "procedure", "steps": 3}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.PROCEDURAL

    def test_classify_task_state_as_working(self):
        """Active task state is working memory."""
        content = "Currently implementing JWT validation in auth.py"
        context = {"type": "task_state", "task_id": "auth-123"}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.WORKING

    def test_classify_ambiguous_content_defaults_to_episodic(self):
        """When unclear, default to episodic (safest choice)."""
        content = "Some unclear content"
        context = {}

        memory_type = classify_memory_type(content, context)
        assert memory_type == MemoryType.EPISODIC


class TestMemorySchema:
    """Test generic MemorySchema validation."""

    def test_memory_schema_validates_required_fields(self):
        """All memory types must have base required fields."""
        schema = MemorySchema(
            memory_type=MemoryType.SEMANTIC,
            required_fields=["concept", "description", "confidence"],
        )

        valid_data = {
            "concept": "Test",
            "description": "A test",
            "confidence": 0.8,
        }

        invalid_data = {
            "concept": "Test",
            # Missing description and confidence
        }

        assert schema.validate(valid_data)
        assert not schema.validate(invalid_data)

    def test_memory_schema_type_checking(self):
        """Schema validates field types."""
        schema = MemorySchema(
            memory_type=MemoryType.EPISODIC,
            required_fields=["timestamp", "participants"],
            field_types={"timestamp": datetime, "participants": list},
        )

        valid_data = {
            "timestamp": datetime.now(),
            "participants": ["user", "claude"],
        }

        invalid_data = {
            "timestamp": "not a datetime",  # Wrong type
            "participants": ["user"],
        }

        assert schema.validate(valid_data)
        assert not schema.validate(invalid_data)
