启动或重新连接Codex服务

使用方式: /codex-start

这个命令会:
1. 生成唯一的实例ID和socket路径
2. 启动Codex子进程并建立通信
3. 自动监控进程状态，崩溃后重启
4. 保存会话配置和历史记录
5. 如果服务已运行，返回当前状态

参数:
无

功能特性:
- 实例锁定：每个Claude实例拥有独立的Codex服务
- 自动恢复：进程异常退出后自动重启
- 会话持久化：重启后完整恢复对话历史和配置
- 安全隔离：严格的权限控制和用户隔离

示例:
/codex-start

调用方式:

终端环境:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-start'))"

Claude Code 环境 (必须使用 -u 参数):
python3 -u -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-start'))"

或者使用 stdbuf:
stdbuf -o0 -e0 python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-start'))"

手动测试验证:
1. 在终端中执行上述命令
2. 观察输出是否显示 "[Codex Recovery]" 等调试信息
3. 确认最后显示 "✅ Codex服务已启动" 消息
4. 正常启动时间应在 0.1-0.3 秒内完成

故障排除:
如果在 Claude Code 中遇到卡顿，必须使用 python3 -u 参数或 stdbuf 来解决输出缓冲问题
