查看Codex连接状态和会话信息

使用方式: /codex-status

执行要求:
- Claude 执行此命令时，仅需运行 `python3 codex_comm.py --status`
- 显示详细的会话和连接状态信息

显示信息:
- 会话ID和运行目录
- Codex进程状态
- 管道连接状态
- 历史记录数量
- 错误信息（如有）

示例:
/codex-status

输出示例:
📊 Codex状态:
   session_id: dual-1704067200-12345
   runtime_dir: /tmp/codex-user/dual-1704067200-12345
   healthy: True
   status: 会话正常
   input_fifo: /tmp/codex-user/dual-1704067200-12345/input.fifo
   output_fifo: /tmp/codex-user/dual-1704067200-12345/output.fifo
   codex_pid: 12345
   history_files: 5

