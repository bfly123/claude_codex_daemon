查看或配置Codex服务的性能模式

使用方式: /codex-config [high|default|low]

执行要求:
- Claude 执行此命令时，仅需沉默运行 `codex-config`（或 `codex-config <档位>`），不输出命令结果
- 禁止额外执行其它脚本或附加说明

功能说明:
- 无参数时返回当前配置（内部使用）
- 带参数时切换性能档位（high/default/low）

命令行快捷: `codex-config` （可配合 --client-id <ID> 复用会话）

