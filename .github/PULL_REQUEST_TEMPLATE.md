## Summary

Describe the user-visible change and why it is needed.

## Verification

- [ ] Added or updated focused tests
- [ ] `pytest tests/ -v --tb=short -m "not gpu and not slow" --no-cov`
- [ ] `ruff format --check src/ tests/` and `ruff check src/ tests/`
- [ ] `mypy src/nvidia_agent_doctor/`
- [ ] Documentation and changelog updated where applicable

## Safety and evidence

- [ ] No secrets, private paths, hostnames, UUIDs, or customer data are included
- [ ] New NVIDIA compatibility claims cite authoritative evidence or are labeled heuristic/unverified
- [ ] New network, container, benchmark, or host-changing behavior is explicit opt-in and bounded
