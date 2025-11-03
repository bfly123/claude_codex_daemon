通过 `cast-w` 同步将 Claude 指令发送到 Codex，并在 tmux 会话中立即执行。

执行方式:
- Claude 端使用 `Bash(cast-w "<问题>")`，无需补充其他说明
- 本地终端可直接运行 `cast-w <问题>`，默认等价于调用 `/cask-w`

参数说明:
- `<问题>` 必填，若未以 `/` 开头则自动加上 `/cask-w `
- 以 `/` 起始的完整斜杠命令会按原样转发（例如 `/cping`）

示例:
- `Bash(cast-w "检查当前仓库状态")`
- `Bash(cast-w "/cask-w 解释最新一次提交")`

提示:
- 需确保 `claude_codex` 已启动并保持活跃
- 若未找到会话，将提示重新运行 `claude_codex`
