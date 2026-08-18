# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

---

## Responsible Disclosure

If you discover a security vulnerability in NVIDIA Agent Doctor, please do **not** file a public GitHub issue. Instead, report it privately via:

- **GitHub Security Advisories:** Use the repository's **Report a vulnerability** button.

Do not include credentials, private keys, or customer data. Maintainers will establish
a private follow-up channel after acknowledging a report.

We will acknowledge receipt within **48 hours** and provide a fix timeline within **7 days** for critical issues.

---

## Threat Model

NVIDIA Agent Doctor is a **local, read-only diagnostic tool by default**. It does not:

- Run a server or expose network ports
- Transmit data to a remote service during normal diagnostics
- Store credentials or secrets
- Modify system configuration (without explicit user confirmation)

The following network-capable actions require a separate explicit opt-in flag:

- `nad doctor --ai-explain --allow-model-request` contacts a validated loopback Ollama endpoint with redacted diagnostic evidence.
- `nad nemotron nim --allow-local-request` contacts a validated loopback NIM readiness endpoint.
- `nad cluster scan --allow-cluster-access` uses fixed, read-only `kubectl` queries against the user's configured cluster context.

These paths reject remote endpoints where applicable, do not print credentials, and are never run by `nad doctor`.

### What we protect against

1. **Secret leakage in reports** — All API keys, tokens, and passwords are redacted before any output
2. **Credential exposure in logs** — Environment variables containing secrets are never printed in full
3. **Destructive auto-fix** — No fix is applied without explicit user confirmation
4. **Dependency supply chain** — We use minimal dependencies; review `pyproject.toml`

### What we do NOT claim to protect against

1. **Malicious SKILL.md files** — Our scanner is heuristic and will miss sophisticated attacks
2. **Malicious MCP servers** — We analyze configuration, not live behavior
3. **Compromised NVIDIA tools** — We trust nvidia-smi and other NVIDIA tools
4. **Kernel-level threats** — We operate entirely in userspace

---

## Scanner Limitations

### Skills Scanner

The SKILL.md scanner uses **heuristic static analysis**. It:

- **Cannot** detect all malicious patterns
- **Will** produce false positives (flagging safe skills as risky)
- **Will** miss sophisticated obfuscated attacks
- **Should not** be used as the sole security gate for agent skills

Always perform human review of all flagged findings.

### MCP Scanner

The MCP scanner analyzes **configuration files** only. It:

- Cannot detect runtime behavior of MCP servers
- Cannot verify that a server does what its configuration claims
- May miss custom transport implementations

### Credential Scanner

The credential scanner uses pattern matching on:

- Environment variable names
- Known API key formats (OpenAI, NVIDIA, HuggingFace, GitHub)
- Common secret naming patterns

It **does not** perform cryptographic validation of detected secrets.

---

## Safe Usage Guidelines

1. **Run in a trusted environment** — Do not run `nad` in untrusted CI environments with production secrets
2. **Review output before sharing** — Even with redaction, review JSON reports before sharing externally
3. **Don't run as root** — AI workloads and diagnostics should run as a non-root user
4. **Verify `--fix` commands** — Always review suggested commands before applying them
5. **Keep updated** — Update to the latest version for security fixes

---

## False Positives and False Negatives

Our heuristic scanners can produce:

- **False positives**: Legitimate skills or MCP servers flagged as risky
- **False negatives**: Malicious patterns not detected

Do not treat NVIDIA Agent Doctor as a complete security solution. Use it as one layer of a defense-in-depth strategy.

---

## Privacy

- **No telemetry** — Nothing is transmitted automatically
- **No cloud upload by default** — Normal diagnostics are local; the explicit cluster scan queries only the configured Kubernetes API context
- **No secret storage** — Secrets are redacted in memory before any output
- **No source code upload** — The tool never reads or transmits your source code

---

*NVIDIA Agent Doctor is an independent open-source project and is not affiliated with NVIDIA Corporation.*
