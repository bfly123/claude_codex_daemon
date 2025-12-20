通过 `gask-w` 命令将指令转发到 Gemini 会话，并同步等待回复（支持 tmux / WezTerm）。

执行方式:
- 后台运行 `Bash(gask-w "<转发内容>", run_in_background=true)`
- 发送后立即继续对话，不阻塞等待
- 需要结果时使用 `TaskOutput(task_id, block=true)` 获取

参数说明:
- `<转发内容>` 必填，会被转发到 Gemini 会话
- 返回 task_id，可用于后续获取结果

交互流程:
1. 后台发送到 Gemini
2. 立即返回 task_id
3. Claude 继续处理其他任务
4. 需要时通过 TaskOutput 获取回复

示例:
- `Bash(gask-w "解释一下这段代码", run_in_background=true)` -> 返回 task_id
- `TaskOutput(task_id, block=true)` -> 获取 Gemini 回复

提示:
- 发送后可继续对话，无需等待
- 使用 `/gpend` 查看最新回复
- 使用 `TaskOutput` 获取特定任务结果
