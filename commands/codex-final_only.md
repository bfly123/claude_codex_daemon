控制输出详细程度（仅最终答案或包含细节）

使用方式: /codex-final_only <on|off>

执行要求:
- Claude 执行此命令时，仅需运行 `codex-final_only <on|off>` 并返回命令输出
- 不要额外执行其它脚本或步骤

这个命令会:
1. 切换输出格式控制开关
2. 实时更新Codex进程配置
3. 控制返回内容的详细程度
4. 保存配置到历史文件

参数:
- on: 仅返回最终答案（推荐，避免额外噪音）
- off: 返回最终答案及额外细节（用于调试）

功能说明:
Output Format控制:
- final_only (on): 只显示AI的最终回答
- final_with_details (off): 包含额外细节信息和中间说明

输出内容对比:
final_only模式:
- 干净简洁的最终答案
- 适合直接使用和分享
- 减少不必要的信息干扰

final_with_details模式:
- 包含处理过程和额外信息
- 适合调试和问题排查
- 可能包含技术细节和元数据

使用建议:
- 生产使用建议设为 on，保持输出简洁
- 调试问题时可以设为 off，获取更多上下文
- 日常对话推荐使用 on 模式

示例:
/codex-final_only on   # 仅输出最终答案（推荐）
/codex-final_only off  # 返回额外细节信息（调试用）
命令行快捷: `codex-final_only on` （可配合 --client-id <ID> 复用会话）

输出示例:
✅ Output Format 已切换为 final_only（推荐开启以避免额外噪音）
✅ Output Format 已切换为 final_with_details（将返回额外细节信息）

调用方式:
codex-final_only on
