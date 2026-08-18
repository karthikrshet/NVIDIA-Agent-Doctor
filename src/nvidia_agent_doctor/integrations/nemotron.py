"""NVIDIA Agent Doctor — Nemotron heuristic integration."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


def detect_nemotron() -> dict[str, Any]:
    """
    Heuristic detection of Nemotron / NeMo environments.
    Never raises. Results are clearly labeled as heuristic.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "nemo_installed": False,
        "nemo_version": None,
        "nim_available": False,
        "cli_available": False,
        "detection_method": "heuristic",
        "note": (
            "Nemotron detection is heuristic. We check for NeMo, NIM, "
            "and related environment indicators."
        ),
    }

    # Check for NeMo Python package
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            nemo_ver = version("nemo_toolkit")
            result["nemo_installed"] = True
            result["nemo_version"] = nemo_ver
            result["installed"] = True
        except PackageNotFoundError:
            pass
    except Exception:
        pass

    # Try nemo import directly
    if not result["nemo_installed"]:
        try:
            import nemo  # type: ignore[import]
            result["nemo_installed"] = True
            result["nemo_version"] = getattr(nemo, "__version__", None)
            result["installed"] = True
        except ImportError:
            pass
        except Exception:
            pass

    # Check NIM (NVIDIA Inference Microservice)
    nim_env_vars = ["NIM_MODEL_NAME", "NIM_MODEL_PATH", "NVIDIA_NIM_CONFIG"]
    if any(os.environ.get(v) for v in nim_env_vars):
        result["nim_available"] = True
        result["installed"] = True

    nim_cli = shutil.which("nim")
    if nim_cli:
        result["nim_available"] = True
        result["nim_cli"] = nim_cli
        result["installed"] = True

    # Check NGC CLI (NVIDIA GPU Cloud)
    ngc_cli = shutil.which("ngc")
    if ngc_cli:
        result["ngc_cli"] = ngc_cli
        result["installed"] = True

    return result


def detect_nemoclaw() -> dict[str, Any]:
    """
    Heuristic detection of NemoClaw environments.
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "cli_available": False,
        "detection_method": "heuristic",
        "note": (
            "NemoClaw detection is heuristic based on CLI binary and "
            "environment variable presence."
        ),
    }

    # Check for nemoclaw binary
    nemoclaw_cli = shutil.which("nemoclaw")
    if not nemoclaw_cli:
        nemoclaw_cli = shutil.which("nemo-claw")
    if nemoclaw_cli:
        result["installed"] = True
        result["cli_available"] = True
        result["cli_path"] = nemoclaw_cli
        result["version"] = _get_cli_version(nemoclaw_cli)

    # Check environment variables
    env_vars = ["NEMOCLAW_HOME", "NEMOCLAW_CONFIG", "NEMO_CLAW_CONFIG"]
    if any(os.environ.get(v) for v in env_vars):
        result["installed"] = True

    # Try package import
    try:
        import nemoclaw  # type: ignore[import]
        result["installed"] = True
        result["version"] = getattr(nemoclaw, "__version__", None)
    except ImportError:
        pass
    except Exception:
        pass

    return result


def _get_cli_version(binary: str) -> str | None:
    for flag in ["--version", "version"]:
        try:
            proc = subprocess.run(
                [binary, flag], capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0:
                import re
                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", proc.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass
    return None
