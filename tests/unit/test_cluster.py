"""Tests for read-only Kubernetes cluster diagnostics."""

from __future__ import annotations

from unittest.mock import patch

from nvidia_agent_doctor.cluster import scan_cluster


def test_cluster_scan_does_not_access_cluster_without_opt_in() -> None:
    with patch("nvidia_agent_doctor.cluster.shutil.which", return_value="kubectl"):
        with patch("nvidia_agent_doctor.cluster.subprocess.run") as run:
            result = scan_cluster()

    run.assert_not_called()
    assert result["status"] == "access_not_requested"
    assert result["cluster_accessed"] is False


def test_cluster_scan_parses_minimal_gpu_evidence() -> None:
    node_payload = {
        "items": [
            {
                "metadata": {"name": "gpu-node-1"},
                "status": {
                    "capacity": {"nvidia.com/gpu": "8"},
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
            }
        ]
    }
    operator_payload = {"items": [{"status": {"phase": "Running"}}]}
    with patch("nvidia_agent_doctor.cluster.shutil.which", return_value="kubectl"):
        with patch(
            "nvidia_agent_doctor.cluster._run_kubectl",
            side_effect=[node_payload, operator_payload],
        ):
            result = scan_cluster(allow_cluster_access=True)

    assert result["status"] == "ok"
    assert result["nodes"] == [{"name": "gpu-node-1", "ready": True, "gpu_capacity": "8"}]
    assert result["gpu_operator"] == {"detected": True, "pod_phases": {"Running": 1}}
