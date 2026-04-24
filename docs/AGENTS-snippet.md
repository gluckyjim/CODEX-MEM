# AGENTS.md Snippet For codex-mem

```md
# Codex-Mem Instructions

- Before substantial work, run `powershell -ExecutionPolicy Bypass -File C:\Users\Ling\Documents\codex-mem\scripts\codex-mem.ps1 preflight --query "<topic>"`.
- If the task is clearly tied to one project, include `--project "<project>"`.
- When the user says `记住这条`, run `powershell -ExecutionPolicy Bypass -File C:\Users\Ling\Documents\codex-mem\scripts\codex-mem.ps1 remember --text "<stable rule>"`.
- After substantial work, save a summary with `capture`, including `--summary`, `--decision`, `--next-step`, and `--changed-file` when possible.
- Use `C:\Users\Ling\Documents\codex-mem\state\profile.md` as the fast stable brief and `memory.db` as the durable source of truth.
```
