"""Read-only Kubernetes and NVIDIA GPU Operator discovery."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, cast

from nvidia_agent_doctor.security.credentials import redact_data, redact_text

_KUBECTL_TIMEOUT_SECONDS = 10
_GPU_OPERATOR_SELECTOR = "app.kubernetes.io/name=nvidia-gpu-operator"


def scan_cluster(allow_cluster_access: bool = False) -> dict[str, Any]:
    """Collect minimal Kubernetes evidence without exposing kubeconfig contents.

    Network access through kubectl is disabled unless the caller explicitly
    enables it. Commands use fixed argument vectors, have a bounded timeout,
    and only retain node names, readiness, GPU capacity, and pod phase counts.
    """
    kubectl = shutil.which("kubectl")
    if kubectl is None:
        return {"status": "not_installed", "cluster_accessed": False, "nodes": []}
    if not allow_cluster_access:
        return {
            "status": "access_not_requested",
            "cluster_accessed": False,
            "nodes": [],
            "recommendation": "Re-run with --allow-cluster-access to query the configured Kubernetes context.",
        }

    nodes_result = _run_kubectl(kubectl, ["get", "nodes", "-o", "json"])
    if nodes_result is None:
        return {"status": "unreachable", "cluster_accessed": True, "nodes": []}

    nodes = _parse_nodes(nodes_result)
    operator_result = _run_kubectl(
        kubectl,
        ["get", "pods", "--all-namespaces", "--selector", _GPU_OPERATOR_SELECTOR, "-o", "json"],
    )
    return cast(
        dict[str, Any],
        redact_data(
            {
                "status": "ok",
                "cluster_accessed": True,
                "nodes": nodes,
                "gpu_operator": _parse_operator_pods(operator_result) if operator_result else {"detected": False},
            }
        ),
    )


def _run_kubectl(kubectl: str, args: list[str]) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            [kubectl, *args],
            capture_output=True,
            text=True,
            timeout=_KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return data if isinstance(data, dict) else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _parse_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata", {})
        status = item.get("status", {})
        capacity = status.get("capacity", {}) if isinstance(status, dict) else {}
        ready = any(
            condition.get("type") == "Ready" and condition.get("status") == "True"
            for condition in status.get("conditions", [])
            if isinstance(condition, dict)
        )
        nodes.append(
            {
                "name": redact_text(str(metadata.get("name", "unknown"))),
                "ready": ready,
                "gpu_capacity": capacity.get("nvidia.com/gpu", "0"),
            }
        )
    return nodes


def _parse_operator_pods(payload: dict[str, Any]) -> dict[str, Any]:
    phases: dict[str, int] = {}
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        status = item.get("status", {})
        phase = status.get("phase", "Unknown") if isinstance(status, dict) else "Unknown"
        phases[str(phase)] = phases.get(str(phase), 0) + 1
    return {"detected": bool(phases), "pod_phases": phases}
