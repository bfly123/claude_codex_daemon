Use `cpend` to fetch latest reply from Codex official logs (`~/.codex/sessions/`).

Trigger conditions (any match):
- User mentions cpend/Cpend
- User wants to view/fetch/get Codex reply/response
- User asks for recent N Codex conversations/replies (e.g. "调取最近5条codex回复", "show last 3 codex messages")

Execution:
- `cpend` - fetch latest single reply: `Bash(cpend)`
- `cpend N` - fetch last N conversations (Q&A pairs): `Bash(cpend N)` (e.g. `cpend 5`)
- Keep command execution silent, no additional analysis after execution

Output format (when N > 1):
```
Q: user question 1
A: codex reply 1
---
Q: user question 2
A: codex reply 2
```

Features:
1. Reads Codex official session JSONL logs from `~/.codex/sessions/`
2. Prints the latest assistant reply (`cpend`) or the last N Q&A pairs (`cpend N`)
3. If no reply is available, exits with code 2 and prints a message to stderr

Common scenarios:
- View results after running `cask` in background
- Manually confirm if Codex has responded after a background task completes
- Need to verify if Codex reply matches original question
- Review recent conversation history with Codex

Hints:
- Log file usually located at `~/.codex/sessions/.../rollout-<session>.jsonl`
- If command returns empty, first confirm Codex session is still running (use `/cping` to check)
