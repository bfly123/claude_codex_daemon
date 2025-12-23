Send message to Codex and wait for reply via `cask` (sync mode).

Designed for Claude Code: run with `run_in_background=true` so Claude can continue working while Codex processes.

Workflow:
1. Run `Bash(cask "<content>", run_in_background=true)` to start background task
2. Tell user the task_id and that Codex is processing, then END your turn
3. When bash-notification arrives, show the task output

Parameters:
- `<content>` required
- `--timeout SECONDS` optional (default from `CCB_SYNC_TIMEOUT`, fallback 3600)
- `--output FILE` optional: write reply atomically to FILE (stdout stays empty)

Output contract:
- stdout: reply text only (or empty when `--output` is used)
- stderr: progress/errors
- exit code: 0 = got reply, 2 = timeout/no reply, 1 = error
