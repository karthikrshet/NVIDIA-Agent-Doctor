# Contributing to NVIDIA Agent Doctor

Thank you for your interest in contributing! 🎉

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/karthikrshet/NVIDIA-Agent-Doctor.git`
3. Install in dev mode: `python -m pip install -e ".[dev]"`
4. Run tests: `pytest tests/ -m "not gpu"`

## Development Workflow

```bash
# Install pre-commit hooks
pre-commit install

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/

# Run tests
pytest tests/ -v -m "not gpu"
```

## What to Contribute

- **Bug reports** — Open a GitHub issue with reproduction steps
- **Bug fixes** — Fork, fix, test, PR
- **New component integrations** — Follow the pattern in `integrations/`
- **Compatibility rules** — Must cite authoritative NVIDIA documentation
- **Documentation** — Improvements always welcome
- **Tests** — More coverage is always better

GitHub provides structured bug and feature forms. Security reports must use the
private disclosure path in [SECURITY.md](SECURITY.md), never a public issue.

## Important Rules

1. **No hallucinated data** — Never add compatibility rules or benchmark numbers without authoritative sources
2. **No breaking changes** — Maintain backward compatibility for CLI flags and JSON schema
3. **Tests required** — All new features need tests
4. **Heuristics labeled** — Any heuristic detection must be clearly labeled as such
5. **Secret safety** — Never log or output secrets; all credential handling goes through `security/credentials.py`

## Code Style

We use `ruff` for linting and formatting. Run `ruff check --fix src/` before committing.

Type hints are required for all new code.

## Disclaimer

By contributing, you agree that your contributions are licensed under the Apache 2.0 license.

NVIDIA Agent Doctor is an independent project. Contributions should not imply official NVIDIA endorsement.
