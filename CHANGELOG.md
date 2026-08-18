# Changelog

All notable changes to NVIDIA Agent Doctor are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

---

## [0.1.0] - 2024-08-19

### Added

**Core:**
- `nad doctor` — Full environment diagnostic command
- `nad gpu info|health` — NVIDIA GPU detection and health
- `nad cuda check` — CUDA toolkit and runtime diagnostics
- `nad security scan` — Baseline security analysis
- `nad compatibility check` — Cross-component compatibility
- `nad mcp scan` — MCP server configuration analysis
- `nad skills scan` — Agent skills heuristic scanner
- `nad openshell diagnose` — OpenShell heuristic detection
- `nad nemotron check` — Nemotron / NeMo detection
- `nad benchmark run` — Opt-in GPU and memory benchmarks
- `nad report generate` — JSON, Markdown, and HTML reports

**Integrations:**
- NVIDIA GPU via `nvidia-smi` (XML parsing with CSV fallback)
- CUDA toolkit via `nvcc` and environment variables
- PyTorch (version, CUDA availability, device count, BF16/FP16 detection)
- TensorRT (import health, builder/runtime checks)
- Triton Inference Server (binary, process, container detection)
- OpenShell (heuristic: CLI, env vars, config files, process)
- Nemotron / NeMo (heuristic: package, NIM CLI, NGC CLI)
- MCP servers (JSON config discovery with secret redaction)
- Docker (daemon, NVIDIA container runtime)

**Security:**
- API key/token redaction (OpenAI, NVIDIA, HuggingFace, GitHub, JWT formats)
- Environment variable secret scanning
- SSH key permission checks
- File permission analysis
- MCP server security analysis (shell execution, exposed secrets, insecure HTTP)
- Agent skills heuristic scanner (dangerous commands, exfiltration patterns)
- Cross-skill risk graph (filesystem→network, credentials→network paths)

**Reports:**
- Rich terminal output with health score bar
- Machine-readable JSON with secret redaction
- Markdown report with tables
- Self-contained dark-mode HTML report

**CI/CD:**
- Multi-OS GitHub Actions CI (Linux, Windows, macOS)
- Reusable `nvidia-agent-doctor.yml` workflow
- Health score output for downstream jobs

**Documentation:**
- README with features, CLI reference, architecture, security/privacy
- Getting started guide
- SECURITY.md with threat model and responsible disclosure
- Example skills and MCP configs

### Exit Codes
- `0` = healthy
- `1` = warnings
- `2` = errors
- `3` = security issues (HIGH or CRITICAL)
- `4` = invalid configuration

### Notes
- No telemetry, no cloud upload, no secret collection
- All optional components gracefully handled (NOT_INSTALLED, not failure)
- Heuristic detections clearly labeled throughout
- No NVIDIA compatibility rules invented — only detected versions compared

---

*NVIDIA Agent Doctor is an independent open-source project and is not affiliated with NVIDIA Corporation.*
