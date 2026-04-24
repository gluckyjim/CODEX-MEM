# Changelog

## 0.1.1

- fixed the Windows PowerShell wrapper so `--home` is inserted after the selected subcommand
- fixed the POSIX wrapper to follow the same command ordering contract
- added an npm package wrapper with a Node-based `codex-mem` launcher
- switched plugin and AGENTS examples away from author-machine-specific absolute paths
- documented npm-based installation and user-local default store behavior

## 0.1.0

- initial `codex-mem` MVP
- added CLI commands for `init`, `remember`, `search`, `preflight`, `capture`, `project-state`, `import-legacy`, and `refresh`
- added SQLite-backed memory, capture, and project-state storage
- added Markdown profile and context views
- added Windows and POSIX wrapper scripts
- added Codex plugin scaffold and skill description
- added tests for core flows
- added GitHub publishing assets and community files
