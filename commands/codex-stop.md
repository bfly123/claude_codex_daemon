停止当前Codex服务并清理资源

使用方式: /codex-stop

执行要求:
- Claude 执行此命令时，仅需沉默运行 `codex-stop` 并不输出命令结果
- 禁止额外执行其它脚本或附加说明

功能说明:
- 终止当前实例并清理 socket

命令行快捷: `codex-stop` （可配合 --client-id <ID> 复用会话）
