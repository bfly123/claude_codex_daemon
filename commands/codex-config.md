查看或配置Codex服务的性能模式

使用方式:
- /codex-config                    # 查看当前配置
- /codex-config <high|default|low> # 切换性能模式

这个命令会:
1. 显示当前配置状态（无参数时）
2. 切换AI模型的性能档位（有参数时）
3. 实时更新Codex进程配置
4. 保存配置到历史文件

参数:
- 无参数: 显示当前所有配置信息
- high: 高性能模式，深度分析，适合复杂问题
- default: 平衡模式，默认设置，适合日常使用
- low: 快速模式，简洁回答，适合简单查询

支持的别名:
- high: high
- default: default, medium, mid, normal, balanced
- low: low

配置说明:
Profile模式:
- high: 最强推理能力，详细分析，响应时间较长
- default: 平衡速度和质量，推荐日常使用
- low: 快速响应，简洁回答，适合简单查询

其他配置项:
- Show Reasoning: 控制是否显示推理过程
- Output Format: 控制输出详细程度
- Instance ID: 当前实例的唯一标识符

前置条件:
- 需要先执行 /codex-start 启动服务

示例:
/codex-config                           # 查看当前配置
/codex-config high                      # 切换到高性能模式
/codex-config default                   # 切换到平衡模式
/codex-config low                       # 切换到快速模式

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-config high'))"
