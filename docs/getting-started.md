# Getting Started with NVIDIA Agent Doctor

## Installation

```bash
pip install nvidia-agent-doctor
```

## First Run

```bash
nad doctor
```

This performs a safe, read-only diagnostic of your environment.

## What Gets Checked

| Component | What We Check |
|-----------|---------------|
| System | OS, Python version, RAM |
| GPU | nvidia-smi, VRAM, temperature, utilization |
| CUDA | Toolkit, runtime, env vars, compatibility |
| PyTorch | Version, CUDA build, device count, compute test |
| Docker | Docker daemon, NVIDIA container runtime |
| Security | Root check, env secrets, SSH key permissions |
| Compatibility | CUDA/PyTorch/TensorRT version alignment |

## No GPU?

That's fine. NVIDIA Agent Doctor handles missing components gracefully:

```
NVIDIA GPU          –  NOT_INSTALLED
CUDA                –  NOT_INSTALLED
```

These are informational, not failures.

## Machine-Readable Output

```bash
nad doctor --json
```

## Generate Reports

```bash
nad report generate --format html --output health.html
```

## Security Scan

```bash
nad security scan
```

## Scan Agent Skills

```bash
nad skills scan ./skills/
```

## Next Steps

- [Architecture](architecture.md)
- [GPU Diagnostics](gpu.md)
- [CUDA Diagnostics](cuda.md)
- [Security Analysis](security.md)
