#!/usr/bin/env python3
"""
Test script to verify codex daemon fixes
"""

import subprocess
import time
import os
import json
import signal
import sys

def cleanup():
    """清理之前的进程和文件"""
    for pid_file in ['/tmp/codex-daemon.pid', '/tmp/codex-daemon.sock']:
        if os.path.exists(pid_file):
            os.unlink(pid_file)

def test_daemon_startup():
    """测试守护进程启动"""
    print("🔧 测试1: 守护进程后台启动")
    cleanup()

    result = subprocess.run(['python3', 'codex_daemon.py', '--daemon'],
                          capture_output=True, text=True, timeout=10)

    if result.returncode != 0:
        print(f"❌ 守护进程启动失败: {result.stderr}")
        return False

    time.sleep(2)  # 等待启动

    if not os.path.exists('/tmp/codex-daemon.pid'):
        print("❌ PID文件未创建")
        return False

    if not os.path.exists('/tmp/codex-daemon.sock'):
        print("❌ Socket文件未创建")
        return False

    # 验证PID文件中的进程是否真实存在
    with open('/tmp/codex-daemon.pid', 'r') as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, 0)  # 检查进程是否存在
        print(f"✅ 守护进程启动成功 (PID: {pid})")
        return True
    except OSError:
        print("❌ PID文件中的进程不存在")
        return False

def test_health_check():
    """测试健康检查"""
    print("🔧 测试2: 健康检查功能")

    result = subprocess.run(['python3', 'codex_daemon.py', '--health'],
                          capture_output=True, text=True, timeout=10)

    if result.returncode == 0:
        health_data = json.loads(result.stdout)
        if health_data.get("status") == "healthy":
            print("✅ 健康检查通过")
            return True
        else:
            print(f"❌ 健康检查失败: {health_data.get('reason')}")
            return False
    else:
        print(f"❌ 健康检查命令失败: {result.stderr}")
        return False

def test_socket_communication():
    """测试Socket通信"""
    print("🔧 测试3: Socket通信")

    try:
        import socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect('/tmp/codex-daemon.sock')

        # 发送帮助命令
        request = {"command": "/codex-help"}
        request_json = json.dumps(request, ensure_ascii=False)
        sock.send(request_json.encode('utf-8') + b'\n')

        # 接收响应
        response = sock.recv(4096).decode('utf-8').strip()
        response_data = json.loads(response)

        sock.close()

        if response_data.get("success"):
            print("✅ Socket通信正常")
            return True
        else:
            print(f"❌ Socket通信失败: {response_data.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Socket通信异常: {e}")
        return False

def test_claude_codex_help():
    """测试claude-codex帮助功能"""
    print("🔧 测试4: claude-codex帮助功能")

    result = subprocess.run(['python3', 'claude-codex', '--help'],
                          capture_output=True, text=True, timeout=10)

    if result.returncode == 0 and "claude-codex" in result.stdout:
        print("✅ claude-codex帮助功能正常")
        return True
    else:
        print("❌ claude-codex帮助功能失败")
        return False

def test_daemon_stop():
    """测试守护进程停止"""
    print("🔧 测试5: 守护进程停止功能")

    # 读取PID
    with open('/tmp/codex-daemon.pid', 'r') as f:
        pid = int(f.read().strip())

    # 通过claude-codex停止
    wrapper = subprocess.Popen(['python3', '-c', '''
import sys
sys.path.insert(0, ".")
from claude_codex import ClaudeCodexWrapper
wrapper = ClaudeCodexWrapper()
wrapper.stop_daemon()
'''], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    wrapper.wait(timeout=10)

    time.sleep(1)

    # 检查进程是否已停止
    try:
        os.kill(pid, 0)
        print("❌ 守护进程仍在运行")
        return False
    except OSError:
        pass  # 进程已停止，这是期望的

    # 检查文件是否已清理
    if os.path.exists('/tmp/codex-daemon.pid'):
        print("❌ PID文件未清理")
        return False

    if os.path.exists('/tmp/codex-daemon.sock'):
        print("❌ Socket文件未清理")
        return False

    print("✅ 守护进程停止功能正常")
    return True

def main():
    """运行所有测试"""
    print("🚀 开始验证codex守护进程修复...")
    print("=" * 50)

    tests = [
        test_daemon_startup,
        test_health_check,
        test_socket_communication,
        test_claude_codex_help,
        test_daemon_stop
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            print()

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！修复验证成功！")
        return 0
    else:
        print("❌ 部分测试失败，需要进一步修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())