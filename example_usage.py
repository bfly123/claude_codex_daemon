#!/usr/bin/env python3
"""
Claude-Codex 双窗口模式使用示例
演示如何使用各种命令和功能
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def print_separator(title):
    print("\n" + "=" * 60)
    print(f"📋 {title}")
    print("=" * 60)

def show_usage_examples():
    """显示使用示例"""
    print_separator("Claude-Codex 双窗口模式使用示例")

    print("""
🚀 启动双窗口模式:
    ./claude-codex-dual
    ./claude-codex-dual /path/to/project
    ./claude-codex-dual --resume

📝 在Claude窗口中使用控制命令:

1. 异步模式（推荐，立即返回）:
   /codex-ask "写一个Python函数计算斐波那契数列"

2. 同步模式（等待回复）:
   /codex-ask --wait "解释一下量子计算的基本原理"
   /codex-ask -w "帮我想一个算法解决方案"

3. 状态监控:
   /codex-status          # 查看详细状态
   /codex-ping            # 测试连通性
   /codex-history 5       # 查看最近5条对话

🎯 典型工作流程:

步骤1: 启动双窗口模式
   $ ./claude-codex-dual

步骤2: 在Claude窗口中发送问题
   /codex-ask "帮我分析这段代码的性能瓶颈"

步骤3: 继续在Claude中工作，Codex在独立窗口回复
   # Claude可以继续其他任务
   /codex-status  # 检查状态

步骤4: 查看回复或历史记录
   /codex-history 3

🔧 高级用法:

1. 批量发送问题:
   /codex-ask "问题1"
   /codex-ask "问题2"
   /codex-ask "问题3"

2. 同步等待重要回复:
   /codex-ask --wait "这个方案可行吗？"

3. 监控连接状态:
   /codex-ping
   /codex-status

💡 使用技巧:

- 异步模式适合发送指令后继续工作
- 同步模式适合需要立即结果的场景
- 可以随时切换两种模式
- Codex窗口可以独立进行用户交互
- 所有对话都会自动保存到历史记录

⚠️ 注意事项:

- 确保两个窗口都保持打开状态
- 异步模式下回复可能需要几秒钟
- 同步模式默认超时15秒
- 可以通过环境变量配置超时时间
""")

def test_command_availability():
    """测试命令是否可用"""
    print_separator("测试命令可用性")

    base_dir = Path(__file__).resolve().parent
    commands = [
        ("双窗口启动器", "claude-codex-dual"),
        ("Codex通信模块", "codex_comm.py"),
        ("Ask命令", "codex-ask"),
        ("Status命令", "codex-status"),
        ("Ping命令", "codex-ping"),
        ("History查看器", "codex_history.py")
    ]

    for name, cmd in commands:
        cmd_path = base_dir / cmd
        if cmd_path.exists():
            if cmd_path.is_file() and os.access(cmd_path, os.X_OK):
                print(f"✅ {name}: {cmd} (可执行)")
            elif cmd_path.suffix == '.py':
                print(f"✅ {name}: {cmd} (Python脚本)")
            else:
                print(f"⚠️ {name}: {cmd} (文件存在但可能不可执行)")
        else:
            print(f"❌ {name}: {cmd} (不存在)")

def show_help_info():
    """显示帮助信息"""
    print_separator("获取帮助信息")

    print("""
📖 查看详细帮助:

1. 双窗口启动器帮助:
   ./claude-codex-dual --help

2. 通信模块帮助:
   python3 codex_comm.py --help

3. 历史记录帮助:
   python3 codex_history.py --help

📚 文档文件:

- README-DUAL.md     # 完整使用指南
- TODO.md           # 开发计划和进度
- commands/*.md     # 各命令的详细文档

🔗 相关文件:

- .codex-session           # 项目会话信息（自动生成）
- /tmp/codex-user/*/       # 运行时目录（自动生成）
""")

def main():
    """主函数"""
    print("🎯 Claude-Codex 双窗口模式")
    print("   使用示例和功能演示")

    # 显示使用示例
    show_usage_examples()

    # 测试命令可用性
    test_command_availability()

    # 显示帮助信息
    show_help_info()

    print_separator("开始使用")
    print("""
🚀 准备开始使用双窗口模式:

1. 启动双窗口:
   $ ./claude-codex-dual

2. 测试连接:
   /codex-ping

3. 发送第一个问题:
   /codex-ask "你好，请介绍一下自己"

4. 查看状态:
   /codex-status

享受全新的双窗口协作体验！ 🎉
""")

if __name__ == "__main__":
    main()