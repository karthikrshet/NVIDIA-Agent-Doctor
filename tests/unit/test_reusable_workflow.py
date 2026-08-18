"""Regression checks for the reusable GitHub Actions workflow contract."""

from pathlib import Path

_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "nvidia-agent-doctor.yml"
_CI_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"


def test_reusable_workflow_installs_its_own_pinned_source() -> None:
    """A workflow caller must never cause us to install an unrelated project."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "repository: karthikrshet/NVIDIA-Agent-Doctor" in workflow
    assert "ref: ${{ github.workflow_sha }}" in workflow
    assert "path: nvidia-agent-doctor" in workflow
    assert "pip install -e nvidia-agent-doctor" in workflow


def test_reusable_workflow_uses_the_report_canonical_health_score() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "data['summary']['overall_score']" in workflow
    assert "# Calculate score from sections" not in workflow


def test_ci_builds_and_installs_the_distribution_wheel() -> None:
    workflow = _CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m build" in workflow
    assert "python -m pip install --force-reinstall dist/*.whl" in workflow
