控制是否在Claude界面展示推理过程

使用方式: /codex-reasoning <on|off>

这个命令会:
1. 切换推理显示开关状态
2. 实时更新Codex进程配置
3. 控制输出中是否包含推理摘要
4. 保存配置到历史文件

参数:
- on: 在Claude中展示推理摘要（可能暴露AI思考细节）
- off: 仅展示最终答案（推荐，保持输出纯净）

功能说明:
Show Reasoning控制:
- on: 输出包含AI的推理过程摘要
- off: 只显示最终答案，推理过程仅在内部使用

影响范围:
- 仅影响Claude界面显示内容
- 不影响Codex的实际推理能力
- 推理过程始终在后台进行

使用建议:
- 日常使用建议设为 off，保持对话简洁
- 调试或学习时可以设为 on，观察AI思考过程
- 开启状态可能暴露更多技术细节

前置条件:
- 需要先执行 /codex-start 启动服务
- Codex进程正常运行

示例:
/codex-reasoning on    # 显示推理过程
/codex-reasoning off   # 仅显示最终答案（推荐）

输出示例:
✅ Show Reasoning 已设置为 on（建议开启以获取推理过程）
✅ Show Reasoning 已设置为 off（建议关闭以保持输出纯净）

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-reasoning on'))"
