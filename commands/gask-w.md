通过 `gask-w` 命令将指令转发到 Gemini tmux 会话，并同步等待回复。

执行方式:
- 沉默运行 `Bash(gask-w "<转发内容>")`，执行完毕后不做其他分析、推理或额外操作
- 在终端中也可执行 `gask-w <转发内容>`，效果等同

参数说明:
- `<转发内容>` 必填，会被转发到 Gemini tmux 会话
- ⚠️ 注意：gask-w 会等待 Gemini 回复后再返回

示例:
- `Bash(gask-w "解释一下这段代码")`
- `Bash(gask-w "这个方案有什么建议？")`

提示:
- gask-w 会阻塞等待 Gemini 回复
- 超时后可使用 `gpend` 查看回复
- 适合需要获取 Gemini 反馈的场景
