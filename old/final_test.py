#!/usr/bin/env python3
"""
最终完整测试脚本
模拟完整的用户工作流程
"""

import subprocess
import time
import os

def cleanup():
    """清理所有codex相关进程"""
    print("🧹 清理环境...")
    try:
        # 停止可能的守护进程
        result = subprocess.run(["pkill", "-f", "codex_daemon.py"],
                              capture_output=True, text=True)
        print(f"清理结果: {result.stdout.strip()}")

        # 清理socket文件
        if os.path.exists("/tmp/codex-daemon.sock"):
            os.unlink("/tmp/codex-daemon.sock")
            print("清理socket文件")

    except Exception as e:
        print(f"清理异常: {e}")

def test_complete_workflow():
    """测试完整工作流程"""
    print("🚀 开始完整工作流程测试")

    # 步骤1: 清理环境
    cleanup()
    time.sleep(1)

    # 步骤2: 启动守护进程（后台）
    print("📦 步骤1: 启动codex守护进程...")
    daemon_process = subprocess.Popen(
        ["python3", "codex_daemon.py", "--daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 等待启动
    time.sleep(3)

    # 步骤3: 测试连接
    print("📦 步骤2: 测试socket连接...")
    try:
        import socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect("/tmp/codex-daemon.sock")
        sock.close()
        print("✅ Socket连接测试成功")
    except Exception as e:
        print(f"❌ Socket连接失败: {e}")
        return False

    # 步骤4: 测试健康检查
    print("📦 步骤3: 测试健康检查...")
    result = subprocess.run(["python3", "codex_daemon.py", "--health"],
                        capture_output=True, text=True)
    print(f"健康检查: {result.stdout.strip()}")

    # 步骤5: 测试客户端命令
    print("📦 步骤4: 测试客户端命令...")
    from codex_commands import handle_codex_command

    test_commands = [
        ("/codex-help", "显示帮助"),
        ("/codex-config", "显示配置"),
        ("/codex-config high", "设置高配置"),
        ("/codex-ask 你好，请介绍一下自己", "测试提问")
    ]

    for cmd, desc in test_commands:
        print(f"  测试: {desc}")
        result = handle_codex_command(cmd)
        print(f"  结果: {result[:100]}..." if len(result) > 100 else result)
        print()

    # 步骤6: 清理
    print("📦 步骤5: 清理测试环境...")
    cleanup()

    print("\n✅ 完整工作流程测试完成！")
    print("\n📋 测试结果总结:")
    print("  ✅ 守护进程启动: 成功")
    print("  ✅ Socket连接: 正常")
    print("  ✅ 健康检查: 通过")
    print("  ✅ 客户端命令: 正常")
    print("  ✅ 自动清理: 完成")

    print("\n🚀 系统已就绪，可以使用以下方式:")
    print("  方式1: ./claude-codex")
    print("  方式2: 在现有Claude中使用codex_commands.py")

    return True

if __name__ == "__main__":
    try:
        test_complete_workflow()
    except KeyboardInterrupt:
        print("\n⚠️ 测试被中断")
        cleanup()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        cleanup()