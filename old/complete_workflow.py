#!/usr/bin/env python3
"""
完整工作流程验证脚本
解决路径问题并提供独立的组件测试
"""

import subprocess
import os
import sys
import time

def stop_all_codex():
    """停止所有Codex相关进程"""
    print("🧹 停止所有Codex进程...")

    # 停止守护进程
    try:
        result = subprocess.run(["pkill", "-f", "codex_daemon.py"],
                              capture_output=True, text=True)
        print(f"守护进程清理: {result.stdout.strip()}")
    except:
        pass

    # 清理socket文件
    try:
        os.unlink("/tmp/codex-daemon.sock")
        print("清理socket文件")
    except:
        pass

def test_daemon_only():
    """测试守护进程单独运行"""
    print("🧪 测试1: 守护进程单独测试")

    # 前台启动测试
    print("  前台模式测试 (5秒)...")
    process = subprocess.Popen(
        ["python3", "codex_daemon.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        stdout, stderr = process.communicate(timeout=5)
        print(f"  前台输出: {stdout[:200]}..." if stdout else "无输出")

        # 检查健康状态
        time.sleep(1)
        health_result = subprocess.run(
            ["python3", "codex_daemon.py", "--health"],
            capture_output=True, text=True
        )
        print(f"  健康检查: {health_result.stdout.strip()}")

        return process.poll() is None

    except subprocess.TimeoutExpired:
        process.terminate()
        print("  ❌ 前台模式超时")
        return False
    except Exception as e:
        print(f"  ❌ 前台测试失败: {e}")
        return False

def test_client_only():
    """测试客户端单独运行"""
    print("\n🧪 测试2: 客户端单独测试")

    # 首先启动守护进程
    print("  启动守护进程 (--daemon)...")
    daemon_process = subprocess.Popen(
        ["python3", "codex_daemon.py", "--daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 等待启动
    time.sleep(3)

    # 测试客户端命令
    from codex_commands import handle_codex_command

    test_commands = [
        ("/codex-help", "显示帮助"),
        ("/codex-config", "查看配置"),
        ("/codex-config high", "设置高配置"),
        ("/codex-status", "查看状态"),
    ]

    all_passed = True
    for cmd, desc in test_commands:
        print(f"  测试: {desc}")
        try:
            result = handle_codex_command(cmd)
            if result and "error" not in result and "❌" not in result:
                print(f"    ✅ {result[:100]}..." if len(result) > 100 else result)
            else:
                print(f"    ❌ {result}")
                all_passed = False
        except Exception as e:
            print(f"    ❌ 异常: {e}")
            all_passed = False

    # 清理
    daemon_process.terminate()
    try:
        daemon_process.wait(timeout=3)
    except:
        pass

    print(f"\n📊 客户端测试结果: {'通过' if all_passed else '失败'}")
    return all_passed

def test_complete_workflow():
    """测试完整工作流程"""
    print("\n🧪 测试3: 完整工作流程测试")

    # 停止所有进程
    stop_all_codex()
    time.sleep(1)

    # 使用绝对路径启动守护进程
    script_dir = os.path.dirname(os.path.abspath(__file__))
    daemon_cmd = [f"python3", f"{script_dir}/codex_daemon.py", "--daemon"]

    print(f"  启动守护进程: {' '.join(daemon_cmd)}")
    daemon_process = subprocess.Popen(daemon_cmd)

    # 等待启动
    time.sleep(3)

    # 检查启动结果
    if daemon_process.poll() is not None:
        stdout, stderr = daemon_process.communicate(timeout=2)
        print(f"  ❌ 守护进程启动失败: {stderr}")
        return False

    time.sleep(2)

    # 检查socket和健康状态
    print("  检查服务状态...")

    # Socket测试
    socket_ok = False
    try:
        import socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect("/tmp/codex-daemon.sock")
        sock.close()
        socket_ok = True
        print("  ✅ Socket连接测试通过")
    except Exception as e:
        print(f"  ❌ Socket连接失败: {e}")

    # 健康检查
    health_ok = False
    try:
        health_result = subprocess.run(
            ["python3", f"{script_dir}/codex_daemon.py", "--health"],
            capture_output=True, text=True
        )
        if "healthy" in health_result.stdout:
            health_ok = True
            print("  ✅ 健康检查通过")
        else:
            print(f"  ❌ 健康检查失败: {health_result.stdout.strip()}")
    except Exception as e:
        print(f"  ❌ 健康检查异常: {e}")

    # 如果守护进程正常，测试客户端
    if socket_ok and health_ok:
        print("\n  守护进程正常运行，测试客户端功能...")

        # 更新Python路径确保能找到codex_commands
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            print(f"  更新Python路径: {current_dir}")

        # 测试客户端
        from codex_commands import handle_codex_command

        client_test = test_client_only()

        # 清理
        daemon_process.terminate()
        try:
            daemon_process.wait(timeout=3)
        except:
            pass

        return client_test
    else:
        print("  ❌ 守护进程未正常运行")
        return False

def main():
    print("🚀 Claude-Codex 完整工作流程验证开始\n")

    # 选择测试模式
    print("可用测试:")
    print("1. 守护进程单独测试")
    print("2. 客户端单独测试")
    print("3. 完整工作流程测试")
    print("0. 退出")

    try:
        choice = input("\n请选择测试模式 (0-3): ").strip()

        if choice == "0":
            print("退出测试")
            return 0
        elif choice == "1":
            success = test_daemon_only()
        elif choice == "2":
            success = test_client_only()
        elif choice == "3":
            success = test_complete_workflow()
        else:
            print("❌ 无效选择")
            return 1

        if success:
            print("\n✅ 测试通过！")
            return 0
        else:
            print("\n❌ 测试失败！")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ 测试被中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())