控制输出详细程度（仅最终答案或包含细节）

使用方式: /codex-final_only <on|off>

执行要求:
- Claude 执行此命令时，仅需沉默运行 `codex-final_only <on|off>` 并不输出命令结果
- 禁止额外执行其它脚本或附加说明

功能说明:
- on: 仅返回最终答案
- off: 返回附带细节

命令行快捷: `codex-final_only` （可配合 --client-id <ID> 复用会话）
