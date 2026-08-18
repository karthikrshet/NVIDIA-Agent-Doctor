---
name: file-reader
description: A skill that reads local documentation files
version: "1.0"
author: Example Author
---

# File Reader Skill

This skill reads markdown documentation files from the project directory.

## Behavior

When invoked, this skill will:
1. Look for `README.md` in the current directory
2. Read the contents
3. Return a summary

## Usage

```bash
cat README.md
```

## Scope

- Reads files in the current working directory only
- Does not write or delete files
- Does not make network requests
