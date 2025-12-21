Forward commands to Codex session and wait for reply via `cask-w` command (supports tmux / WezTerm).

Execution:
1. Run `Bash(cask-w "<content>", run_in_background=true)` to start background task
2. Tell user the task_id and that Codex is processing
3. Wait for bash-notification (task completed)
4. When notification arrives, immediately `cat` the output file to show result

Parameters:
- `<content>` required, will be forwarded to Codex session

Workflow:
1. Start cask-w in background -> get task_id
2. Inform user: "Codex processing (task: xxx)"
3. When bash-notification arrives -> `cat <output-file>` to show result

Examples:
- `Bash(cask-w "analyze code", run_in_background=true)`
- bash-notification arrives -> `cat /tmp/.../tasks/xxx.output`

Hints:
- Use `cask` for fire-and-forget (no wait)
- Use `/cpend` to view latest reply anytime
