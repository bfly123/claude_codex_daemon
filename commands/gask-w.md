Send message to Gemini and wait for reply via `gask-w` (foreground sync).

Execution:
- Run `Bash(gask-w "<content>")` and wait until it returns

Parameters:
- `<content>` required
- `--timeout SECONDS` optional (default from `CCB_SYNC_TIMEOUT`, fallback 3600)
- `--output FILE` optional: write reply atomically to FILE (stdout still prints the reply)

Output contract:
- stdout: reply text only
- stderr: progress/errors
- exit code: 0 = got reply, 2 = timeout/no reply, 1 = error

Hints:
- Use `gask` with `run_in_background=true` for background waiting
- Use `/gpend` to view the latest reply from Gemini logs
