"""NVIDIA Agent Doctor — Checker plugin registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nvidia_agent_doctor.core.result import SectionResult

CheckerFn = Callable[..., SectionResult]

_registry: dict[str, CheckerFn] = {}


def register(name: str) -> Callable[[CheckerFn], CheckerFn]:
    """Decorator to register a checker function under a given name."""
    def decorator(fn: CheckerFn) -> CheckerFn:
        _registry[name] = fn
        return fn
    return decorator


def get_checker(name: str) -> CheckerFn | None:
    """Retrieve a registered checker by name."""
    return _registry.get(name)


def list_checkers() -> list[str]:
    """Return sorted list of all registered checker names."""
    return sorted(_registry.keys())


def run_checker(name: str, **kwargs: Any) -> SectionResult | None:
    """Run a registered checker, returning None if not found."""
    fn = get_checker(name)
    if fn is None:
        return None
    return fn(**kwargs)
