Forward commands to Codex session and wait for reply via `cask-w` command (supports tmux / WezTerm, forward only, does not execute in current Claude process).

Execution:
1. Run `Bash(cask-w "<content>", run_in_background=true)` to start background task
2. Tell user the task_id and that Codex is processing
3. STOP immediately and wait for user input (do NOT call TaskOutput)

Parameters:
- `<content>` required, will be forwarded to Codex session

Workflow:
1. Start cask-w in background -> get task_id
2. Inform user: "Codex processing in background (task: xxx), use /cpend to check reply"
3. STOP and continue conversation - do NOT block waiting

When user wants result:
- User can say "check codex" or use `/cpend` to view reply
- Or use `TaskOutput(task_id, block=false)` to check status

Examples:
- `Bash(cask-w "analyze code", run_in_background=true)` -> inform user, STOP
- User: "check codex" -> `cpend` or `TaskOutput(task_id)`

Hints:
- Do NOT use `TaskOutput(block=true)` - it blocks conversation
- Use `/cpend` to view latest reply anytime
- Use `cask` for fire-and-forget (no wait)
