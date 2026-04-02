from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "daily-code-metrics.md"
COMPILED_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "daily-code-metrics.lock.yml"


def test_source_workflow_removes_dataviz_import_from_required_path() -> None:
    source = SOURCE_WORKFLOW.read_text()

    assert "shared/python-dataviz.md" not in source
    # Keep the root-cause note explicit so regressions are obvious in review.
    assert "#3968" in source
    assert "root cause" in source.lower()
    assert "timed out" in source
    assert "chart generation" in source
    assert "package install" in source


def test_source_workflow_requires_bounded_no_install_success_path() -> None:
    source = SOURCE_WORKFLOW.read_text()

    assert "Do **not** install packages" in source
    assert "Do **not** generate charts" in source
    assert "Do **not** call `upload_asset`." in source
    assert "git rev-parse --is-shallow-repository" in source
    assert "data gaps" in source
    assert "required success path" in source
    assert "`push_repo_memory` safe output" in source
    assert "create_discussion" in source
    assert "Generate **6 high-quality charts**" not in source


def test_compiled_workflow_excludes_runtime_dataviz_import() -> None:
    compiled = COMPILED_WORKFLOW.read_text()

    assert "{{#runtime-import .github/workflows/shared/python-dataviz.md}}" not in compiled
    assert "{{#runtime-import .github/workflows/daily-code-metrics.md}}" in compiled
    assert "push_repo_memory" in compiled
