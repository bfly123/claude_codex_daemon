Use `gpend` to fetch latest reply from Gemini logs (`~/.gemini/tmp/.../chats/session-*.json`).

Trigger conditions (any match):
- User mentions gpend/Gpend
- User wants to view/fetch/get Gemini reply/response
- User asks for recent N Gemini conversations/replies (e.g. "调取最近5条gemini回复", "show last 3 gemini messages")

Execution:
- `gpend` - fetch latest single reply: `Bash(gpend)`
- `gpend N` - fetch last N conversations (Q&A pairs): `Bash(gpend N)` (e.g. `gpend 5`)
- Keep command execution silent, no additional analysis after execution

Output format (when N > 1):
```
Q: user question 1
A: gemini reply 1
---
Q: user question 2
A: gemini reply 2
```

Output contract:
- stdout: reply text (or Q&A pairs)
- stderr: message when no reply / errors
- exit code: 0 = got reply, 2 = no reply available, 1 = error

Common scenarios:
- View reply after running `gask` in background
- Continue getting reply after a foreground/background wait returns empty/timeout
- Review recent conversation history with Gemini

Hints:
- If command exits with code 2, first confirm Gemini session is still running (use `/gping` to check)
