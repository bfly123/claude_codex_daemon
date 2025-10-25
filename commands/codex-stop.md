停止当前Codex服务并清理资源

使用方式: /codex-stop

这个命令会:
1. 向Codex子进程发送终止信号
2. 等待子进程优雅退出
3. 清理socket通信文件
4. 更新服务状态标记
5. 保留历史文件以便后续恢复

参数:
无

前置条件:
- Codex服务必须处于运行状态
- 有权限终止相关进程

功能特性:
- 优雅关闭：使用SIGTERM信号正常终止
- 资源清理：自动删除socket文件
- 状态同步：更新内部状态标记
- 历史保留：对话历史文件不会被删除

清理内容:
- Unix socket文件
- 进程监控线程
- 内存中的服务状态

保留内容:
- 对话历史文件 (codex-*-history.json)
- 实例配置信息
- 用户偏好设置

示例:
/codex-stop

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-stop'))"
