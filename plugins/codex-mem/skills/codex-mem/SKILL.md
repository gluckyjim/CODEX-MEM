---
name: codex-mem
description: Use the local codex-mem CLI before substantial work, when the user says `记住这条`, and after substantial work to preserve project state and stable preferences across Codex sessions.
---

# Codex Mem Skill

## When to use

- Before substantial work when prior context matters.
- When the user says `记住这条`.
- After substantial work to save what changed, key decisions, next steps, and changed files.
- When you need a compact cross-session project snapshot.

## Primary workflow

1. Before substantial work, render a preflight brief:

```bash
codex-mem preflight --query "<topic>"
```

If the task clearly belongs to one project, include:

```bash
--project "<project>"
```

2. When the user says `记住这条`, save the stable rule:

```bash
codex-mem remember --text "<stable rule>"
```

3. After substantial work, capture the session:

```bash
codex-mem capture \
  --project "<project>" \
  --summary "<what changed>" \
  --decision "<key decision>" \
  --next-step "<next step>" \
  --changed-file "/abs/path/to/file.py"
```

## Notes

- Prefer concise, durable statements over raw transcript dumps.
- Use `--rule` for facts that should become stable memory immediately.
- Use `project-state show` when you need the latest project snapshot without a broader search.
- If `codex-mem` is not on PATH, fall back to `python -m codex_mem ...` from the repo or the platform wrapper in `scripts/`.
- On Windows PowerShell, if npm's `codex-mem.ps1` shim is blocked by execution policy, use `codex-mem.cmd ...`.
- npm installs default to a user-local home (`%USERPROFILE%\\Documents\\codex-mem\\state` on Windows, `~/.codex-mem/state` on POSIX).
