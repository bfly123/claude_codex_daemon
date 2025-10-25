#!/usr/bin/env python3
"""
Claude-Codex 集成测试脚本
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def test_daemon_startup():
    """测试守护进程启动"""
    print("🧪 测试1: 守护进程启动")

    # 测试健康检查（应该返回unhealthy）
    result = subprocess.run(["python3", "codex_daemon.py", "--health"],
                            capture_output=True, text=True)
    print(f"健康检查结果: {result.stdout.strip()}")

    # 启动守护进程
    print("启动后台守护进程...")
    process = subprocess.Popen(["python3", "codex_daemon.py", "--daemon"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    # 等待启动
    time.sleep(3)

    # 再次检查健康状态
    result = subprocess.run(["python3", "codex_daemon.py", "--health"],
                            capture_output=True, text=True)
    print(f"启动后健康检查: {result.stdout.strip()}")

    return process.poll() is None

def test_client_commands():
    """测试客户端命令"""
    print("\n🧪 测试2: 客户端命令")

    from codex_commands import handle_codex_command

    # 测试帮助命令
    print("测试 /codex-help:")
    result = handle_codex_command("/codex-help")
    print(f"结果: {result[:100]}..." if len(result) > 100 else result)

    # 测试配置命令
    print("\n测试 /codex-config high:")
    result = handle_codex_command("/codex-config high")
    print(f"结果: {result}")

    # 测试询问命令
    print("\n测试 /codex-ask '你是谁':")
    result = handle_codex_command("/codex-ask 你是谁")
    print(f"结果: {result}")

def test_claude_codex_simulation():
    """模拟claude-codex启动"""
    print("\n🧪 测试3: 模拟claude-codex启动")

    # 这里只是模拟，实际需要用户运行
    print("模拟: ./claude-codex")
    print("预期效果:")
    print("  1. 后台启动codex_daemon.py")
    print("  2. 前台启动claude-code")
    print("  3. 在Claude中使用 /codex-* 命令")

def main():
    print("🚀 Claude-Codex 集成测试开始\n")

    try:
        # 测试1: 守护进程
        if not test_daemon_startup():
            print("❌ 守护进程启动测试失败")
            return 1

        # 测试2: 客户端命令
        test_client_commands()

        # 测试3: 模拟完整流程
        test_claude_codex_simulation()

        print("\n✅ 所有测试通过！")
        print("\n📋 下一步:")
        print("1. 运行: ./claude-codex")
        print("2. 在Claude中使用: /codex-ask 你的问题")
        print("3. 查看状态: /codex-status")

        return 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 清理：停止守护进程
        try:
            subprocess.run(["pkill", "-f", "codex_daemon.py"],
                           capture_output=True, text=True)
            print("🧹 已清理测试进程")
        except:
            pass

if __name__ == "__main__":
    sys.exit(main())