Forward commands to Gemini session and wait for reply via `gask-w` command (supports tmux / WezTerm).

Execution:
1. Run `Bash(gask-w "<content>", run_in_background=true)` to start background task
2. Tell user the task_id and that Gemini is processing
3. STOP immediately and wait for user input (do NOT call TaskOutput)

Parameters:
- `<content>` required, will be forwarded to Gemini session

Workflow:
1. Start gask-w in background -> get task_id
2. Inform user: "Gemini processing in background (task: xxx), use /gpend to check reply"
3. STOP and continue conversation - do NOT block waiting

When user wants result:
- User can say "check gemini" or use `/gpend` to view reply
- Or use `TaskOutput(task_id, block=false)` to check status

Examples:
- `Bash(gask-w "explain this", run_in_background=true)` -> inform user, STOP
- User: "check gemini" -> `gpend` or `TaskOutput(task_id)`

Hints:
- Do NOT use `TaskOutput(block=true)` - it blocks conversation
- Use `/gpend` to view latest reply anytime
- Use `gask` for fire-and-forget (no wait)
