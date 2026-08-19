# NVIDIA Hardware Validation

Run these tests only on a machine where inspecting the GPU is authorized:

```bash
pytest tests/hardware -m gpu -v --tb=short
nad doctor --json --profile --deep-pytorch
nad gpu info
nad gpu health
nad cuda check
nad compatibility check
nad benchmark run --yes --max-memory-mb 128 --timeout-seconds 15
```

The hardware test module uses real local `nvidia-smi`, CUDA, and (when present)
PyTorch data. It skips with `GPU VALIDATION BLOCKED` when `nvidia-smi` is not
available; a skip is not a passing GPU validation result. TensorRT and Triton
are recorded as optional runtime evidence and are never simulated. The
sanitized RTX 3050 fixture also records a successful local PyTorch CUDA basic
compute check; it does not assert TensorRT, Triton, NIM, or multi-GPU support.

The default `nad doctor` reads PyTorch package metadata only, so it remains
fast and does not initialize CUDA. The `--deep-pytorch` flag in this runbook is
intentional: it opts into the real device enumeration and bounded basic compute
check needed for hardware validation.

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
doctor report.

The workflow has read-only repository permissions, runs only through
`workflow_dispatch`, does not retain checkout credentials, and deliberately
does not upload reports or artifacts. A missing GPU, missing PyTorch CUDA
runtime, absent measured benchmark result, or an unexpected diagnostic failure
fails the workflow rather than being reported as a successful validation.

Before enabling it, configure a dedicated, patched Linux GPU runner with only
trusted maintainers able to dispatch workflows. Review any local reports and
commit only sanitized fixtures; do not upload host-specific diagnostic output.
