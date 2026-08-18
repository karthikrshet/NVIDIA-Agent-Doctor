# NVIDIA Agent Doctor 🩺

> **An independent open-source diagnostic, security, compatibility and benchmarking toolkit for NVIDIA AI-agent environments.**
>
> GPU • CUDA • OpenShell • NemoClaw • Nemotron • MCP • Agent Skills

[![CI](https://github.com/karthikrshet/nvidia-agent-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/karthikrshet/nvidia-agent-doctor/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/nvidia-agent-doctor.svg)](https://badge.fury.io/py/nvidia-agent-doctor)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

> ⚠️ **Disclaimer:** NVIDIA Agent Doctor is an **independent open-source project** and is **not affiliated with, endorsed by, or an official product of NVIDIA Corporation.**

---

## The Problem

Modern NVIDIA AI agent environments stack many layers:

```
NVIDIA GPU → Driver → CUDA → PyTorch / TensorRT → Triton → NeMo → Nemotron
    → OpenShell → NemoClaw → MCP Servers → Agent Skills → Network → Security
```

When something breaks, developers manually chase through all these layers.

**NVIDIA Agent Doctor gives you one command to inspect them all.**

---

## 30-Second Demo

```bash
pip install nvidia-agent-doctor
nad doctor
```

```
╭──────────────────────────────────────────────╮
│          NVIDIA AGENT DOCTOR                 │
│  Independent Open-Source Diagnostic Toolkit  │
╰──────────────────────────────────────────────╯

┌────────────────────────────┬──────────────────┐
│ System                     │  ✓  PASS         │
│ NVIDIA GPU                 │  ✓  PASS         │
│ CUDA                       │  ⚠  WARNING      │
│ PyTorch                    │  ✓  PASS         │
│ Docker                     │  ✓  PASS         │
│ Security                   │  ✓  PASS         │
│ Compatibility              │  ✓  PASS         │
│ TensorRT                   │  –  NOT_INSTALLED│
│ Triton                     │  –  NOT_INSTALLED│
│ OpenShell                  │  –  NOT_INSTALLED│
│ Nemotron                   │  –  NOT_INSTALLED│
└────────────────────────────┴──────────────────┘

╭──────────────────────────────────────────────╮
│ Diagnostic Summary                           │
│                                              │
│ Overall Health: 91/100  ██████████████████░░ │
│ Warnings:       1                            │
│ Critical Issues: 0                           │
│ Recommendations: 2                           │
╰──────────────────────────────────────────────╯

Recommendations:
  1. Set CUDA_HOME to your CUDA installation directory
  2. Install CUDA-enabled PyTorch for GPU workloads
```

---

## Features

| Feature | Status |
|---------|--------|
| GPU detection & health | ✅ v0.1 |
| CUDA diagnostics | ✅ v0.1 |
| PyTorch validation | ✅ v0.1 |
| Docker / container runtime | ✅ v0.1 |
| Security baseline scan | ✅ v0.1 |
| Cross-component compatibility | ✅ v0.1 |
| JSON / Markdown / HTML reports | ✅ v0.1 |
| OpenShell diagnostics | ✅ v0.1 (heuristic) |
| MCP server analysis | ✅ v0.1 |
| Agent Skills scanner | ✅ v0.1 |
| Cross-skill risk graph | ✅ v0.1 |
| Nemotron / NeMo detection | ✅ v0.1 (heuristic) |
| TensorRT detection | ✅ v0.1 (optional import heuristic) |
| Bounded benchmark engine | ✅ v0.1 (opt-in; measurement only) |
| GitHub Action | ✅ v0.1 |
| HTML dashboard | 🔜 v0.5 |
| Plugin system | 🔜 v0.4 |

---

## Installation

```bash
pip install nvidia-agent-doctor
```

**From source:**
```bash
git clone https://github.com/karthikrshet/nvidia-agent-doctor.git
cd nvidia-agent-doctor
pip install -e ".[dev]"
```

**Requirements:** Python 3.11+

---

## CLI Reference

### Core Commands

```bash
nad doctor                     # Full environment diagnostic
nad doctor --json              # Machine-readable JSON output
nad doctor --verbose           # Detailed output
nad doctor --fix               # Show remediation suggestions
nad doctor --auto-resolve      # Generate a review-only remediation plan
nad doctor --quiet             # Minimal output (CI-friendly)
```

### Component Commands

```bash
nad gpu info                   # Detailed GPU info
nad gpu health                 # GPU health checks
nad cuda check                 # CUDA installation check
nad cuda check --verbose       # With environment details
nad openshell diagnose         # OpenShell runtime diagnostics
nad nemotron check             # Nemotron / NeMo detection
nad nemotron benchmark --yes   # Opt-in Nemotron benchmark
```

### Security & Analysis

```bash
nad security scan              # Baseline security analysis
nad security leak-check        # Verify redaction regression probes locally
nad mcp scan                   # MCP server security analysis
nad mcp scan --config ./mcp.json  # With explicit config path
nad skills scan ./skills/      # Scan agent skills directory
nad skills scan . --risk-graph # Include cross-skill risk graph
nad skills verify ./SKILL.md   # Verify detached SHA-256 digest + SKILLCARD.yaml
nad test-agent ./skills --json # Static agent/MCP wiring preflight; executes nothing
nad compatibility check        # Cross-component compatibility
```

### Reports

```bash
nad report generate                    # Terminal report
nad report generate --format json      # JSON
nad report generate --format markdown  # Markdown
nad report generate --format html      # Self-contained HTML
nad report generate --format html --output report.html
nad report generate --format compliance-audit  # Evidence-oriented readiness mapping
```

### Benchmarks (opt-in only)

```bash
nad benchmark run              # GPU + system benchmark (confirmation required)
nad benchmark run --yes        # Skip confirmation
nad benchmark run --gpu-only   # GPU benchmark only
```

---

## Diagnostic Categories

| Status | Meaning |
|--------|---------|
| `PASS` | Component is healthy |
| `WARNING` | Potential issue detected, review recommended |
| `ERROR` | Critical issue requiring action |
| `NOT_INSTALLED` | Optional component not present (not a failure) |
| `NOT_APPLICABLE` | Check doesn't apply to this environment |
| `UNKNOWN` | Could not determine status |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | Warnings present |
| `2` | Errors present |
| `3` | Security issues (HIGH or CRITICAL) |
| `4` | Invalid configuration |

---

## Architecture

```
nvidia-agent-doctor/
├── cli/              # Typer CLI commands
├── core/             # Data models, severity, config
├── collectors/       # System, GPU, CUDA, Docker, Python, Network
├── integrations/     # Per-component adapters
├── analyzers/        # Health analysis logic
├── skills/           # SKILL.md parser and scanner
├── security/         # Credential detection, permissions, MCP/skills security
├── benchmark/        # Opt-in GPU benchmarks
└── reports/          # Terminal (Rich), JSON, Markdown, HTML
```

---

## Supported NVIDIA Technologies

| Technology | Detection | Diagnostics |
|-----------|-----------|-------------|
| NVIDIA GPU | ✅ nvidia-smi | ✅ VRAM, temp, utilization |
| NVIDIA Driver | ✅ | ✅ version |
| CUDA | ✅ nvcc, env vars | ✅ version compatibility |
| PyTorch | ✅ import | ✅ CUDA, compute test |
| TensorRT | ✅ import | ✅ builder/runtime |
| Triton IS | ✅ binary/process | ✅ status |
| NeMo / Nemotron | ✅ heuristic | ✅ package/NIM |
| OpenShell | ✅ heuristic | ✅ config, runtime |
| MCP | ✅ config scan | ✅ security analysis |
| Agent Skills | ✅ SKILL.md scan | ✅ static analysis |
| Docker | ✅ | ✅ NVIDIA runtime |

---

## Security & Privacy

**Privacy-first design:**
- ✅ **No telemetry** — all diagnostics are local-only
- ✅ **No cloud upload** — nothing leaves your machine
- ✅ **No secret collection** — known API-key, token, password, and credential formats are redacted at report boundaries
- ✅ **Read-only by default** — `nad doctor` never modifies your system

**Secret redaction:** Terminal, JSON, Markdown, HTML, MCP arguments, URLs, metadata, and handled exception messages pass through the same redaction boundary. The `nad security leak-check` command runs deterministic local regression probes; it is not a proof that every possible secret format is detectable.

**Remediation:** `nad doctor --auto-resolve` generates a platform-aware plan for human review. It never installs packages, changes drivers, or executes shell commands automatically.

**Heuristic security scanning:** The skills and MCP scanners use heuristic static analysis. They can produce false positives and false negatives. All findings require human review.

---

## Configuration

Create `.nvidia-agent-doctor.toml` in your project root:

```toml
[doctor]
strict = false  # true = mark optional-not-found as WARNING

[security]
enabled = true

[benchmark]
enabled = false  # Never runs during 'nad doctor'

[mcp]
enabled = true
config_paths = ["~/.mcp/config.json"]

[skills]
enabled = true
scan_depth = 3
```

---

## GitHub Actions

```yaml
# .github/workflows/ai-health.yml
name: AI Environment Health

on: [push, pull_request]

jobs:
  diagnose:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install nvidia-agent-doctor
      - run: nad doctor --json
      - run: nad security scan --json
      - run: nad skills scan ./skills/ --json
```

**Note:** Standard GitHub-hosted runners don't have NVIDIA GPUs. GPU-specific checks will show `NOT_INSTALLED`, which is expected and correct. Use self-hosted NVIDIA GPU runners for full hardware diagnostics.

---

## Limitations

- GPU diagnostics require `nvidia-smi` (NVIDIA driver installed)
- OpenShell, NemoClaw, and Nemotron detection is **heuristic** — results vary by installation method
- Skills scanner is **static analysis only** — cannot detect runtime behavior
- MCP scanner analyzes configuration, not live server behavior
- `nad test-agent` is a static preflight: it never starts an MCP server, invokes a skill, or calls a model
- `nad skills verify` supports a detached SHA-256 digest and local SKILLCARD schema validation. A digest provides integrity, not publisher authentication; OpenSSF/OMS public-key verification is not currently implemented.
- The readiness report is not a compliance certification or an assessment against a named framework
- Benchmark results are hardware and workload specific — not directly comparable across systems
- This tool does not replace NVIDIA Nsight, dedicated security scanners, or official NVIDIA monitoring tools

For evidence-based validation on an authorized GPU machine, follow the
[hardware validation runbook](docs/hardware-validation.md). Hardware checks are
blocked/skipped when `nvidia-smi` is unavailable; they are never simulated as a pass.

---

## Roadmap

| Version | Focus |
|---------|-------|
| v0.1 | CLI, GPU/CUDA/PyTorch/Docker/Security/JSON |
| v0.2 | OpenShell, MCP scanner, Skills scanner |
| v0.3 | Nemotron diagnostics, benchmark engine |
| v0.4 | GitHub Action, HTML reports, plugin system |
| v0.5 | Local dashboard, historical benchmarks |
| v1.0 | Stable APIs, production quality, plugin ecosystem |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

We welcome:
- Bug reports and fixes
- New component integrations
- Compatibility rules (with authoritative sources)
- Documentation improvements
- Test coverage improvements

---

## License

Apache 2.0 — see [LICENSE](LICENSE)

---

## Disclaimer

**NVIDIA Agent Doctor is an independent open-source project and is not affiliated with, endorsed by, or an official product of NVIDIA Corporation.**

NVIDIA, CUDA, TensorRT, Triton, NeMo, Nemotron, and other NVIDIA product names are trademarks of NVIDIA Corporation. Use of these names in this project is for identification purposes only.
