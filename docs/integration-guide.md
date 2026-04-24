# Integration Guide

## Goal

Use `codex-mem` as a repeatable memory layer in Codex workflows.

## Installation Options

### npm package wrapper

```bash
npm install -g github:gluckyjim/CODEX-MEM
codex-mem doctor
```

The npm wrapper runs the bundled Python module and defaults to a user-local store:

- Windows: `%USERPROFILE%\\Documents\\codex-mem\\state`
- POSIX: `~/.codex-mem/state`

On Windows PowerShell, npm may generate a `codex-mem.ps1` shim that is blocked by local execution policy. If that happens, use `codex-mem.cmd ...` or the repo wrapper in `scripts/`.

### Python package

```bash
python -m pip install -e .
codex-mem doctor
```

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
