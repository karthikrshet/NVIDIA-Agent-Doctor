---
name: web-fetch
description: A skill that fetches public documentation URLs
version: "1.0"
author: Example Author
---

# Web Fetch Skill

This skill fetches public documentation from known trusted URLs.

## Behavior

```python
import urllib.request

def fetch_docs(url: str) -> str:
    """Fetch content from a trusted URL."""
    allowed_domains = ["docs.nvidia.com", "pytorch.org", "huggingface.co"]
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.netloc not in allowed_domains:
        raise ValueError(f"Domain not in allowlist: {parsed.netloc}")
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")
```

## Network Scope

Only fetches from:
- docs.nvidia.com
- pytorch.org
- huggingface.co

No authentication required. No credentials used.
