# Repository Guidelines

## Project Structure & Module Organization
- `claude_codex_manager.py` contains the supervisor that spawns Codex child processes, enforces socket hygiene, and restores state between restarts.
- `codex_process.py` runs the assistant loop, validating requests, persisting conversation history, and handling profile configuration.
- `.claude/commands/` holds operator-facing markdown snippets; update them alongside workflow changes.
- `todo.md` and `方案.md` track operational plans—keep entries brief and actionable.

## Build, Test, and Development Commands
- `python3 claude_codex_manager.py`: start the supervisor locally; it will fork the worker on first request.
- `PYTHONPATH=. python3 -m codex_process`: run the worker directly when debugging socket handling.
- `python3 -m black . && python3 -m ruff check .`: format and lint before pushing; install tools via `pip install black ruff`.
- `pytest -q`: execute unit tests once they live under `tests/`; combine with `pytest -k manager` when isolating scenarios.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, 88-character soft limits, and descriptive snake_case names for functions, modules, and sockets.
- Prefer explicit helper methods (see `_handle_config_request`) over inline branching; add short docstrings for public entry points.
- Use f-strings for interpolation and guard Unix-path literals with `os.path` helpers for portability.
- Keep logs and user-facing strings in Simplified Chinese to match existing output unless there is a clear English requirement.

## Testing Guidelines
- Place new tests in `tests/` mirroring the module path, e.g., `tests/test_codex_process.py`.
- Mock filesystem and socket interactions with `pytest` fixtures to avoid touching `/tmp`; verify permission changes and restart flows.
- Add regression tests for error codes (`VALIDATION_ERROR`, `UNKNOWN_CONFIG_ACTION`) whenever logic changes.
- Aim for high-coverage around state restoration and profile switching, since production incidents cluster there.

## Commit & Pull Request Guidelines
- Write commits in imperative mood (`Add socket backoff`), grouping related code, tests, and docs together.
- Reference related tasks from `todo.md` or external trackers in the commit body instead of the subject line.
- PRs should summarize behavior changes, list manual verification (e.g., `python3 claude_codex_manager.py` smoke run), and mention any new dependencies.
- Include before/after logs or screenshots when UI-visible command output changes, especially inside `.claude/commands/`.
