# Getting Started with NVIDIA Agent Doctor

## Installation

```bash
git clone https://github.com/karthikrshet/NVIDIA-Agent-Doctor.git
cd NVIDIA-Agent-Doctor
python -m pip install -e ".[dev]"
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

## Limitations

OpenShell, NemoClaw, Nemotron, NIM, TensorRT, and Triton checks are optional
detection or heuristic checks unless a command explicitly reports completed local
validation. They do not establish workload correctness or vendor support.

The skills and MCP scanners are static, heuristic reviews—not malware detection.
Use them as one input to human security review.
