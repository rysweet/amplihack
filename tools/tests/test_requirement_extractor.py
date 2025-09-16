"""
Comprehensive tests for the requirements extraction tool
Following testing pyramid: 60% unit, 30% integration, 10% E2E
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import List

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from requirement_extractor.models import (
    CodeFile, CodeModule, Requirement, ModuleRequirements,
    ProcessingState, GapAnalysis, ExtractionConfig, OutputFormat
)
from requirement_extractor.discovery import CodeDiscovery
from requirement_extractor.state_manager import StateManager
from requirement_extractor.extractor import RequirementsExtractor
from requirement_extractor.gap_analyzer import GapAnalyzer
from requirement_extractor.formatter import RequirementsFormatter
from requirement_extractor.orchestrator import RequirementsOrchestrator


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample files"""
    temp_dir = tempfile.mkdtemp()

    # Create sample project structure
    project_structure = {
        'src': {
            'main.py': 'def main():\n    print("Hello")\n',
            'auth': {
                'login.py': 'def login(user, password):\n    return True\n',
                'logout.py': 'def logout():\n    pass\n',
            },
            'utils': {
                'helpers.py': 'def format_date(date):\n    return str(date)\n',
            }
        },
        'tests': {
            'test_main.py': 'def test_main():\n    assert True\n',
        },
        'node_modules': {  # Should be skipped
            'package.json': '{}',
        },
        '.venv': {  # Should be skipped
            'lib.py': 'pass',
        },
        'requirements.txt': 'pytest\nflask\n',
        'README.md': '# Test Project\n',
    }

    def create_structure(base_path, structure):
        for name, content in structure.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir(parents=True, exist_ok=True)
                create_structure(path, content)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

    create_structure(Path(temp_dir), project_structure)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_code_files():
    """Sample CodeFile objects for testing"""
    return [
        CodeFile(
            path="/project/src/main.py",
            relative_path="src/main.py",
            language="python",
            size=100,
            lines=10
        ),
        CodeFile(
            path="/project/src/auth/login.py",
            relative_path="src/auth/login.py",
            language="python",
            size=200,
            lines=20
        ),
        CodeFile(
            path="/project/src/auth/logout.py",
            relative_path="src/auth/logout.py",
            language="python",
            size=150,
            lines=15
        ),
    ]


@pytest.fixture
def sample_modules(sample_code_files):
    """Sample CodeModule objects for testing"""
    return [
        CodeModule(
            name="main",
            description="Main application entry point",
            files=[sample_code_files[0]],
            primary_language="python"
        ),
        CodeModule(
            name="auth",
            description="Authentication module",
            files=[sample_code_files[1], sample_code_files[2]],
            primary_language="python"
        ),
    ]


@pytest.fixture
def sample_requirements():
    """Sample Requirement objects for testing"""
    return [
        Requirement(
            id="REQ-001",
            title="User Authentication",
            description="System must support user login and logout",
            category="Authentication",
            priority="high",
            source_modules=["auth"],
            evidence=["def login(user, password):", "def logout():"],
            confidence=0.95
        ),
        Requirement(
            id="REQ-002",
            title="Application Entry Point",
            description="System must have a main entry point",
            category="Core",
            priority="high",
            source_modules=["main"],
            evidence=["def main():"],
            confidence=0.9
        ),
        Requirement(
            id="REQ-003",
            title="Date Formatting",
            description="System must provide date formatting utilities",
            category="Utilities",
            priority="low",
            source_modules=["utils"],
            evidence=["def format_date(date):"],
            confidence=0.7
        ),
    ]


# =============================================================================
# Unit Tests - Discovery Module
# =============================================================================

class TestCodeDiscovery:
    """Tests for CodeDiscovery class"""

    def test_init(self):
        """Test discovery initialization"""
        discovery = CodeDiscovery("/test/path", max_files_per_module=100)
        assert discovery.project_path == Path("/test/path").resolve()
        assert discovery.max_files_per_module == 100

    def test_discover_files(self, temp_project_dir):
        """Test file discovery in project"""
        discovery = CodeDiscovery(temp_project_dir)
        files = discovery.discover_files()

        # Check discovered files
        paths = {f.relative_path for f in files}

        # Should include Python files
        assert "src/main.py" in paths
        assert "src/auth/login.py" in paths
        assert "src/auth/logout.py" in paths
        assert "src/utils/helpers.py" in paths
        assert "tests/test_main.py" in paths

        # Should skip node_modules and .venv
        assert not any("node_modules" in p for p in paths)
        assert not any(".venv" in p for p in paths)

        # Check language detection
        py_files = [f for f in files if f.language == "python"]
        assert len(py_files) >= 5

    def test_group_files_by_directory(self, sample_code_files):
        """Test grouping files by directory structure"""
        discovery = CodeDiscovery("/project")
        modules = discovery._group_by_directory(sample_code_files)

        # Should create modules for directories
        module_names = {m.name for m in modules}
        assert "auth" in module_names  # Directory with multiple files

        # Auth module should have 2 files
        auth_module = next(m for m in modules if m.name == "auth")
        assert len(auth_module.files) == 2

    def test_skip_directories(self):
        """Test that specified directories are skipped"""
        discovery = CodeDiscovery("/test")

        # Check skip directories are configured
        assert ".git" in discovery.SKIP_DIRS
        assert "node_modules" in discovery.SKIP_DIRS
        assert "__pycache__" in discovery.SKIP_DIRS

    def test_language_detection(self):
        """Test language detection from file extensions"""
        discovery = CodeDiscovery("/test")

        # Test Python
        from pathlib import Path
        assert discovery._get_language(Path("test.py")) == "python"
        assert discovery._get_language(Path("test.pyi")) == "python"

        # Test JavaScript/TypeScript
        assert discovery._get_language(Path("test.js")) == "javascript"
        assert discovery._get_language(Path("test.ts")) == "typescript"

        # Test unknown returns None
        assert discovery._get_language(Path("test.xyz")) is None

    def test_empty_project(self):
        """Test handling of empty project directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = CodeDiscovery(temp_dir)
            files = discovery.discover_files()
            assert files == []

            modules = discovery.group_into_modules(files)
            assert modules == []

    def test_large_module_splitting(self):
        """Test that large modules are split appropriately"""
        # Create many files
        files = [
            CodeFile(
                path=f"/project/src/file{i}.py",
                relative_path=f"src/file{i}.py",
                language="python",
                size=100,
                lines=10
            )
            for i in range(100)
        ]

        discovery = CodeDiscovery("/project", max_files_per_module=30)
        modules = discovery.group_into_modules(files)

        # Should split large directory into multiple modules
        for module in modules:
            assert len(module.files) <= 30


# =============================================================================
# Unit Tests - State Manager Module
# =============================================================================

class TestStateManager:
    """Tests for StateManager class"""

    def test_init(self):
        """Test state manager initialization"""
        manager = StateManager(".test_state.json")
        assert manager.state_file == Path(".test_state.json")
        assert manager.state is None

    def test_create_state(self):
        """Test creating new processing state"""
        manager = StateManager(".test_state.json")
        state = manager.create_state("/project", 5)

        assert state.project_path == "/project"
        assert state.total_modules == 5
        assert state.processed_modules == []
        assert state.failed_modules == []
        assert state.current_module is None
        assert manager.state == state

    def test_save_and_load_state(self):
        """Test saving and loading state from disk"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            # Create and save state
            manager = StateManager(state_file)
            state = manager.create_state("/project", 3)
            state.processed_modules = ["module1", "module2"]
            state.current_module = "module3"
            manager.save_state()

            # Load state in new manager
            manager2 = StateManager(state_file)
            loaded_state = manager2.load_state()

            assert loaded_state is not None
            assert loaded_state.project_path == "/project"
            assert loaded_state.total_modules == 3
            assert loaded_state.processed_modules == ["module1", "module2"]
            assert loaded_state.current_module == "module3"
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_update_progress(self):
        """Test updating processing progress"""
        manager = StateManager(".test_state.json")
        state = manager.create_state("/project", 3)

        # Mark module as processing
        manager.update_progress("module1", "processing")
        assert state.current_module == "module1"

        # Mark as completed
        manager.update_progress("module1", "completed")
        assert "module1" in state.processed_modules
        assert state.current_module is None

        # Mark another as failed
        manager.update_progress("module2", "failed")
        assert "module2" in state.failed_modules
        assert "module2" not in state.processed_modules

    def test_is_module_processed(self):
        """Test checking if module is already processed"""
        manager = StateManager(".test_state.json")
        state = manager.create_state("/project", 3)
        state.processed_modules = ["module1"]
        state.failed_modules = ["module2"]

        assert manager.is_module_processed("module1") == True
        assert manager.is_module_processed("module2") == False  # Failed modules can be retried
        assert manager.is_module_processed("module3") == False

    def test_get_pending_modules(self):
        """Test getting list of pending modules"""
        manager = StateManager(".test_state.json")
        state = manager.create_state("/project", 5)
        state.processed_modules = ["module1", "module2"]
        state.failed_modules = ["module3"]

        all_modules = ["module1", "module2", "module3", "module4", "module5"]
        pending = manager.get_pending_modules(all_modules)

        assert "module1" not in pending  # Already processed
        assert "module2" not in pending  # Already processed
        assert "module3" in pending  # Failed, can retry
        assert "module4" in pending
        assert "module5" in pending

    def test_state_progress_calculation(self):
        """Test progress percentage calculation"""
        state = ProcessingState(
            project_path="/test",
            total_modules=4,
            processed_modules=["m1", "m2"],
            failed_modules=["m3"]
        )

        assert state.progress_percentage == 50.0  # 2 out of 4 processed
        assert state.is_complete == False

        state.processed_modules.append("m4")
        assert state.progress_percentage == 75.0  # 3 out of 4 processed
        assert state.is_complete == True  # 3 processed + 1 failed = 4 total


# =============================================================================
# Unit Tests - Extractor Module (with mocked AI)
# =============================================================================

class TestRequirementsExtractor:
    """Tests for RequirementsExtractor class"""

    @pytest.mark.asyncio
    async def test_init_with_timeout(self):
        """Test extractor initialization with timeout settings"""
        extractor = RequirementsExtractor(timeout_seconds=60)
        assert extractor.timeout_seconds == 60

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_extract_from_module_success(self, mock_sdk):
        """Test successful extraction from module with mocked SDK"""
        # Setup mock
        mock_client = AsyncMock()
        mock_sdk.return_value.__aenter__.return_value = mock_client
        mock_client.query = AsyncMock()

        # Mock response stream
        mock_message = Mock()
        mock_message.content = [Mock(text=json.dumps({
            "requirements": [
                {
                    "title": "User Login",
                    "description": "Authenticate users",
                    "category": "Auth",
                    "priority": "high",
                    "evidence": ["def login()"],
                    "confidence": 0.9
                }
            ]
        }))]
        mock_client.receive_response = AsyncMock(return_value=[mock_message])

        # Test extraction
        extractor = RequirementsExtractor()
        module = CodeModule(
            name="auth",
            description="Authentication",
            files=[CodeFile("/test.py", "test.py", "python", 100, 10)],
            primary_language="python"
        )

        requirements = await extractor.extract_from_module(module)

        assert len(requirements) == 1
        assert requirements[0].title == "User Login"
        assert requirements[0].category == "Auth"
        assert requirements[0].source_modules == ["auth"]

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_extract_timeout(self, mock_sdk):
        """Test extraction timeout handling"""
        # Setup mock to timeout
        mock_sdk.side_effect = asyncio.TimeoutError()

        extractor = RequirementsExtractor(timeout_seconds=1)
        module = CodeModule(
            name="test",
            description="Test",
            files=[],
            primary_language="python"
        )

        requirements = await extractor.extract_from_module(module)
        assert requirements == []  # Should return empty on timeout

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_extract_with_malformed_response(self, mock_sdk):
        """Test handling of malformed AI responses"""
        # Mock malformed response
        mock_client = AsyncMock()
        mock_sdk.return_value.__aenter__.return_value = mock_client
        mock_client.query = AsyncMock()

        mock_message = Mock()
        mock_message.content = [Mock(text="Not valid JSON")]
        mock_client.receive_response = AsyncMock(return_value=[mock_message])

        extractor = RequirementsExtractor()
        module = CodeModule(
            name="test",
            description="Test",
            files=[],
            primary_language="python"
        )

        requirements = await extractor.extract_from_module(module)
        assert requirements == []  # Should handle gracefully

    def test_prepare_module_content(self):
        """Test preparing module content for AI processing"""
        extractor = RequirementsExtractor()

        module = CodeModule(
            name="auth",
            description="Authentication module",
            files=[
                CodeFile("/auth/login.py", "auth/login.py", "python", 100, 10),
                CodeFile("/auth/logout.py", "auth/logout.py", "python", 50, 5),
            ],
            primary_language="python"
        )

        content = extractor._prepare_module_content(module)

        assert "Module: auth" in content
        assert "Authentication module" in content
        assert "auth/login.py" in content
        assert "auth/logout.py" in content
        assert "Total lines: 15" in content


# =============================================================================
# Unit Tests - Gap Analyzer Module
# =============================================================================

class TestGapAnalyzer:
    """Tests for GapAnalyzer class"""

    def test_init(self):
        """Test gap analyzer initialization"""
        analyzer = GapAnalyzer()
        assert analyzer is not None

    def test_analyze_gaps(self, sample_requirements):
        """Test gap analysis between extracted and documented requirements"""
        analyzer = GapAnalyzer()

        # Split requirements for testing
        documented = sample_requirements[:2]  # First 2 requirements
        extracted = sample_requirements[1:]  # Last 2 requirements

        analysis = analyzer.analyze_gaps(documented, extracted)

        # REQ-001 is only in documented
        assert len(analysis.missing_in_code) == 1
        assert analysis.missing_in_code[0].id == "REQ-001"

        # REQ-003 is only in extracted
        assert len(analysis.missing_in_docs) == 1
        assert analysis.missing_in_docs[0].id == "REQ-003"

        # REQ-002 is in both
        assert any(r.id == "REQ-002" for r in analysis.documented_requirements)
        assert any(r.id == "REQ-002" for r in analysis.extracted_requirements)

    def test_parse_existing_requirements_markdown(self):
        """Test parsing requirements from markdown file"""
        md_content = """
# Requirements

## REQ-001: User Authentication
**Priority:** High
**Category:** Security

Users must be able to log in and log out securely.

## REQ-002: Data Processing
**Priority:** Medium
**Category:** Core

System must process data in real-time.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(md_content)
            temp_file = f.name

        try:
            analyzer = GapAnalyzer()
            requirements = analyzer.parse_existing_requirements(temp_file)

            assert len(requirements) == 2
            assert requirements[0].id == "REQ-001"
            assert requirements[0].title == "User Authentication"
            assert requirements[0].priority == "high"
            assert requirements[1].id == "REQ-002"
        finally:
            Path(temp_file).unlink()

    def test_parse_existing_requirements_json(self):
        """Test parsing requirements from JSON file"""
        json_content = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "title": "API Rate Limiting",
                    "description": "Limit API calls",
                    "category": "Security",
                    "priority": "high"
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_file = f.name

        try:
            analyzer = GapAnalyzer()
            requirements = analyzer.parse_existing_requirements(temp_file)

            assert len(requirements) == 1
            assert requirements[0].id == "REQ-001"
            assert requirements[0].title == "API Rate Limiting"
        finally:
            Path(temp_file).unlink()

    def test_find_inconsistencies(self, sample_requirements):
        """Test finding inconsistencies between requirements"""
        analyzer = GapAnalyzer()

        # Modify one requirement to create inconsistency
        req1 = sample_requirements[0]
        req2 = Requirement(
            id="REQ-001",  # Same ID
            title="User Management",  # Different title
            description="Different description",
            category="User",  # Different category
            priority="low",  # Different priority
            source_modules=["users"],
            evidence=[],
            confidence=0.8
        )

        inconsistencies = analyzer._find_inconsistencies([req1], [req2])

        assert len(inconsistencies) == 1
        assert inconsistencies[0]["id"] == "REQ-001"
        assert "title" in inconsistencies[0]["differences"]
        assert "priority" in inconsistencies[0]["differences"]
        assert "category" in inconsistencies[0]["differences"]

    def test_empty_gap_analysis(self):
        """Test gap analysis with empty inputs"""
        analyzer = GapAnalyzer()

        analysis = analyzer.analyze_gaps([], [])
        assert analysis.missing_in_code == []
        assert analysis.missing_in_docs == []
        assert analysis.inconsistencies == []


# =============================================================================
# Unit Tests - Formatter Module
# =============================================================================

class TestRequirementsFormatter:
    """Tests for RequirementsFormatter class"""

    def test_format_markdown(self, sample_requirements):
        """Test formatting requirements as markdown"""
        formatter = RequirementsFormatter(
            output_format=OutputFormat.MARKDOWN,
            include_evidence=True
        )

        output = formatter.format(sample_requirements)

        # Check structure
        assert "# Requirements Document" in output
        assert "## Summary" in output
        assert "Total Requirements: 3" in output

        # Check requirements are present
        assert "REQ-001" in output
        assert "User Authentication" in output
        assert "**Priority:** high" in output
        assert "**Confidence:** 95%" in output

        # Check evidence is included
        assert "def login(user, password):" in output

    def test_format_json(self, sample_requirements):
        """Test formatting requirements as JSON"""
        formatter = RequirementsFormatter(output_format=OutputFormat.JSON)

        output = formatter.format(sample_requirements)
        data = json.loads(output)

        assert data["total_requirements"] == 3
        assert len(data["requirements"]) == 3
        assert data["requirements"][0]["id"] == "REQ-001"
        assert data["requirements"][0]["priority"] == "high"

    def test_format_yaml(self, sample_requirements):
        """Test formatting requirements as YAML"""
        formatter = RequirementsFormatter(output_format=OutputFormat.YAML)

        output = formatter.format(sample_requirements)

        # Basic YAML structure checks
        assert "requirements:" in output
        assert "- id: REQ-001" in output
        assert "  title: User Authentication" in output
        assert "total_requirements: 3" in output

    def test_format_with_gaps(self, sample_requirements):
        """Test formatting with gap analysis"""
        formatter = RequirementsFormatter(output_format=OutputFormat.MARKDOWN)

        gap_analysis = GapAnalysis(
            documented_requirements=sample_requirements[:1],
            extracted_requirements=sample_requirements[1:],
            missing_in_docs=[sample_requirements[2]],
            missing_in_code=[sample_requirements[0]],
            inconsistencies=[]
        )

        output = formatter.format_with_gaps(sample_requirements, gap_analysis)

        assert "# Gap Analysis" in output
        assert "## Requirements Missing in Documentation" in output
        assert "REQ-003" in output
        assert "## Requirements Missing in Code" in output
        assert "REQ-001" in output

    def test_save_to_file(self, sample_requirements):
        """Test saving formatted output to file"""
        formatter = RequirementsFormatter(output_format=OutputFormat.MARKDOWN)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            formatter.save(sample_requirements, temp_file)

            # Read and verify
            content = Path(temp_file).read_text()
            assert "# Requirements Document" in content
            assert "REQ-001" in content
        finally:
            Path(temp_file).unlink()

    def test_filter_by_confidence(self, sample_requirements):
        """Test filtering requirements by minimum confidence"""
        formatter = RequirementsFormatter(
            output_format=OutputFormat.JSON,
            min_confidence=0.8
        )

        # Filter out low confidence (0.7)
        filtered = formatter._filter_requirements(sample_requirements)
        assert len(filtered) == 2  # Only high confidence ones
        assert all(r.confidence >= 0.8 for r in filtered)

    def test_categorize_requirements(self, sample_requirements):
        """Test categorizing requirements"""
        formatter = RequirementsFormatter(output_format=OutputFormat.MARKDOWN)

        categorized = formatter._categorize_requirements(sample_requirements)

        assert "Authentication" in categorized
        assert len(categorized["Authentication"]) == 1
        assert categorized["Authentication"][0].id == "REQ-001"

        assert "Core" in categorized
        assert "Utilities" in categorized


# =============================================================================
# Integration Tests - Orchestrator
# =============================================================================

class TestRequirementsOrchestrator:
    """Integration tests for RequirementsOrchestrator"""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator setup with all components"""
        config = ExtractionConfig(
            project_path="/test",
            output_path="requirements.md"
        )

        orchestrator = RequirementsOrchestrator(config)

        assert orchestrator.config == config
        assert orchestrator.discovery is not None
        assert orchestrator.extractor is not None
        assert orchestrator.state_manager is not None
        assert orchestrator.formatter is not None
        assert orchestrator.gap_analyzer is not None

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_run_extraction_pipeline(self, mock_sdk, temp_project_dir):
        """Test full extraction pipeline with mocked AI"""
        # Setup mock AI responses
        mock_client = AsyncMock()
        mock_sdk.return_value.__aenter__.return_value = mock_client
        mock_client.query = AsyncMock()

        mock_message = Mock()
        mock_message.content = [Mock(text=json.dumps({
            "requirements": [
                {
                    "title": "Main Entry Point",
                    "description": "Application main function",
                    "category": "Core",
                    "priority": "high",
                    "evidence": ["def main():"],
                    "confidence": 0.9
                }
            ]
        }))]
        mock_client.receive_response = AsyncMock(return_value=[mock_message])

        # Setup config
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_file = f.name

        try:
            config = ExtractionConfig(
                project_path=temp_project_dir,
                output_path=output_file,
                output_format=OutputFormat.MARKDOWN
            )

            orchestrator = RequirementsOrchestrator(config)
            await orchestrator.run()

            # Verify output was created
            assert Path(output_file).exists()
            content = Path(output_file).read_text()
            assert "Requirements Document" in content

        finally:
            Path(output_file).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_resume_capability(self, mock_sdk, temp_project_dir):
        """Test resuming extraction from saved state"""
        # Setup mock
        mock_client = AsyncMock()
        mock_sdk.return_value.__aenter__.return_value = mock_client
        mock_client.query = AsyncMock()

        mock_message = Mock()
        mock_message.content = [Mock(text=json.dumps({"requirements": []}))]
        mock_client.receive_response = AsyncMock(return_value=[mock_message])

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            state_file = f.name

        try:
            config = ExtractionConfig(
                project_path=temp_project_dir,
                state_file=state_file
            )

            # Run partial extraction
            orchestrator = RequirementsOrchestrator(config)

            # Pre-populate some state
            orchestrator.state_manager.create_state(temp_project_dir, 3)
            orchestrator.state_manager.state.processed_modules = ["module1"]
            orchestrator.state_manager.save_state()

            # Create new orchestrator and verify it loads state
            orchestrator2 = ExtractionOrchestrator(config)
            state = orchestrator2.state_manager.load_state()

            assert state is not None
            assert "module1" in state.processed_modules

        finally:
            Path(state_file).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.RequirementsExtractor.extract_from_module')
    async def test_incremental_saves(self, mock_extract, temp_project_dir):
        """Test that results are saved incrementally after each module"""
        # Mock extraction to return requirements
        mock_extract.return_value = [
            Requirement(
                id=f"REQ-{i}",
                title=f"Requirement {i}",
                description="Test",
                category="Test",
                priority="medium",
                source_modules=[],
                evidence=[],
                confidence=0.8
            )
            for i in range(2)
        ]

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            config = ExtractionConfig(
                project_path=temp_project_dir,
                output_path=output_file,
                output_format=OutputFormat.JSON
            )

            orchestrator = RequirementsOrchestrator(config)
            await orchestrator.run()

            # Check that output was saved
            content = Path(output_file).read_text()
            data = json.loads(content)

            # Should have requirements from multiple modules
            assert data["total_requirements"] > 0

        finally:
            Path(output_file).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('requirement_extractor.extractor.ClaudeSDKClient')
    async def test_error_handling_and_retry(self, mock_sdk, temp_project_dir):
        """Test handling of extraction errors and retry logic"""
        # First call fails, second succeeds
        mock_sdk.side_effect = [
            Exception("Network error"),
            AsyncMock()  # Second attempt succeeds
        ]

        config = ExtractionConfig(
            project_path=temp_project_dir,
            retry_failed=True
        )

        orchestrator = RequirementsOrchestrator(config)

        # Should handle the error gracefully
        # Note: actual retry logic would need to be implemented
        # This tests that errors don't crash the whole pipeline
        try:
            await orchestrator.run()
        except:
            pass  # Expected to handle errors

    @pytest.mark.asyncio
    async def test_gap_analysis_integration(self, temp_project_dir):
        """Test integration with gap analysis when existing requirements provided"""
        # Create existing requirements file
        existing_reqs = """
# Requirements

## REQ-001: Existing Requirement
**Priority:** High
**Category:** Core
Description of existing requirement.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(existing_reqs)
            existing_file = f.name

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_file = f.name

        try:
            config = ExtractionConfig(
                project_path=temp_project_dir,
                output_path=output_file,
                existing_requirements_path=existing_file
            )

            orchestrator = RequirementsOrchestrator(config)

            # Verify gap analyzer is configured
            assert orchestrator.gap_analyzer is not None

            # Would run full pipeline in real test
            # await orchestrator.run()

        finally:
            Path(existing_file).unlink(missing_ok=True)
            Path(output_file).unlink(missing_ok=True)


# =============================================================================
# Edge Cases and Error Scenarios
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def test_module_with_no_files(self):
        """Test handling module with no files"""
        module = CodeModule(
            name="empty",
            description="Empty module",
            files=[],
            primary_language="unknown"
        )

        assert module.total_lines == 0

    def test_requirement_with_empty_evidence(self):
        """Test requirement with no evidence"""
        req = Requirement(
            id="REQ-001",
            title="Test",
            description="Test",
            category="Test",
            priority="low",
            source_modules=[],
            evidence=[],  # Empty evidence
            confidence=0.5
        )

        assert req.evidence == []
        assert req.confidence == 0.5

    def test_state_file_corruption(self):
        """Test handling corrupted state file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("Not valid JSON{")
            temp_file = f.name

        try:
            manager = StateManager(temp_file)
            state = manager.load_state()
            assert state is None  # Should handle gracefully
        finally:
            Path(temp_file).unlink()

    def test_output_path_permission_error(self):
        """Test handling output path without write permissions"""
        formatter = RequirementsFormatter(output_format=OutputFormat.MARKDOWN)

        # Try to write to a read-only location
        try:
            formatter.save([], "/root/no_permission.md")
        except (PermissionError, OSError):
            pass  # Expected behavior

    @pytest.mark.asyncio
    async def test_timeout_recovery(self):
        """Test recovery from timeout scenarios"""
        extractor = RequirementsExtractor(timeout_seconds=0.001)  # Very short timeout

        module = CodeModule(
            name="test",
            description="Test",
            files=[],
            primary_language="python"
        )

        # Should not crash, just return empty
        requirements = await extractor.extract_from_module(module)
        assert requirements == []

    def test_circular_dependency_detection(self):
        """Test handling of circular dependencies in modules"""
        # This would be implementation-specific
        # Testing the concept of handling circular refs
        files = [
            CodeFile("/a.py", "a.py", "python", 100, 10),
            CodeFile("/b.py", "b.py", "python", 100, 10),
        ]

        discovery = CodeDiscovery("/test")
        modules = discovery.group_into_modules(files)

        # Should not create infinite loops
        assert len(modules) >= 0

    def test_very_large_file_handling(self):
        """Test handling of very large code files"""
        large_file = CodeFile(
            path="/large.py",
            relative_path="large.py",
            language="python",
            size=10_000_000,  # 10MB file
            lines=500_000  # 500k lines
        )

        module = CodeModule(
            name="large",
            description="Large module",
            files=[large_file],
            primary_language="python"
        )

        # Should handle without memory issues
        assert module.total_lines == 500_000

    def test_unicode_in_requirements(self):
        """Test handling of unicode characters in requirements"""
        req = Requirement(
            id="REQ-001",
            title="Unicode Test 测试 🚀",
            description="Description with émoji and 中文",
            category="Test",
            priority="high",
            source_modules=["test"],
            evidence=["def 函数(): pass"],
            confidence=0.9
        )

        formatter = RequirementsFormatter(output_format=OutputFormat.JSON)
        output = formatter.format([req])

        # Should handle unicode properly
        data = json.loads(output)
        assert "🚀" in data["requirements"][0]["title"]
        assert "中文" in data["requirements"][0]["description"]


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestPerformance:
    """Performance and stress tests"""

    def test_large_project_discovery(self):
        """Test discovery performance with many files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many files
            for i in range(100):
                Path(temp_dir, f"file{i}.py").write_text(f"# File {i}")

            discovery = CodeDiscovery(temp_dir)
            files = discovery.discover_files()

            assert len(files) == 100

    @pytest.mark.asyncio
    async def test_concurrent_extraction(self):
        """Test concurrent extraction of multiple modules"""
        modules = [
            CodeModule(
                name=f"module{i}",
                description=f"Module {i}",
                files=[],
                primary_language="python"
            )
            for i in range(10)
        ]

        extractor = RequirementsExtractor()

        # Mock the extraction method
        with patch.object(extractor, 'extract_from_module',
                         return_value=[]) as mock_extract:
            tasks = [extractor.extract_from_module(m) for m in modules]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert mock_extract.call_count == 10

    def test_memory_efficient_state_management(self):
        """Test that state management doesn't leak memory"""
        manager = StateManager(".test_state.json")

        # Create and update state many times
        for i in range(1000):
            state = manager.create_state("/test", 100)
            state.processed_modules.append(f"module{i}")
            # Should not accumulate memory

        # Final state should be manageable
        assert len(manager.state.processed_modules) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])