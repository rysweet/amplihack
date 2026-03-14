"""Tests for memory export/import functionality.

Philosophy:
- Test roundtrip: export -> import -> verify identical facts
- Test JSON format human-readability
- Test merge mode (import into existing KB)
- Test CLI-level export/import commands
- Use temporary directories for DB isolation
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from amplihack.agents.goal_seeking.hierarchical_memory import (
    HierarchicalMemory,
)
from amplihack.agents.goal_seeking.memory_export import export_memory, import_memory


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test databases and exports."""
    d = Path(tempfile.mkdtemp())
    yield d
    if d.exists():
        shutil.rmtree(d)


@pytest.fixture
def populated_memory(temp_dir):
    """Create a HierarchicalMemory with some test data."""
    mem = HierarchicalMemory(agent_name="export_test", db_path=temp_dir / "source_db")

    # Store an episode
    ep_id = mem.store_episode(
        content="Article about marine biology and coral reefs.",
        source_label="Wikipedia: Coral Reefs",
    )

    # Store semantic nodes derived from the episode
    mem.store_knowledge(
        content="Coral reefs are underwater ecosystems built by colonies of tiny animals.",
        concept="coral reefs",
        confidence=0.95,
        source_id=ep_id,
        tags=["biology", "marine"],
    )
    mem.store_knowledge(
        content="The Great Barrier Reef is the largest coral reef system in the world.",
        concept="great barrier reef",
        confidence=0.9,
        source_id=ep_id,
        tags=["geography", "marine"],
    )
    mem.store_knowledge(
        content="Coral bleaching occurs when water temperatures rise abnormally.",
        concept="coral bleaching",
        confidence=0.85,
        tags=["ecology", "climate"],
    )

    yield mem
    mem.close()


class TestExportToJson:
    """Tests for HierarchicalMemory.export_to_json()."""

    def test_export_returns_all_semantic_nodes(self, populated_memory):
        """All stored semantic nodes should appear in the export."""
        data = populated_memory.export_to_json()
        assert len(data["semantic_nodes"]) == 3

    def test_export_returns_episodic_nodes(self, populated_memory):
        """Stored episodic nodes should appear in the export."""
        data = populated_memory.export_to_json()
        assert len(data["episodic_nodes"]) == 1
        assert data["episodic_nodes"][0]["source_label"] == "Wikipedia: Coral Reefs"

    def test_export_includes_metadata(self, populated_memory):
        """Exported nodes should contain full metadata."""
        data = populated_memory.export_to_json()
        sem_node = data["semantic_nodes"][0]
        assert "memory_id" in sem_node
        assert "content" in sem_node
        assert "concept" in sem_node
        assert "confidence" in sem_node
        assert "tags" in sem_node
        assert "metadata" in sem_node
        assert "created_at" in sem_node
        assert "entity_name" in sem_node

    def test_export_includes_derives_from_edges(self, populated_memory):
        """Export should include DERIVES_FROM edges from facts to episodes."""
        data = populated_memory.export_to_json()
        # Nodes with source_id should have DERIVES_FROM edges
        assert len(data["derives_from_edges"]) >= 1
        edge = data["derives_from_edges"][0]
        assert "source_id" in edge
        assert "target_id" in edge
        assert "extraction_method" in edge

    def test_export_includes_similar_to_edges_for_high_overlap(self, temp_dir):
        """SIMILAR_TO edges should be exported when content overlaps strongly."""
        mem = HierarchicalMemory(agent_name="sim_test", db_path=temp_dir / "sim_db")
        mem.store_knowledge(
            content="Photosynthesis converts light energy into chemical energy in plants",
            concept="photosynthesis",
            tags=["biology", "plants", "energy"],
        )
        mem.store_knowledge(
            content="Plants perform photosynthesis to produce energy from sunlight",
            concept="photosynthesis",
            tags=["biology", "plants", "energy"],
        )
        data = mem.export_to_json()
        assert len(data["similar_to_edges"]) >= 1
        mem.close()

    def test_export_includes_statistics(self, populated_memory):
        """Export should include summary statistics."""
        data = populated_memory.export_to_json()
        stats = data["statistics"]
        assert stats["semantic_node_count"] == 3
        assert stats["episodic_node_count"] == 1

    def test_export_includes_agent_name(self, populated_memory):
        """Export should record the source agent name."""
        data = populated_memory.export_to_json()
        assert data["agent_name"] == "export_test"

    def test_export_format_version(self, populated_memory):
        """Export should include a format version."""
        data = populated_memory.export_to_json()
        assert data["format_version"] == "1.0"

    def test_export_is_json_serializable(self, populated_memory):
        """Exported data should be JSON-serializable without error."""
        data = populated_memory.export_to_json()
        json_str = json.dumps(data, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 100

    def test_export_empty_memory(self, temp_dir):
        """Exporting empty memory should return empty lists."""
        mem = HierarchicalMemory(agent_name="empty_agent", db_path=temp_dir / "empty_db")
        data = mem.export_to_json()
        assert data["semantic_nodes"] == []
        assert data["episodic_nodes"] == []
        assert data["statistics"]["semantic_node_count"] == 0
        mem.close()


class TestImportFromJson:
    """Tests for HierarchicalMemory.import_from_json()."""

    def test_import_creates_nodes(self, populated_memory, temp_dir):
        """Import should create all nodes in the target memory."""
        # Export from source
        data = populated_memory.export_to_json()

        # Import into a fresh memory
        target = HierarchicalMemory(agent_name="import_test", db_path=temp_dir / "target_db")
        stats = target.import_from_json(data)

        assert stats["semantic_nodes_imported"] == 3
        assert stats["episodic_nodes_imported"] == 1
        assert stats["errors"] == 0

        # Verify nodes exist
        nodes = target.get_all_knowledge(limit=50)
        assert len(nodes) == 3
        target.close()

    def test_import_creates_edges(self, populated_memory, temp_dir):
        """Import should reconstruct edges."""
        data = populated_memory.export_to_json()

        target = HierarchicalMemory(agent_name="import_test2", db_path=temp_dir / "target_db2")
        stats = target.import_from_json(data)

        assert stats["edges_imported"] >= 2  # At least SIMILAR_TO + DERIVES_FROM
        target.close()

    def test_import_replace_mode_clears_existing(self, populated_memory, temp_dir):
        """Import with merge=False should clear existing data first."""
        data = populated_memory.export_to_json()

        # Create target with some existing data
        target = HierarchicalMemory(agent_name="replace_test", db_path=temp_dir / "replace_db")
        target.store_knowledge("Old fact that should be removed", "old topic")

        # Import with replace (merge=False, the default)
        target.import_from_json(data, merge=False)

        nodes = target.get_all_knowledge(limit=50)
        contents = [n.content for n in nodes]
        assert "Old fact that should be removed" not in contents
        assert len(nodes) == 3  # Only the imported ones
        target.close()

    def test_import_merge_mode_adds_to_existing(self, populated_memory, temp_dir):
        """Import with merge=True should keep existing data."""
        data = populated_memory.export_to_json()

        # Create target with existing data
        target = HierarchicalMemory(agent_name="merge_test", db_path=temp_dir / "merge_db")
        target.store_knowledge("Existing fact that should remain", "existing topic")

        # Import with merge
        stats = target.import_from_json(data, merge=True)

        assert stats["semantic_nodes_imported"] == 3
        nodes = target.get_all_knowledge(limit=50)
        contents = [n.content for n in nodes]
        assert "Existing fact that should remain" in contents
        assert len(nodes) == 4  # 1 existing + 3 imported
        target.close()

    def test_import_merge_skips_duplicates(self, populated_memory, temp_dir):
        """Merge mode should skip nodes that already exist by ID."""
        data = populated_memory.export_to_json()

        # Import into fresh target
        target = HierarchicalMemory(agent_name="dedup_test", db_path=temp_dir / "dedup_db")
        stats1 = target.import_from_json(data, merge=False)
        assert stats1["semantic_nodes_imported"] == 3
        assert stats1["skipped"] == 0

        # Import again with merge - should skip all existing
        stats2 = target.import_from_json(data, merge=True)
        assert stats2["semantic_nodes_imported"] == 0
        assert stats2["skipped"] == 4  # 3 semantic + 1 episodic

        # Verify no duplicates
        nodes = target.get_all_knowledge(limit=50)
        assert len(nodes) == 3
        target.close()


class TestRoundtrip:
    """Tests for full export -> import roundtrip."""

    def test_roundtrip_preserves_content(self, populated_memory, temp_dir):
        """Exported and re-imported data should have identical content."""
        # Export
        data = populated_memory.export_to_json()

        # Import into new memory
        target = HierarchicalMemory(agent_name="roundtrip_test", db_path=temp_dir / "rt_db")
        target.import_from_json(data)

        # Verify all content preserved
        source_nodes = populated_memory.get_all_knowledge(limit=50)
        target_nodes = target.get_all_knowledge(limit=50)

        source_contents = sorted(n.content for n in source_nodes)
        target_contents = sorted(n.content for n in target_nodes)

        assert source_contents == target_contents
        target.close()

    def test_roundtrip_preserves_concepts(self, populated_memory, temp_dir):
        """Concepts should survive the roundtrip."""
        data = populated_memory.export_to_json()

        target = HierarchicalMemory(agent_name="rt_concepts", db_path=temp_dir / "rt2_db")
        target.import_from_json(data)

        source_nodes = populated_memory.get_all_knowledge(limit=50)
        target_nodes = target.get_all_knowledge(limit=50)

        source_concepts = sorted(n.concept for n in source_nodes)
        target_concepts = sorted(n.concept for n in target_nodes)

        assert source_concepts == target_concepts
        target.close()

    def test_roundtrip_preserves_confidence(self, populated_memory, temp_dir):
        """Confidence scores should survive the roundtrip."""
        data = populated_memory.export_to_json()

        target = HierarchicalMemory(agent_name="rt_conf", db_path=temp_dir / "rt3_db")
        target.import_from_json(data)

        source_nodes = populated_memory.get_all_knowledge(limit=50)
        target_nodes = target.get_all_knowledge(limit=50)

        source_confidences = sorted(n.confidence for n in source_nodes)
        target_confidences = sorted(n.confidence for n in target_nodes)

        assert source_confidences == target_confidences
        target.close()

    def test_roundtrip_via_file(self, populated_memory, temp_dir):
        """Full file-based roundtrip: export to JSON file, import from JSON file."""
        json_file = temp_dir / "roundtrip.json"

        # Export to file
        export_result = export_memory(
            agent_name="export_test",
            storage_path=temp_dir / "source_db",
            output_path=json_file,
            fmt="json",
        )
        assert Path(export_result["output_path"]).exists()
        assert export_result["statistics"]["semantic_node_count"] == 3

        # Import from file
        import_result = import_memory(
            agent_name="file_rt_test",
            storage_path=temp_dir / "file_rt_db",
            input_path=json_file,
            fmt="json",
        )
        assert import_result["statistics"]["semantic_nodes_imported"] == 3
        assert import_result["statistics"]["episodic_nodes_imported"] == 1
        assert import_result["statistics"]["errors"] == 0


class TestJsonHumanReadability:
    """Tests that the JSON export format is human-readable."""

    def test_json_has_readable_structure(self, populated_memory, temp_dir):
        """JSON export should be well-structured and readable."""
        json_file = temp_dir / "readable.json"
        export_memory(
            agent_name="export_test",
            storage_path=temp_dir / "source_db",
            output_path=json_file,
            fmt="json",
        )

        with open(json_file) as f:
            content = f.read()

        # Should be indented (pretty-printed)
        assert "\n  " in content

        # Should be valid JSON
        data = json.loads(content)
        assert "semantic_nodes" in data
        assert "episodic_nodes" in data

    def test_json_contains_all_fields(self, populated_memory, temp_dir):
        """Exported JSON should contain all expected top-level keys."""
        data = populated_memory.export_to_json()
        expected_keys = {
            "agent_name",
            "exported_at",
            "format_version",
            "semantic_nodes",
            "episodic_nodes",
            "similar_to_edges",
            "derives_from_edges",
            "supersedes_edges",
            "statistics",
        }
        assert set(data.keys()) == expected_keys


class TestExportMemoryFunction:
    """Tests for the standalone export_memory() function."""

    def test_export_json_format(self, populated_memory, temp_dir):
        """export_memory with json format should create a JSON file."""
        output = temp_dir / "export.json"
        result = export_memory(
            agent_name="export_test",
            storage_path=temp_dir / "source_db",
            output_path=output,
            fmt="json",
        )
        assert result["format"] == "json"
        assert Path(result["output_path"]).exists()
        assert result["file_size_bytes"] > 0

    def test_export_invalid_format_raises(self, temp_dir):
        """Unsupported format should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            export_memory(
                agent_name="test",
                storage_path=temp_dir / "db",
                output_path=temp_dir / "out.xml",
                fmt="xml",
            )

    def test_export_empty_agent_name_raises(self, temp_dir):
        """Empty agent name should raise ValueError."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            export_memory(
                agent_name="",
                storage_path=temp_dir / "db",
                output_path=temp_dir / "out.json",
            )


class TestImportMemoryFunction:
    """Tests for the standalone import_memory() function."""

    def test_import_nonexistent_file_raises(self, temp_dir):
        """Importing from nonexistent path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            import_memory(
                agent_name="test",
                input_path=temp_dir / "nonexistent.json",
                fmt="json",
            )

    def test_import_invalid_format_raises(self, temp_dir):
        """Unsupported format should raise ValueError."""
        # Create a dummy file
        dummy = temp_dir / "dummy.txt"
        dummy.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported format"):
            import_memory(
                agent_name="test",
                input_path=dummy,
                fmt="xml",
            )

    def test_import_kuzu_merge_raises(self, temp_dir):
        """Merge mode with kuzu format should raise ValueError."""
        # Create a dummy directory to act as kuzu DB
        dummy_dir = temp_dir / "dummy_kuzu"
        dummy_dir.mkdir()
        (dummy_dir / "placeholder").write_text("data")

        with pytest.raises(ValueError, match="Merge mode is not supported for kuzu format"):
            import_memory(
                agent_name="test",
                input_path=dummy_dir,
                fmt="kuzu",
                merge=True,
            )


class TestClearAgentData:
    """Tests for HierarchicalMemory._clear_agent_data()."""

    def test_clear_removes_all_nodes(self, populated_memory):
        """_clear_agent_data should remove all nodes for this agent."""
        stats_before = populated_memory.get_statistics()
        assert stats_before["semantic_nodes"] == 3
        assert stats_before["episodic_nodes"] == 1

        populated_memory._clear_agent_data()

        stats_after = populated_memory.get_statistics()
        assert stats_after["semantic_nodes"] == 0
        assert stats_after["episodic_nodes"] == 0
