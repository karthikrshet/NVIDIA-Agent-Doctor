# NVIDIA Hardware Validation

Run these tests only on a machine where inspecting the GPU is authorized:

```bash
pytest tests/hardware -m gpu -v --tb=short
nad doctor --json --profile
nad gpu info
nad gpu health
nad cuda check
nad compatibility check
nad benchmark run --yes --max-memory-mb 128 --timeout-seconds 15
```

The hardware test module uses real local `nvidia-smi`, CUDA, and (when present)
PyTorch data. It skips with `GPU VALIDATION BLOCKED` when `nvidia-smi` is not
available; a skip is not a passing GPU validation result. TensorRT and Triton
are recorded as optional runtime evidence and are never simulated.

## Compatibility evidence

The driver lower-bound check is limited to CUDA major-family minor-version
compatibility and links to NVIDIA's [CUDA Compatibility Guide](https://docs.nvidia.com/deploy/cuda-compatibility/).
Exact TensorRT combinations must be verified against NVIDIA's current
[TensorRT Support Matrix](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html),
because supported package, operating system, CUDA, and driver combinations vary
by TensorRT release.

Save the command output and attach it to an issue or release validation record
after removing any locally sensitive paths or metadata.
