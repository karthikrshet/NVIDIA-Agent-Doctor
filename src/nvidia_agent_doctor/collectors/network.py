"""NVIDIA Agent Doctor — Network connectivity collector."""

from __future__ import annotations

import socket
import urllib.request
from typing import NamedTuple, cast
from urllib.parse import urlparse


class NetworkCheck(NamedTuple):
    host: str
    reachable: bool
    latency_ms: float | None
    error: str | None


_DEFAULT_HOSTS = [
    ("8.8.8.8", 53),  # Google DNS
    ("1.1.1.1", 53),  # Cloudflare DNS
]

_DEFAULT_URLS = [
    "https://pypi.org",
    "https://huggingface.co",
]


def check_basic_connectivity(timeout: float = 5.0) -> dict[str, bool]:
    """Check basic network connectivity. Returns a dict of check_name -> reachable."""
    results: dict[str, bool] = {}

    # DNS / raw socket checks
    for host, port in _DEFAULT_HOSTS:
        key = f"{host}:{port}"
        results[key] = _check_socket(host, port, timeout)

    return results


def check_url_reachability(
    urls: list[str] | None = None,
    timeout: float = 10.0,
) -> dict[str, bool]:
    """Check if URLs are reachable (HEAD request). Never raises."""
    if urls is None:
        urls = _DEFAULT_URLS
    results: dict[str, bool] = {}
    for url in urls:
        results[url] = _check_url(url, timeout)
    return results


def _check_socket(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, OSError):
        return False


def _check_url(url: str, timeout: float) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    try:
        req = urllib.request.Request(url, method="HEAD")  # noqa: S310 -- HTTPS is validated above.
        req.add_header("User-Agent", "nvidia-agent-doctor/0.1.0")
        with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310 -- HTTPS-only request.
            return True
    except Exception:
        return False


def get_local_ip() -> str | None:
    """Get the primary local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return cast(str, s.getsockname()[0])
    except Exception:
        return None
