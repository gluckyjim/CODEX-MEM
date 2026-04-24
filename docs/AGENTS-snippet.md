# AGENTS.md Snippet For codex-mem

```md
# Codex-Mem Instructions

- Before substantial work, run `codex-mem preflight --query "<topic>"`.
- If the task is clearly tied to one project, include `--project "<project>"`.
- When the user says `记住这条`, run `codex-mem remember --text "<stable rule>"`.
- After substantial work, save a summary with `capture`, including `--summary`, `--decision`, `--next-step`, and `--changed-file` when possible.
- If `codex-mem` is unavailable on PATH, fall back to `python -m codex_mem ...` or the wrapper in `scripts/`.
- On Windows PowerShell, if npm’s `codex-mem.ps1` shim is blocked by execution policy, use `codex-mem.cmd ...` instead.
- Use `codex-mem doctor` to inspect the active store location before wiring absolute file paths into AGENTS.
```
