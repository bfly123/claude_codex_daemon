查看当前Codex服务的运行状态

使用方式: /codex-status

执行要求:
- Claude 执行此命令时，仅需运行 `codex-status` 并返回命令输出
- 不要额外做检测、读取文件或执行其它脚本

这个命令会:
1. 检查Codex服务是否运行
2. 显示实例基本信息
3. 展示当前配置设置
4. 提供进程和通信状态
5. 统计对话轮次信息

参数:
无

前置条件:
- Codex服务应该处于运行状态
- 如果未运行会提示启动

显示信息:
- 实例ID: 当前会话的唯一标识符
- 当前Profile: high/default/low 性能模式
- Show Reasoning: on/off 推理显示开关
- Output Format: final_only/final_with_details 输出格式
- 对话轮次: 已进行的对话次数
- 进程PID: Codex子进程ID
- Socket: Unix socket通信路径

状态说明:
- ✅ 表示服务正常运行
- ❌ 表示服务未运行或异常

示例:
/codex-status
命令行快捷: `codex-status` （可配合 --client-id <ID> 复用会话）

输出示例:
✅ Codex服务运行中:
• 实例ID: 26a62163
• 当前Profile: default
• Show Reasoning: off
• Output Format: final_only
• 对话轮次: 5
• 进程PID: 12345
• Socket: /tmp/codex-user/codex-26a62163-12345.sock

调用方式:
codex-status
