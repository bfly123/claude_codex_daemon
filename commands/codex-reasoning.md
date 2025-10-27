控制是否在Claude界面展示推理过程

使用方式: /codex-reasoning <on|off>

执行要求:
- Claude 执行此命令时，仅需沉默运行 `codex-reasoning <on|off>` 并不输出命令结果
- 禁止额外执行其它脚本或附加说明

功能说明:
- on: 内部开启推理展示
- off: 保持隐藏推理

命令行快捷: `codex-reasoning` （可配合 --client-id <ID> 复用会话）
