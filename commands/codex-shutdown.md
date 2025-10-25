关闭 Codex 守护进程以及所有活动的 Codex 实例。

使用方式: /codex-shutdown

该命令会：
1. 请求守护进程依次停止每个客户端的 Codex 子进程；
2. 关闭后台守护进程自身并清理 Unix socket；
3. 此后需要重新运行 `claude-codex` 才能再次使用 Codex 服务。

前置条件:
- 守护进程正在运行。

注意:
- `/codex-stop` 仅关闭当前客户端实例，不影响其他会话；
- `/codex-shutdown` 会停止所有实例，慎用。
