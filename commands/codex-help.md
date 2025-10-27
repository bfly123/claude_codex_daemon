显示Codex命令系统的完整帮助信息

使用方式: /codex-help

这个命令会:
1. 显示所有可用的Codex命令列表
2. 提供每个命令的简要说明
3. 给出使用示例和最佳实践
4. 包含维护建议和故障排除提示

参数:
无

服务管理:
- Codex守护进程由 `claude-codex` 自动启动与重连，无需额外的手动启动命令

命令列表:

基础命令:
• /codex-ask <问题>
  - 说明: 向当前Codex实例发起提问，自动携带当前模型强度/输出配置
  - 使用: `/codex-ask 解释一下数据库分片`

• /codex-status
  - 说明: 查看实例ID、当前profile、推理/输出开关、进程PID等运行信息
  - 使用: 检查服务状态，获取详细运行数据

• /codex-stop
  - 说明: 手动停止当前Codex子进程并清理socket，Claude退出时会自动调用
  - 使用: 主动释放资源，重启服务前使用

配置命令:
• /codex-config [high|default|low]
  - 说明: 不带参数查看档位和开关；附带参数可切换模型强度
  - 建议: 详细模式用 high，快速问答用 low，default 保持平衡

• /codex-reasoning <on|off>
  - 说明: 控制是否在Claude侧展示推理摘要，on 仅影响展示不影响真实推理
  - 建议: 默认为 off 以保持回答纯净，除非调试需要

• /codex-final_only <on|off>
  - 说明: on 时仅返回最终答案；off 时附带额外细节或中间说明
  - 建议: 生产使用保持 on，调试场景可临时关闭

• /codex-help
  - 说明: 显示本帮助信息
  - 使用: 获取命令说明和使用指导

使用工作流:
1. 打开终端运行 `claude-codex`（守护进程会自动启动并保持运行）
2. 日常查询 → /codex-ask <问题>
3. 配置调节 → /codex-config <档位>
4. 状态检查 → /codex-status
5. 结束使用 → /codex-stop

维护建议:
1. 需要撤回最近一轮或清理上下文时，可结合 Claude 的 /rewind 或 /clear
2. 切换档位后如遇回答异常，优先执行 `/codex-config` 查看当前状态
3. 若长时间未用，建议 `/codex-stop` 后重新运行 `claude-codex` 以释放资源并拉起新实例
4. 遇到通信错误时，尝试重启服务：/codex-stop → 在终端执行 `claude-codex`

故障排除:
• Claude Code 中启动卡顿
  - 原因：输出缓冲区问题导致异步输出延迟显示
  - 解决：使用 python3 -u 参数或 stdbuf 命令
  - 示例：codex-status

• 进程异常退出
  - 检查：ps aux | grep codex
  - 清理：pkill -f "codex" && rm -rf /tmp/codex-*
  - 重启：在终端执行 `claude-codex`

• Socket 连接失败
  - 检查：ls -la /tmp/codex-*/
  - 重建：/codex-stop → 在终端执行 `claude-codex`

调用方式:
codex-help
