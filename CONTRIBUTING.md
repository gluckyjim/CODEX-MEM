# Contributing

Thanks for contributing to `codex-mem`.

## Principles

- keep the tool local-first
- prefer simple workflows over clever abstractions
- optimize for Codex continuity, not generic note-taking
- preserve backward compatibility where practical

## Development Setup

```bash
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

## Pull Request Guidelines

- keep changes scoped
- add or update tests when behavior changes
- update docs when commands or workflows change
- avoid committing local runtime state from `state/`
