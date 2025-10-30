使用 `cpend` 从 Codex 官方日志中抓取最新回复，适合异步模式或超时后的补充查询。

执行方式:
- Claude 端使用 `Bash(cpend)`，命令执行过程保持静默
- 本地终端可直接运行 `cpend`

功能特点:
1. 解析 `.codex-session` 记录的日志路径，定位本次会话的最新 JSONL 文件
2. 读取尾部消息并返回 Codex 最近一次输出
3. 若无新内容，将提示“暂无 Codex 回复”

常见场景:
- `cask` 异步提交多条任务后集中查看结果
- `cask-w` 因超时退出后手动确认 Codex 是否已回应
- 需要核对 Codex 回复与原始问题是否匹配

提示:
- 日志文件通常位于 `~/.codex/sessions/.../rollout-<session>.jsonl`
- 如果命令返回空，请先确认 Codex 会话仍在运行（可用 `/cping` 检查）
