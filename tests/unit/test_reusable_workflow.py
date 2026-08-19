"""Regression checks for the reusable GitHub Actions workflow contract."""

from pathlib import Path

_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "nvidia-agent-doctor.yml"
_CI_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"
_GPU_WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "gpu-validation.yml"


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


def test_reusable_workflow_does_not_upload_caller_reports_or_hide_scan_failures() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "actions/upload-artifact" not in workflow
    assert "nad security scan --json > nad-security.json || true" not in workflow
    assert 'nad skills scan "$SKILLS_PATH" --json > nad-skills.json || true' not in workflow


def test_ci_builds_and_installs_the_distribution_wheel() -> None:
    workflow = _CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m build" in workflow
    assert "python -m pip install --force-reinstall dist/*.whl" in workflow


def test_manual_gpu_workflow_is_trusted_bounded_and_no_artifact() -> None:
    workflow = _GPU_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "runs-on: [self-hosted, linux, x64, gpu]" in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "pytest tests/hardware -m gpu" in workflow
    assert '--max-memory-mb "$NAD_BENCHMARK_MAX_MEMORY_MB"' in workflow
    assert '--timeout-seconds "$NAD_BENCHMARK_TIMEOUT_SECONDS"' in workflow
    assert "actions/upload-artifact" not in workflow
