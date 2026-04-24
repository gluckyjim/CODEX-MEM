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

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Ling\Documents\codex-mem\scripts\codex-mem.ps1 preflight --query "<topic>"
```

If the task clearly belongs to one project, include:

```powershell
--project "<project>"
```

2. When the user says `记住这条`, save the stable rule:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Ling\Documents\codex-mem\scripts\codex-mem.ps1 remember --text "<stable rule>"
```

3. After substantial work, capture the session:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Ling\Documents\codex-mem\scripts\codex-mem.ps1 capture `
  --project "<project>" `
  --summary "<what changed>" `
  --decision "<key decision>" `
  --next-step "<next step>" `
  --changed-file "C:\path\to\file.py"
```

## Notes

- Prefer concise, durable statements over raw transcript dumps.
- Use `--rule` for facts that should become stable memory immediately.
- Use `project-state show` when you need the latest project snapshot without a broader search.
- The durable store lives under `C:\Users\Ling\Documents\codex-mem\state\`.
