# Changelog

All notable changes to NVIDIA Agent Doctor are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Offline Ed25519 detached-signature verification for local agent skills.
- Dependabot coverage and structured bug, feature, security-routing, and pull-request templates for sustainable public maintenance.
- `nad report compare` to detect health-score, diagnostic-error, and high-security regressions between two local NAD JSON reports.
- `nad docker gpu-check` for an explicit, bounded validation of NVIDIA GPU visibility inside an already-local Docker CUDA image.
- A README hero banner with an adjacent independent-project disclaimer.
- `nad tensorrt check` for local TensorRT Python binding, runtime, and builder probes.
- `nad triton check` for local Triton indicators and an explicit loopback-only readiness check.
- Sanitized real-hardware evidence for an RTX 3050 with CUDA-enabled PyTorch.
- Regression coverage for benchmark cleanup, TensorRT error redaction, NIM/Triton hostile URLs, and runtime CLI behavior.
- A manually dispatched, self-hosted GPU validation workflow that requires measured hardware evidence and never uploads host reports.

### Changed

- Distribution CI now smoke-tests clean wheel and source-distribution installs.
- Remove Typer's obsolete `all` extra; Rich is already a direct runtime dependency.
- Removed the unused pre-Python-3.11 TOML backport dependency; the project requires Python 3.11 or newer.
- The README now contains an evidence-based validation ledger that separates verified hardware paths from unavailable or unverified deployment targets.
- The default doctor now reads PyTorch package metadata without importing the runtime; `--deep-pytorch` explicitly enables CUDA device and bounded compute validation.
- Driver-reported CUDA maximums are now distinct from local CUDA runtime evidence, preventing `nvidia-smi` capability output from being presented as an installed runtime.
- Configuration now accepts only settings consumed by the CLI; unsupported legacy/no-op keys fail validation instead of being accepted silently.
- The README now distinguishes real integrations, static/heuristic detection, and hardware-validated evidence.
- The doctor command reuses its PyTorch discovery result during CUDA collection to avoid redundant optional-runtime probing.
- Section commands, report generation, MCP scans, and skill scans now return documented warning, error, and high-security exit codes.

### Fixed

- TensorRT detection no longer treats PyTorch CUDA availability as proof of TensorRT/CUDA support-matrix compatibility.
- Benchmark and PyTorch validation errors are redacted and release GPU cache references on all handled paths.
- Older NVIDIA-SMI installations that reject `--version` can still be detected through the documented GPU-listing probe.
- Local NIM and Triton readiness endpoints reject malformed, remote, credential-bearing, query-string, and fragment URLs.
- MCP findings, arguments, URLs, terminal output, and JSON output are redacted before rendering.
- Reusable workflows no longer upload caller diagnostic reports or suppress failed security and skills scans.

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
