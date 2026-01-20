"""End-to-end test: Guide teaches beginner about REST APIs.

Simulates complete meta-delegation workflow where guide persona
teaches a beginner about REST API concepts through delegation.
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation import run_meta_delegation
except ImportError:
    pytest.skip("Meta-delegation not implemented yet", allow_module_level=True)


@pytest.mark.e2e
@pytest.mark.requires_platform
class TestGuideTeachesBeginner:
    """E2E test for guide persona teaching scenario."""

    @pytest.fixture
    def teaching_goal(self):
        """Define teaching goal."""
        return """
Teach a beginner developer about REST APIs by creating a simple example
with clear explanations. Cover:
- What REST APIs are
- HTTP methods (GET, POST, PUT, DELETE)
- Status codes
- A working example with FastAPI
- Step-by-step tutorial
"""

    @pytest.fixture
    def teaching_success_criteria(self):
        """Define success criteria for teaching."""
        return """
- Has tutorial document explaining REST concepts clearly
- Has working code example with comments
- Example demonstrates GET and POST endpoints
- Has README with setup instructions
- Code is beginner-friendly and well-documented
- Includes examples of API requests
"""

    @pytest.fixture
    def mock_subprocess_teaching(self):
        """Mock subprocess for teaching scenario."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 99999
            mock_process.poll.side_effect = [None, None, None, 0]  # Runs then completes
            mock_process.returncode = 0
            mock_process.communicate.return_value = (
                "Teaching session completed successfully",
                "",
            )
            mock_popen.return_value = mock_process
            yield mock_popen

    @pytest.fixture
    def mock_teaching_evidence(self, tmp_path):
        """Create mock evidence from teaching session."""
        workspace = tmp_path / "teaching_workspace"
        workspace.mkdir()

        # Tutorial document
        (workspace / "REST_API_TUTORIAL.md").write_text(
            """
# REST API Tutorial for Beginners

## What is a REST API?

A REST API (Representational State Transfer Application Programming Interface)
is a way for programs to communicate over the internet using HTTP.

## HTTP Methods

- **GET**: Retrieve data
- **POST**: Create new data
- **PUT**: Update existing data
- **DELETE**: Remove data

## Status Codes

- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Server Error

## Let's Build an Example!

See `example_api.py` for a working implementation.
"""
        )

        # Example code with extensive comments
        (workspace / "example_api.py").write_text(
            '''
"""
Simple REST API Example for Beginners
This API manages a list of books.
"""

from fastapi import FastAPI, HTTPException
from typing import List, Dict

# Create FastAPI application
app = FastAPI(title="Book API Tutorial")

# In-memory database (just a list for simplicity)
books: List[Dict] = [
    {"id": 1, "title": "Python Basics", "author": "John Doe"},
    {"id": 2, "title": "Web Development", "author": "Jane Smith"},
]

@app.get("/books")
def get_books():
    """
    GET /books - Retrieve all books

    This endpoint returns a list of all books in our database.
    Try it: http://localhost:8000/books
    """
    return {"books": books}

@app.post("/books")
def create_book(title: str, author: str):
    """
    POST /books - Create a new book

    This endpoint adds a new book to our database.
    We need: title and author
    """
    new_book = {
        "id": len(books) + 1,
        "title": title,
        "author": author
    }
    books.append(new_book)
    return {"message": "Book created!", "book": new_book}

# Run with: uvicorn example_api:app --reload
'''
        )

        # README with setup
        (workspace / "README.md").write_text(
            """
# REST API Tutorial - Getting Started

## Setup Instructions

1. Install Python (version 3.8 or higher)
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn
   ```

3. Run the server:
   ```bash
   uvicorn example_api:app --reload
   ```

4. Try the API:
   - Open browser: http://localhost:8000/docs
   - Test GET: http://localhost:8000/books

## Example Requests

### Get all books
```bash
curl http://localhost:8000/books
```

### Create a book
```bash
curl -X POST "http://localhost:8000/books?title=New Book&author=You"
```

## Next Steps

- Try adding PUT and DELETE endpoints
- Add error handling
- Connect to a real database
"""
        )

        # Example requests file
        (workspace / "example_requests.txt").write_text(
            """
# Example API Requests

## Get all books
GET http://localhost:8000/books

Expected response:
{
  "books": [
    {"id": 1, "title": "Python Basics", "author": "John Doe"},
    {"id": 2, "title": "Web Development", "author": "Jane Smith"}
  ]
}

## Create new book
POST http://localhost:8000/books?title=API Design&author=Teacher

Expected response:
{
  "message": "Book created!",
  "book": {"id": 3, "title": "API Design", "author": "Teacher"}
}
"""
        )

        return workspace

    @patch("amplihack.meta_delegation.orchestrator.MetaDelegationOrchestrator")
    def test_guide_creates_educational_content(
        self,
        mock_orchestrator,
        teaching_goal,
        teaching_success_criteria,
        mock_teaching_evidence,
    ):
        """Test guide persona creates educational tutorial content."""
        from datetime import datetime

        from amplihack.meta_delegation import MetaDelegationResult
        from amplihack.meta_delegation.evidence_collector import EvidenceItem

        # Mock orchestrator to return educational results
        mock_orch_instance = Mock()

        evidence = [
            EvidenceItem(
                type="documentation",
                path=str(mock_teaching_evidence / "REST_API_TUTORIAL.md"),
                content=(mock_teaching_evidence / "REST_API_TUTORIAL.md").read_text(),
                excerpt="# REST API Tutorial...",
                size_bytes=1000,
                timestamp=datetime.now(),
                metadata={"format": "markdown"},
            ),
            EvidenceItem(
                type="code_file",
                path=str(mock_teaching_evidence / "example_api.py"),
                content=(mock_teaching_evidence / "example_api.py").read_text(),
                excerpt='"""Simple REST API...',
                size_bytes=2000,
                timestamp=datetime.now(),
                metadata={"language": "python"},
            ),
            EvidenceItem(
                type="documentation",
                path=str(mock_teaching_evidence / "README.md"),
                content=(mock_teaching_evidence / "README.md").read_text(),
                excerpt="# REST API Tutorial...",
                size_bytes=500,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        mock_result = MetaDelegationResult(
            status="SUCCESS",
            success_score=95,
            evidence=evidence,
            execution_log="Guide session completed. Tutorial created successfully.",
            duration_seconds=180.5,
            persona_used="guide",
            platform_used="claude-code",
            failure_reason=None,
            partial_completion_notes=None,
            subprocess_pid=99999,
            test_scenarios=None,
        )

        mock_orch_instance.orchestrate_delegation.return_value = mock_result
        mock_orchestrator.return_value = mock_orch_instance

        # Run delegation
        result = run_meta_delegation(
            goal=teaching_goal,
            success_criteria=teaching_success_criteria,
            persona_type="guide",
            platform="claude-code",
        )

        # Assertions
        assert result.status == "SUCCESS"
        assert result.persona_used == "guide"
        assert result.success_score >= 90

        # Verify educational content
        assert len(result.evidence) >= 3

        # Check for tutorial document
        tutorials = [e for e in result.evidence if "TUTORIAL" in e.path]
        assert len(tutorials) > 0

        tutorial_content = tutorials[0].content
        assert "REST API" in tutorial_content
        assert "beginner" in tutorial_content.lower()
        assert "HTTP" in tutorial_content

        # Check for well-commented code
        code_files = [e for e in result.evidence if e.type == "code_file"]
        assert len(code_files) > 0

        code_content = code_files[0].content
        assert '"""' in code_content or "#" in code_content  # Has comments
        assert "def" in code_content  # Has functions

        # Check for setup instructions
        readmes = [e for e in result.evidence if "README" in e.path]
        assert len(readmes) > 0

        readme_content = readmes[0].content
        assert "install" in readme_content.lower()
        assert "setup" in readme_content.lower() or "getting started" in readme_content.lower()

    @patch("amplihack.meta_delegation.orchestrator.MetaDelegationOrchestrator")
    def test_guide_tutorial_is_beginner_friendly(
        self, mock_orchestrator, teaching_goal, teaching_success_criteria, mock_teaching_evidence
    ):
        """Test guide creates beginner-friendly content."""
        from datetime import datetime

        from amplihack.meta_delegation import MetaDelegationResult
        from amplihack.meta_delegation.evidence_collector import EvidenceItem

        mock_orch_instance = Mock()

        # Load evidence
        evidence = []
        for file in mock_teaching_evidence.glob("*.md"):
            evidence.append(
                EvidenceItem(
                    type="documentation",
                    path=str(file),
                    content=file.read_text(),
                    excerpt=file.read_text()[:200],
                    size_bytes=len(file.read_text()),
                    timestamp=datetime.now(),
                    metadata={},
                )
            )

        for file in mock_teaching_evidence.glob("*.py"):
            evidence.append(
                EvidenceItem(
                    type="code_file",
                    path=str(file),
                    content=file.read_text(),
                    excerpt=file.read_text()[:200],
                    size_bytes=len(file.read_text()),
                    timestamp=datetime.now(),
                    metadata={},
                )
            )

        mock_result = MetaDelegationResult(
            status="SUCCESS",
            success_score=92,
            evidence=evidence,
            execution_log="Educational content generated",
            duration_seconds=150.0,
            persona_used="guide",
            platform_used="claude-code",
            failure_reason=None,
            partial_completion_notes=None,
            subprocess_pid=99999,
            test_scenarios=None,
        )

        mock_orch_instance.orchestrate_delegation.return_value = mock_result
        mock_orchestrator.return_value = mock_orch_instance

        result = run_meta_delegation(
            goal=teaching_goal,
            success_criteria=teaching_success_criteria,
            persona_type="guide",
        )

        # Check beginner-friendly characteristics
        all_content = " ".join([e.content for e in result.evidence])

        # Should explain concepts clearly
        assert any(
            phrase in all_content.lower()
            for phrase in ["what is", "explanation", "simple", "beginner", "tutorial"]
        )

        # Should have examples
        assert "example" in all_content.lower()

        # Code should have extensive comments
        code_evidence = [e for e in result.evidence if e.type == "code_file"]
        if code_evidence:
            code = code_evidence[0].content
            comment_lines = [line for line in code.split("\n") if "#" in line or '"""' in line]
            # At least 20% of lines should be comments
            total_lines = len([line for line in code.split("\n") if line.strip()])
            assert len(comment_lines) >= total_lines * 0.2
