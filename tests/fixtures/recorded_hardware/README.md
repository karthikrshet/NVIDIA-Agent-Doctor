# Recorded Hardware Fixtures

This directory contains **sanitized evidence captured from authorized real
hardware**. It must never contain generated, guessed, customer, host, PCI, GPU
UUID, model-weight, credential, or benchmark data.

| Fixture | Evidence | Status |
|---|---|---|
| `rtx3050_windows_driver511_65.json` | Single NVIDIA GPU, driver and CUDA maximum, VRAM, compute capability, and PyTorch CUDA compute | Recorded on authorized hardware |
| `rtx3050_docker_cuda116_linux.json` | Same authorized RTX 3050 visible from the bounded `nvidia/cuda:11.6.2-base-ubuntu20.04` Linux-container probe | Recorded on authorized hardware |
| Multi-GPU | Inventory and per-GPU capability | Pending an authorized multi-GPU host |
| CUDA/driver mismatch | Actual diagnostic result from a supported test environment | Pending an authorized mismatch test host |
| Low-memory condition | Observed workload-independent health evidence | Pending an authorized test host |
| TensorRT/Triton/NIM | Installed and unavailable states from real runtimes | Pending authorized runtime environments |

## Capture procedure

On an authorized machine, run the hardware validation runbook first:

```bash
pytest tests/hardware -m gpu -v --tb=short
nad doctor --json --profile --deep-pytorch
nad gpu info --json
nad gpu health --json
nad cuda check --json
nad compatibility check --json
nad docker gpu-check --allow-container-run --json
```

For an explicitly opted-in, bounded benchmark, record the command and runtime
limits alongside the result; never claim results from another GPU as local
evidence. Before committing a fixture, remove GPU UUIDs, PCI identifiers,
timestamps, hostnames, file paths, process names, credentials, and dynamic
workload measurements. Add a test that identifies the source command and
asserts the stable values that the fixture is intended to preserve.
