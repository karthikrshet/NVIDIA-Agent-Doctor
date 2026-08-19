<p align="center">
  <img src="https://raw.githubusercontent.com/karthikrshet/NVIDIA-Agent-Doctor/main/docs/assets/nvidia-agent-doctor-banner.png" alt="NVIDIA Agent Doctor" width="100%">
</p>

<p align="center">
  <strong>Diagnose. Secure. Validate. Benchmark. NVIDIA AI Environments.</strong>
</p>

<p align="center">
  <sub>Independent open-source project — not affiliated with, endorsed by, or an official product of NVIDIA Corporation.</sub>
</p>

# NVIDIA Agent Doctor

> An independent, local-first CLI for diagnosing NVIDIA AI environments and reviewing agent, MCP, and skill configuration risk.

[![CI](https://github.com/karthikrshet/nvidia-agent-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/karthikrshet/nvidia-agent-doctor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Independent project:** NVIDIA Agent Doctor is not affiliated with, endorsed by, or an official product of NVIDIA Corporation. It does not claim NVIDIA certification or vendor support.

`nad` answers a practical question: **what can this machine actually run, what is misconfigured, and what configuration needs human security review?** It combines read-only hardware and software checks with static inspection of MCP and agent-skill files. It does not change drivers, install packages, start servers, upload data, or run a benchmark unless you explicitly request the relevant action.

## Contents

- [What it checks](#what-it-checks)
- [Install and first run](#install-and-first-run)
- [Common workflows](#common-workflows)
- [Command reference](#command-reference)
- [Configuration](#configuration)
- [Results, scores, and exit codes](#results-scores-and-exit-codes)
- [Security and privacy model](#security-and-privacy-model)
- [Real hardware validation](#real-hardware-validation)
- [Scope and limitations](#scope-and-limitations)
- [Development](#development)

## What it checks

The default `nad doctor` command is read-only. It checks the local operating system, NVIDIA GPU state, CUDA evidence, optional Python integrations, Docker, baseline security posture, and cross-component compatibility. Optional components are reported as `NOT_INSTALLED`, rather than treated as failures.

| Area | What the tool does today | Classification |
|---|---|---|
| NVIDIA GPU | Uses `nvidia-smi` XML with a query fallback to read inventory, driver, VRAM, utilization, temperature, power when available, and compute capability when supported. | Real local integration |
| CUDA | Reads `nvcc`, CUDA environment variables, driver evidence, and an installed PyTorch CUDA build when present. Driver compatibility is limited to documented CUDA major-family minimums. | Real local integration; not a full support matrix |
| PyTorch | Imports the package when installed, checks CUDA availability/devices, and performs one tiny GPU dot product. | Real local integration |
| Docker | Detects Docker and NVIDIA container-runtime indicators. | Local detection |
| TensorRT | Checks whether the local Python package imports and whether basic builder/runtime indicators are present. | Partial local detection |
| Triton Inference Server | Checks binary, process, and container indicators; optionally calls the documented loopback readiness endpoint after explicit consent. It never sends inference. | Heuristic detection plus limited local integration |
| NeMo, Nemotron, NemoClaw | Checks package, CLI, and configured local indicators. | Heuristic detection |
| NVIDIA NIM | Optionally sends a read-only request to a validated loopback readiness endpoint; model-list discovery is also local and opt-in. | Limited local integration |
| OpenShell | Checks documented local CLI/config/process indicators and reports isolation-policy indicators without changing policy. | Heuristic detection |
| MCP | Discovers supported JSON configuration files and statically reviews command, environment, transport, and endpoint risk. | Static configuration analysis |
| Agent skills | Parses `SKILL.md` files, builds a risk graph, and detects suspicious static patterns. | Static heuristic analysis |
| Kubernetes | Runs fixed, read-only `kubectl` queries only after explicit consent. | Opt-in local cluster inspection |
| Benchmark | Measures small PyTorch GPU matrix multiplication, CUDA copy, and optional system-memory copy under explicit memory/time limits. | Opt-in measured benchmark |

`PASS` means the specific local check succeeded. It does **not** certify a workload, a cluster, an image, a vendor support matrix, or the security of an agent.

## Install and first run

### Requirements

- Python 3.11+ (CI validates Python 3.11 and 3.12)
- `nvidia-smi` on `PATH` for NVIDIA GPU inventory and driver checks
- Optional: a CUDA-enabled PyTorch build in the same Python environment for a real PyTorch CUDA compute check
- Optional: Docker, `kubectl`, Ollama, NIM, TensorRT, Triton, OpenShell, and NeMo-related tooling only if you want those checks

The CUDA toolkit (`nvcc`) is not required for a prebuilt CUDA-enabled PyTorch wheel. It is needed when you compile CUDA code locally.

### Install from source

Source installation is the supported distribution path at this stage; do not assume a PyPI package exists.

```bash
git clone https://github.com/karthikrshet/NVIDIA-Agent-Doctor.git
cd NVIDIA-Agent-Doctor
python -m pip install -e .
nad --version
nad doctor
```

For development tools and the test suite:

```bash
python -m pip install -e ".[dev]"
```

On a CPU-only machine, `nad doctor` completes normally and reports GPU-specific components as unavailable or optional. It never fabricates a GPU result.

### First commands to run

```bash
# Human-readable environment summary
nad doctor

# Machine-readable diagnostic report; validate it in another tool if needed
nad doctor --json

# Targeted GPU and CUDA evidence
nad gpu info --json
nad gpu health --json
nad cuda check --json
nad compatibility check --json

# Optional local runtime probes; absence is reported as optional
nad tensorrt check --json
nad triton check --json
```

To inspect where time is spent on your machine, use `nad doctor --json --profile`. PyTorch import and CUDA initialization can dominate a first run when CUDA-enabled PyTorch is installed.

## Common workflows

### Diagnose a local GPU environment

```bash
nad doctor --json
nad gpu health
nad cuda check
nad compatibility check
```

The compatibility report only makes claims supported by the discovered environment. For example, a successful PyTorch GPU operation verifies that installed PyTorch can initialize and execute on the detected GPU; it does not establish TensorRT compatibility.

### Review MCP configuration without exposing secrets

```bash
# Built-in discovery locations plus an explicit file
nad mcp scan --config examples/mcp/example-mcp-config.json --json

# Security baseline and deterministic redaction regression probes
nad security scan --json
nad security leak-check
```

MCP inspection reads configuration. It does not start MCP servers, execute configured commands, or test live tool permissions.

### Review agent skills before use

```bash
nad skills scan examples/skills --risk-graph --json
nad skills verify path/to/SKILL.md --signature path/to/skill.sig --json
nad test-agent examples/skills --mcp-config examples/mcp/example-mcp-config.json --json
```

`nad skills scan` and `nad test-agent` are static preflight checks. They do not run a skill, invoke an MCP server, call a model, or make a network request. `skills verify` currently validates a detached SHA-256 digest and a local `SKILLCARD.yaml` schema. A digest proves integrity of the supplied file, not publisher identity; public-key/OpenSSF Model Signing verification is not implemented.

### Produce a shareable report

```bash
nad report generate --format json --output nad-report.json
nad report generate --format markdown --output nad-report.md
nad report generate --format html --output nad-report.html
nad report generate --format compliance-audit --output readiness.md
```

JSON, Markdown, HTML, terminal, and compliance-audit renderers apply the project’s credential redaction boundary. Reports still contain environment facts such as operating-system and hardware information. Review reports before sharing them externally.

### Run a safe, bounded benchmark

Benchmarks are never part of `nad doctor`. They require confirmation unless `--yes` is supplied and enforce a memory range of 16–1024 MB and a timeout range of 1–300 seconds.

```bash
# Conservative explicit GPU-only measurement
nad benchmark run --gpu-only --yes --max-memory-mb 16 --timeout-seconds 15 --json

# Include the optional system-memory and CUDA-copy measurements
nad benchmark run --yes --max-memory-mb 128 --timeout-seconds 15
```

Results are measured on the current machine and workload only. They are not fabricated, are not hardware specifications, and should not be compared across unrelated configurations. A timeout produces exit code `2`; GPU memory references are cleaned up on success and failure.

### Query a local NIM service safely

```bash
# No request is made without --allow-local-request
nad nemotron nim --allow-local-request --json

# Optional local model-list query; no inference request is sent
nad nemotron nim --allow-local-request --models --json
```

Only loopback readiness and model-list endpoints are accepted. Remote URLs, credential-bearing URLs, query strings, and fragments are rejected.

### Verify a local Triton server is ready

```bash
# Default: inspect local indicators only; no HTTP request
nad triton check --json

# One GET request to the validated loopback /v2/health/ready endpoint
nad triton check --allow-local-request --endpoint http://127.0.0.1:8000 --json
```

The readiness probe uses Triton's documented [`/v2/health/ready` endpoint](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/getting_started/quick_deployment_by_backend.html). It accepts only an `http(s)` loopback base URL, has a 30-second maximum timeout, does not fetch model metadata, and never sends inference input. A requested but unavailable or non-ready local server returns exit code `1`.

### Review a Kubernetes context deliberately

```bash
# Detect whether kubectl is available; does not contact a cluster
nad cluster scan --json

# Fixed, read-only queries against the current kubectl context
nad cluster scan --allow-cluster-access --json
```

The cluster command does not edit workloads, policies, or contexts. Confirm that the current `kubectl` context is appropriate before granting access.

## Command reference

| Command | Purpose | Default safety behavior |
|---|---|---|
| `nad doctor [--json] [--profile]` | Full local diagnostic | Read-only; no benchmark or network request |
| `nad doctor --auto-resolve` | Produces a review-only remediation plan | Does not install, modify, or execute fixes |
| `nad doctor --ai-explain --allow-model-request --model NAME` | Requests a local Ollama explanation | Only a validated loopback endpoint is allowed |
| `nad gpu info` / `nad gpu health` | NVIDIA GPU inventory and health | Read-only `nvidia-smi` calls |
| `nad cuda check` | CUDA toolkit/runtime/environment evidence | Read-only |
| `nad compatibility check` | GPU, driver, CUDA, PyTorch, TensorRT evidence | Read-only; does not invent a support matrix |
| `nad tensorrt check` | TensorRT Python binding, runtime, and builder-object probe | Does not build an engine or claim CUDA support-matrix compatibility |
| `nad triton check` | Local Triton binary/client/process indicators and optional readiness | One local GET only with `--allow-local-request`; never loads a model or runs inference |
| `nad security scan` | Environment and local permission baseline | Does not print detected secret values |
| `nad security leak-check` | Redaction regression probes | Uses deterministic test values, not your credentials |
| `nad mcp scan` | MCP configuration discovery and static review | Does not execute MCP server commands |
| `nad skills scan` | Static `SKILL.md` risk review | Does not execute skills |
| `nad skills verify` | SHA-256 digest and `SKILLCARD.yaml` validation | Local file read only |
| `nad test-agent` | Static skill/MCP wiring preflight | No tools, models, or network calls |
| `nad openshell diagnose` / `audit` | Local OpenShell indicators and heuristic audit | Does not modify OpenShell policy |
| `nad nemotron check` / `nad nemoclaw check` | Local package/CLI detection | Heuristic, read-only |
| `nad nemotron nim` | Optional local NIM readiness check | No request without explicit consent |
| `nad cluster scan` | Optional Kubernetes health inventory | No cluster request without explicit consent |
| `nad benchmark run` | Bounded performance measurement | Never automatic; confirmation required |
| `nad report generate` | Terminal, JSON, Markdown, HTML, or readiness report | Writes a file only when requested or for default HTML output |
| `nad interactive` | Guided Rich terminal console | Not a live dashboard; no benchmark |

For all options, use `nad <command> --help`. Global options must appear before the subcommand, for example:

```bash
nad --config ./nad.toml doctor --json
nad --no-color doctor
nad --version
```

## Configuration

Configuration files are TOML and are validated strictly: malformed TOML, unknown keys, invalid values, or a missing explicit `--config` file return exit code `4`. NVIDIA Agent Doctor does not silently fall back to defaults after an invalid user configuration.

Search order when `--config` is not provided:

1. `./.nvidia-agent-doctor.toml`
2. `~/.nvidia-agent-doctor.toml`
3. Safe built-in defaults

The checked-in [example configuration](.nvidia-agent-doctor.toml) is a starting point. The command settings currently read by the CLI are:

```toml
[benchmark]
# Used by `nad benchmark run` when the equivalent CLI option is omitted.
max_memory_mb = 128     # 16–1024
timeout_seconds = 15    # 1–300

[mcp]
# Included by `nad mcp scan` and `nad test-agent`.
config_paths = ["./mcp.json"]

[skills]
# Used when `nad skills scan` is called without --depth.
scan_depth = 3
```

Unsupported settings are rejected rather than retained as no-ops. Explicit CLI consent flags remain required for operations that could contact local services or a Kubernetes cluster.

## Results, scores, and exit codes

| Status | Meaning |
|---|---|
| `PASS` | The local check completed successfully. |
| `WARNING` | A potential problem or review item was found. |
| `ERROR` | A local check failed and needs action. |
| `NOT_INSTALLED` | Optional software is absent; this is not automatically a failure. |
| `NOT_APPLICABLE` | The check does not apply to this environment. |
| `UNKNOWN` | The tool lacks sufficient evidence to determine a result. |

The health score is deterministic and excludes `NOT_INSTALLED`, `NOT_APPLICABLE`, and `UNKNOWN` checks. It is a diagnostic summary, not a compliance, security, or performance certification.

| Exit code | Meaning |
|---|---|
| `0` | No warnings or errors in the command’s report. |
| `1` | One or more warnings. |
| `2` | One or more diagnostic errors, including a failed benchmark measurement. |
| `3` | A `HIGH` or `CRITICAL` security finding. |
| `4` | Invalid or missing explicitly requested configuration. |

## Security and privacy model

- **Local-first:** normal diagnostics make no network request and send no telemetry.
- **Redaction:** known API-key, token, password, private-key, credential URL, MCP argument, metadata, and handled-exception patterns are redacted before supported report rendering.
- **Human review:** static skill and MCP findings describe potential risk requiring review. They do not label content as malicious and can produce false positives or false negatives.
- **Explicit network consent:** NIM, Triton readiness, Ollama explanation, and Kubernetes queries require dedicated consent flags and have restricted targets or fixed read-only commands.
- **No automatic remediation:** `--fix` and `--auto-resolve` show suggestions only; they never install packages, alter drivers, change firewall rules, edit policies, or execute shell commands.

Redaction is defense in depth, not a guarantee that every proprietary string is classified as a secret. Use `nad security leak-check` after upgrading and inspect generated reports before uploading or sharing them.

## Real hardware validation

The repository includes a sanitized record from an authorized Windows test machine:

| Evidence | Verified result |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| Driver | 511.65 |
| Driver-reported CUDA maximum | 11.6 |
| PyTorch | 2.7.1+cu118 |
| PyTorch CUDA | One device; compute capability 8.6; tiny CUDA compute passed |
| Bounded benchmark | 16 MB GPU-only matrix multiplication measured successfully with a 15-second timeout |

This validates the listed machine only. It is not evidence for every driver, GPU generation, operating system, CUDA version, or optional NVIDIA runtime. TensorRT, Triton, NIM, multi-GPU, OpenShell, and Kubernetes require their own authorized environments before they can be described as hardware-validated.

Run the same evidence-based checks on an authorized GPU host:

```bash
pytest tests/hardware -m gpu -v --tb=short
nad doctor --json --profile
nad gpu info --json
nad gpu health --json
nad cuda check --json
nad compatibility check --json
nad benchmark run --gpu-only --yes --max-memory-mb 16 --timeout-seconds 15 --json
```

See the [hardware validation runbook](docs/hardware-validation.md) and [sanitized fixture rules](tests/fixtures/recorded_hardware/README.md) before adding a fixture. Never commit hostnames, UUIDs, PCI identifiers, timestamps, credentials, model data, or dynamic workload output.

## Scope and limitations

- This is an **alpha** project (`0.1.0`), not a production certification.
- GPU checks require a functional `nvidia-smi`; absence is reported rather than simulated.
- CUDA compatibility checks use limited documented driver-major lower bounds. Use official NVIDIA release notes and support matrices for exact deployment compatibility.
- TensorRT, Triton, NeMo/Nemotron/NemoClaw, OpenShell, NIM, and Kubernetes coverage has the classification stated above; absence of a detection result is not proof of absence or incompatibility.
- MCP analysis reads configuration; it does not observe live server behavior or establish effective OS/container capabilities.
- Skill scanning is static heuristic analysis, not malware detection or sandboxing.
- The HTML report is escaped and self-contained, but reports may still contain non-secret local environment details.
- Benchmarks are minimal diagnostic measurements. Use NVIDIA Nsight, application profiling, and vendor tools for detailed performance work.

## Development

```bash
python -m pip install -e ".[dev]"
pytest tests/ -v --tb=short -m "not gpu and not slow" --no-cov
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/nvidia_agent_doctor/
```

GPU tests are deliberately marked and run only on an authorized NVIDIA host:

```bash
pytest tests/hardware -m gpu -v --tb=short
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md) for project process and disclosure guidance.

## License

Apache-2.0. See [LICENSE](LICENSE).

NVIDIA, CUDA, TensorRT, Triton, NeMo, Nemotron, and related product names are trademarks of NVIDIA Corporation. Their use here is solely for identification.
