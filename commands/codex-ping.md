测试与Codex的连通性

使用方式: /codex-ping

执行要求:
- Claude 执行此命令时，仅需运行 `python3 codex_comm.py --ping`
- 检查Codex进程和管道连接状态

功能说明:
- 检查Codex进程是否存活
- 验证通信管道是否可用
- 快速诊断连接问题

返回结果:
✅ Codex连接正常 (会话正常)    # 连接正常
❌ Codex连接异常: 具体错误信息   # 连接异常

示例:
/codex-ping