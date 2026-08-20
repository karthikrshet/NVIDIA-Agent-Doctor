# NVIDIA Hardware Validation

Run these tests only on a machine where inspecting the GPU is authorized:

```bash
pytest tests/hardware -m gpu -v --tb=short
nad doctor --json --profile --deep-pytorch
nad gpu info
nad gpu health
nad gpu topology
nad cuda check
nad compatibility check
nad docker gpu-check --allow-container-run --json
nad benchmark run --yes --max-memory-mb 128 --timeout-seconds 15
```

The hardware test module uses real local `nvidia-smi`, CUDA, and (when present)
PyTorch data. It skips with `GPU VALIDATION BLOCKED` when `nvidia-smi` is not
available; a skip is not a passing GPU validation result. TensorRT and Triton
are recorded as optional runtime evidence and are never simulated. The
sanitized RTX 3050 fixtures record a successful local PyTorch CUDA basic
compute check and a bounded Linux-container GPU visibility probe; they do not
assert TensorRT, Triton, NIM, or multi-GPU support.

`nad docker gpu-check` never pulls an image. It requires an already-local CUDA
image plus `--allow-container-run`, then starts one automatically removed,
network-isolated, read-only container with dropped Linux capabilities and CPU,
memory, PID, and timeout limits. It runs one `nvidia-smi` inventory query only.

The default `nad doctor` reads PyTorch package metadata only, so it remains
fast and does not initialize CUDA. The `--deep-pytorch` flag in this runbook is
intentional: it opts into the real device enumeration and bounded basic compute
check needed for hardware validation.

## Optional deployed-runtime gates

Use these only on an authorized machine that already has the service or
runtime installed. The test suite never installs TensorRT, starts a server,
loads a model, or makes a remote request. Endpoints must pass the CLI's
loopback-only validation before a single readiness `GET` is made.

```bash
# Require a real local TensorRT Python runtime and safe builder/runtime probes.
NAD_REQUIRE_TENSORRT=true pytest tests/hardware -m gpu -v --tb=short

# Require a ready local Triton server (no model inference is sent).
NAD_TRITON_ENDPOINT=http://127.0.0.1:8000 pytest tests/hardware -m gpu -v --tb=short

# Require a ready local NIM service (no inference is sent).
NAD_NIM_ENDPOINT=http://127.0.0.1:8000 pytest tests/hardware -m gpu -v --tb=short
```

For a supported `nvidia-smi`, `nad gpu topology` reports only GPU labels and
GPU-to-GPU link classes. It excludes raw topology output, CPU affinity, NUMA,
and PCI identifiers. An unavailable topology query is expected on some older
drivers and does not represent a failed GPU-health check.

The availability probe uses NVIDIA's documented `nvidia-smi -L` GPU-listing
operation. This avoids treating older drivers that reject `nvidia-smi --version`
as unavailable.

## Compatibility evidence

The driver lower-bound check is limited to CUDA major-family minor-version
compatibility and links to NVIDIA's [CUDA Compatibility Guide](https://docs.nvidia.com/deploy/cuda-compatibility/).
Exact TensorRT combinations must be verified against NVIDIA's current
[TensorRT Support Matrix](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html),
because supported package, operating system, CUDA, and driver combinations vary
by TensorRT release.

`nvidia-smi`'s `CUDA Version` is shown as a **driver-reported CUDA maximum**.
It establishes the maximum CUDA version the installed driver advertises, not
that a local CUDA runtime is installed. Agent Doctor reports it separately from
toolkit and runtime evidence and does not use it to claim runtime validation.

Save the command output and attach it to an issue or release validation record
after removing any locally sensitive paths or metadata.

Record only sanitized, evidence-backed fixtures. The current fixture inventory
and capture rules are in [`tests/fixtures/recorded_hardware`](../tests/fixtures/recorded_hardware/README.md).

## Manual GitHub Actions validation

The repository includes a manually dispatched **NVIDIA Hardware Validation**
workflow at [`.github/workflows/gpu-validation.yml`](../.github/workflows/gpu-validation.yml).
It only targets a trusted self-hosted runner labelled `gpu`; GitHub-hosted
runners do not provide NVIDIA hardware. It runs the real hardware tests, core
GPU/CUDA commands, a bounded measured GPU benchmark, and validates the JSON
doctor report. Dispatchers can optionally require TensorRT and provide local
Triton/NIM loopback endpoints; an explicitly requested runtime that is absent
or not ready fails the workflow.

The workflow has read-only repository permissions, runs only through
`workflow_dispatch`, does not retain checkout credentials, and deliberately
does not upload reports or artifacts. A missing GPU, missing PyTorch CUDA
runtime, absent measured benchmark result, or an unexpected diagnostic failure
fails the workflow rather than being reported as a successful validation.

Before enabling it, configure a dedicated, patched Linux GPU runner with only
trusted maintainers able to dispatch workflows. Review any local reports and
commit only sanitized fixtures; do not upload host-specific diagnostic output.
