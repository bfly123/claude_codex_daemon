#!/usr/bin/env python3
"""
简单测试脚本
"""

import subprocess
import time
import os

def test_basic():
    print("🧪 基础测试开始...")

    # 测试1: 直接启动守护进程
    print("\n1. 测试守护进程直接启动:")
    process = subprocess.Popen(["python3", "codex_daemon.py"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    print("   等待启动...")
    time.sleep(5)

    # 检查结果
    returncode = process.poll()
    if returncode is None:
        print("   ✅ 守护进程运行中")
        # 读取前几行日志
        try:
            stdout, stderr = process.communicate(timeout=2)
            if stdout:
                lines = stdout.strip().split('\n')[:5]
                for line in lines:
                    if line.strip():
                        print(f"   📝 {line}")
        except:
            pass
    else:
        print(f"   ❌ 守护进程退出，返回码: {returncode}")

    return returncode == 0

def test_connection():
    print("\n2. 测试Socket连接:")

    if os.path.exists("/tmp/codex-daemon.sock"):
        try:
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect("/tmp/codex-daemon.sock")
            sock.close()
            print("   ✅ Socket连接成功")
            return True
        except Exception as e:
            print(f"   ❌ Socket连接失败: {e}")
            return False
    else:
        print("   ❌ Socket文件不存在")
        return False

if __name__ == "__main__":
    success = test_basic()
    if success:
        test_connection()

    print(f"\n📊 测试完成，Socket文件状态: {os.path.exists('/tmp/codex-daemon.sock')}")