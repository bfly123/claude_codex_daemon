#!/bin/bash

# Claude Codex Lock 一键启动脚本
# 自动设置环境、拷贝命令文件并启动 Codex 服务

set -e

echo "🚀 Claude Codex Lock - 一键启动"
echo "================================"

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "📁 项目目录: $PROJECT_DIR"

# 检查 Python 版本
echo "📋 检查系统要求..."
python3 --version >/dev/null 2>&1 || { echo "❌ 错误: 需要 Python 3.8 或更高版本"; exit 1; }

# 检查必要文件
echo "🔍 验证项目文件..."
required_files=(
    "claude_codex_manager.py"
    "codex_commands.py"
    "codex_process.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$PROJECT_DIR/$file" ]]; then
        echo "❌ 错误: 缺少必要文件 $file"
        exit 1
    fi
done

echo "✅ 项目文件验证通过"

# 配置运行目录
RUNTIME_DIR="$PROJECT_DIR/.runtime"
echo "📦 配置运行目录..."
mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"
export CODEX_RUNTIME_DIR="$RUNTIME_DIR"
echo "✅ 运行目录: $RUNTIME_DIR"

# 设置 Python 路径
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# 检查并创建 .claude/commands 目录
CLAUDE_DIR="$PROJECT_DIR/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands"

echo "📂 设置 Claude 命令目录..."
if [[ ! -d "$CLAUDE_DIR" ]]; then
    mkdir -p "$CLAUDE_DIR"
    echo "✅ 创建 .claude 目录"
fi

if [[ ! -d "$COMMANDS_DIR" ]]; then
    mkdir -p "$COMMANDS_DIR"
    echo "✅ 创建 commands 目录"
fi

# 检查是否需要拷贝命令文件
echo "🔄 检查命令文件状态..."
command_files=(
    "codex-start.md"
    "codex-ask.md"
    "codex-stop.md"
    "codex-status.md"
    "codex-config.md"
    "codex-reasoning.md"
    "codex-final_only.md"
    "codex-help.md"
)

need_copy=false
for file in "${command_files[@]}"; do
    if [[ ! -f "$COMMANDS_DIR/$file" ]]; then
        need_copy=true
        break
    fi
done

if [[ "$need_copy" == true ]]; then
    echo "📋 拷贝命令文件..."

    # 从项目级commands目录拷贝到.claude/commands
    if [[ -d "$PROJECT_DIR/commands" ]]; then
        cp "$PROJECT_DIR"/commands/*.md "$COMMANDS_DIR/" 2>/dev/null || echo "项目级commands目录为空，继续创建默认文件..."
    fi

    # 如果项目级目录没有文件，创建默认文件
    cat > "$COMMANDS_DIR/codex-start.md" << 'EOF'
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
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-start'))"
EOF

    cat > "$COMMANDS_DIR/codex-ask.md" << 'EOF'
向当前Codex实例发起提问

使用方式: /codex-ask <问题>

这个命令会:
1. 检查Codex服务是否已启动
2. 通过socket向Codex进程发送问题
3. 获取AI的响应结果
4. 自动保存对话历史
5. 返回格式化的回答内容

参数:
- 问题 (必需): 要向Codex询问的问题或任务描述

前置条件:
- 需要先执行 /codex-start 启动服务
- Codex进程正常运行

功能特性:
- 自动重试机制：通信失败时最多重试3次
- 实例验证：确保响应来自正确的实例
- 历史记录：自动保存对话轮次
- 配置继承：使用当前的profile和输出设置

示例:
/codex-ask 解释一下量子计算的基本原理
/codex-ask 帮我写一个Python函数计算斐波那契数列
/codex-ask 分析这段代码的性能瓶颈

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-ask 你的问题'))"
EOF

    cat > "$COMMANDS_DIR/codex-stop.md" << 'EOF'
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
EOF

    cat > "$COMMANDS_DIR/codex-status.md" << 'EOF'
查看当前Codex服务的运行状态

使用方式: /codex-status

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
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-status'))"
EOF

    cat > "$COMMANDS_DIR/codex-config.md" << 'EOF'
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
EOF

    cat > "$COMMANDS_DIR/codex-reasoning.md" << 'EOF'
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
EOF

    cat > "$COMMANDS_DIR/codex-final_only.md" << 'EOF'
控制输出详细程度（仅最终答案或包含细节）

使用方式: /codex-final_only <on|off>

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

前置条件:
- 需要先执行 /codex-start 启动服务
- Codex进程正常运行

示例:
/codex-final_only on   # 仅输出最终答案（推荐）
/codex-final_only off  # 返回额外细节信息（调试用）

输出示例:
✅ Output Format 已切换为 final_only（推荐开启以避免额外噪音）
✅ Output Format 已切换为 final_with_details（将返回额外细节信息）

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-final_only on'))"
EOF

    cat > "$COMMANDS_DIR/codex-help.md" << 'EOF'
显示Codex命令系统的完整帮助信息

使用方式: /codex-help

这个命令会:
1. 显示所有可用的Codex命令列表
2. 提供每个命令的简要说明
3. 给出使用示例和最佳实践
4. 包含维护建议和故障排除提示

参数:
无

命令列表:

基础命令:
• /codex-start
  - 说明: 启动或重新连接Codex进程，自动生成专属socket和实例ID
  - 使用: 首次对话前执行一次即可，如已运行会返回当前状态

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
1. 首次使用 → /codex-start
2. 日常查询 → /codex-ask <问题>
3. 配置调节 → /codex-config <档位>
4. 状态检查 → /codex-status
5. 结束使用 → /codex-stop

维护建议:
1. 需要撤回最近一轮或清理上下文时，可结合 Claude 的 /rewind 或 /clear
2. 切换档位后如遇回答异常，优先执行 `/codex-config` 查看当前状态
3. 若长时间未用，建议 `/codex-stop` 后再 `/codex-start` 以释放资源
4. 遇到通信错误时，尝试重启服务：/codex-stop → /codex-start

调用方式:
python3 -c "from codex_commands import handle_codex_command; print(handle_codex_command('/codex-help'))"
EOF

    echo "✅ 命令文件拷贝完成"
else
    echo "✅ 命令文件已存在，跳过拷贝"
fi

# 检查是否已经运行
echo "🔍 检查服务状态..."
if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from codex_commands import handle_codex_command
status = handle_codex_command('/codex-status')
if '运行中' in status:
    print('✅ Codex 服务已在运行')
    print(status)
    exit(0)
except Exception as e:
    print(f'状态检查失败: {e}')
" 2>/dev/null; then
    echo ""
    echo "🎉 Codex 服务已运行！"
    echo ""
    echo "📋 可在 Claude Code 中使用以下命令:"
    echo "   /codex-start      # 启动服务"
    echo "   /codex-ask 问题    # 向 Codex 提问"
    echo "   /codex-status     # 查看状态"
    echo "   /codex-config     # 配置调节"
    echo "   /codex-help       # 查看帮助"
    echo "   /codex-stop       # 停止服务"
    echo ""
    echo "💡 提示: 重启 Claude Code 以刷新命令列表"
    exit 0
fi

echo "🚀 启动 Codex 服务..."

# 启动服务并验证启动是否成功
if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from codex_commands import handle_codex_command

# 启动服务
result = handle_codex_command('/codex-start')
print(result)

# 验证启动是否成功
status = handle_codex_command('/codex-status')
if '运行中' in status:
    print('✅ 服务启动成功')
    exit(0)
else:
    print('❌ 服务启动失败')
    exit(1)
" 2>/dev/null; then
    echo ""
    echo "🎉 Codex 服务启动成功！"
    echo ""
    echo "📋 可在 Claude Code 中使用以下命令:"
    echo "   /codex-start      # 启动服务"
    echo "   /codex-ask 问题    # 向 Codex 提问"
    echo "   /codex-status     # 查看状态"
    echo "   /codex-config     # 配置调节"
    echo "   /codex-help       # 查看帮助"
    echo "   /codex-stop       # 停止服务"
    echo ""
    echo "🔧 配置示例:"
    echo "   /codex-config high    # 高性能模式"
    echo "   /codex-reasoning on   # 显示推理过程"
    echo "   /codex-final_only on  # 仅显示最终答案"
    echo ""
    echo "💡 提示: 重启 Claude Code 以刷新命令列表"
else
    echo "❌ 服务启动失败，请检查错误信息"
    exit 1
fi
