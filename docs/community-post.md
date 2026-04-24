# Community Post Template

`codex-mem` is now public: https://github.com/gluckyjim/CODEX-MEM

It is a local-first persistent memory workflow for Codex. The goal is simple: keep stable rules, project state, and session summaries outside the default context window so long-running work stays coherent.

Current MVP highlights:

- `remember` for durable rules and preferences
- `preflight` for compact context before work
- `capture` for session summaries, decisions, and next steps
- `project-state` for rolling project snapshots
- SQLite-backed local storage
- legacy memory import support
- plugin scaffold and AGENTS integration examples

It is intentionally explicit rather than magical. If you want a practical memory layer for Codex workflows, feedback and contributions are welcome.
