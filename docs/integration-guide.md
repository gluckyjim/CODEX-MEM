# Integration Guide

## Goal

Use `codex-mem` as a repeatable memory layer in Codex workflows.

## Minimal Pattern

1. Before substantial work:

```bash
codex-mem preflight --project "<project>" --query "<topic>"
```

2. When a stable rule appears:

```bash
codex-mem remember --project "<project>" --text "<rule>"
```

3. After substantial work:

```bash
codex-mem capture --project "<project>" --summary "<summary>"
```

## AGENTS.md Pattern

Add a memory section that explicitly tells Codex to:

- run `preflight` before substantial work
- use `search` when prior context may matter
- store stable rules with `remember`
- save major work with `capture`

The repo includes a ready-to-copy snippet in [AGENTS-snippet.md](AGENTS-snippet.md).
