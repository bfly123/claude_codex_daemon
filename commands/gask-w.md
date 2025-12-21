Forward commands to Gemini session and wait for reply via `gask-w` command (supports tmux / WezTerm).

Execution:
1. Run `Bash(gask-w "<content>", run_in_background=true)` to start background task
2. Tell user the task_id and that Gemini is processing
3. Wait for bash-notification (task completed)
4. When notification arrives, immediately `cat` the output file to show result

Parameters:
- `<content>` required, will be forwarded to Gemini session

Workflow:
1. Start gask-w in background -> get task_id
2. Inform user: "Gemini processing (task: xxx)"
3. When bash-notification arrives -> `cat <output-file>` to show result

Examples:
- `Bash(gask-w "explain this", run_in_background=true)`
- bash-notification arrives -> `cat /tmp/.../tasks/xxx.output`

Hints:
- Use `gask` for fire-and-forget (no wait)
- Use `/gpend` to view latest reply anytime
