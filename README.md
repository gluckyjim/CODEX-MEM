# codex-mem

`codex-mem` is a local-first persistent memory workflow for Codex.

It is designed for a practical problem: long-running Codex collaborations accumulate rules, decisions, preferences, and project state that do not fit inside the default active context window. `codex-mem` gives that information a durable home and a repeatable workflow.

## Why It Exists

Many agent memory tools were designed around hook systems that Codex does not currently expose in the same way. `codex-mem` takes a Codex-native approach instead:

- explicit `preflight` before substantial work
- explicit `capture` after substantial work
- explicit `remember` when the user shares a stable rule
- SQLite as the durable source of truth
- compact Markdown summaries for fast human and agent review

The goal is not magical omniscience. The goal is practical continuity.

## Features

- `remember`
  Store a durable rule, preference, or long-lived fact.
- `search`
  Search memories, captures, and project state.
- `preflight`
  Generate a compact context brief before substantial work.
- `capture`
  Save a session summary, decisions, next steps, and changed files.
- `project-state`
  Maintain a rolling project snapshot.
- `import-legacy`
  Import an older memory store into `codex-mem`.
- `refresh`
  Rebuild the human-readable profile and context files.

## Current Status

This repository is a publishable MVP:

- working Python package and CLI
- local runtime store
- legacy import support
- unit tests for core flows
- Codex plugin scaffold
- AGENTS integration pattern
- Windows and POSIX wrapper scripts
- GitHub community files and CI workflow

## Repository Layout

- `codex_mem/`
  Python package for storage, scoring, rendering, and CLI commands.
- `scripts/`
  Convenience wrappers and bootstrap scripts.
- `plugins/codex-mem/`
  Codex plugin scaffold with a skill description.
- `docs/`
  Integration and publishing notes.
- `tests/`
  Unit tests for the core memory workflow.
- `state/`
  Local runtime state. Ignored by git.

## Installation

### Run From The Repo

```bash
python -m codex_mem init
python -m codex_mem preflight --query "memory workflow"
```

### Install Editable

```bash
python -m pip install -e .
codex-mem init
codex-mem preflight --query "memory workflow"
```

### npm Package Wrapper

```bash
npm install -g github:gluckyjim/CODEX-MEM
codex-mem doctor
codex-mem preflight --query "memory workflow"
```

The npm wrapper executes the bundled Python module and defaults to a user-local store:

- Windows: `%USERPROFILE%\\Documents\\codex-mem\\state`
- POSIX: `~/.codex-mem/state`

On Windows PowerShell, npm may generate a `codex-mem.ps1` shim that is blocked by local execution policy. In that case, use `codex-mem.cmd ...` or the repo wrapper in `scripts/`.

### Windows Wrapper

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\codex-mem.ps1 doctor
```

### POSIX Wrapper

```bash
./scripts/codex-mem.sh doctor
```

## Quick Start

Initialize the store:

```bash
python -m codex_mem init
```

Import a legacy memory store:

```bash
python -m codex_mem import-legacy --path "/path/to/legacy/memory.db"
```

Generate a context brief before work:

```bash
python -m codex_mem preflight --project "my-project" --query "pricing rules"
```

Remember a stable rule:

```bash
python -m codex_mem remember --project "my-project" --text "Remember this: always read prior memory before substantial work."
```

Capture the outcome of a work session:

```bash
python -m codex_mem capture \
  --project "my-project" \
  --summary "Implemented project-state rendering and improved preflight search." \
  --decision "Keep storage local-first for the MVP." \
  --next-step "Publish the repo to GitHub." \
  --changed-file "/abs/path/to/file.py"
```

## Recommended Codex Workflow

Before substantial work:

```bash
codex-mem preflight --project "my-project" --query "topic"
```

When a stable rule should be remembered:

```bash
codex-mem remember --project "my-project" --text "Remember this: ..."
```

After substantial work:

```bash
codex-mem capture --project "my-project" --summary "..."
```

## Design Principles

- local-first by default
- useful without network access
- compact context beats dumping raw history
- explicit workflows beat unreliable guesswork
- structured project state matters as much as raw memory entries

## Testing

```bash
python -m unittest discover -s tests -p "test_*.py"
```

For a larger synthetic retrieval benchmark:

```bash
python scripts/run_extreme_self_test.py \
  --sizes 1000 5000 10000 \
  --query-count 120 \
  --output-json docs/benchmarks/extreme-self-test.json \
  --output-md docs/benchmarks/extreme-self-test.md
```

Latest published benchmark:

- [docs/benchmarks/extreme-self-test-2026-04-24.md](docs/benchmarks/extreme-self-test-2026-04-24.md)

## Codex Integration

This repo includes:

- an `AGENTS.md` snippet
- a Codex plugin scaffold
- a Codex skill description

See:

- [docs/AGENTS-snippet.md](docs/AGENTS-snippet.md)
- [docs/integration-guide.md](docs/integration-guide.md)
- [plugins/codex-mem/.codex-plugin/plugin.json](plugins/codex-mem/.codex-plugin/plugin.json)

## Publishing

This repo is structured so it can be published directly to GitHub as the first public `codex-mem` release candidate.

See:

- [docs/publishing.md](docs/publishing.md)
- [CHANGELOG.md](CHANGELOG.md)
- [ROADMAP.md](ROADMAP.md)

## Language Notes

The codebase supports both English and Chinese memory content. Public-facing documentation is English-first so global Codex users can adopt it more easily.

## License

MIT
