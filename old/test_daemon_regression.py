#!/usr/bin/env python3
"""
Codex 守护进程回归测试
验证所有关键修复是否正常工作
"""

import subprocess
import time
import os
import sys

def run_test(test_name, test_func):
    """运行单个测试并显示结果"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")

    success = False
    try:
        success = test_func()
        if success:
            print(f"✅ {test_name} - 通过")
        else:
            print(f"❌ {test_name} - 失败")
    except Exception as e:
        print(f"💥 {test_name} - 异常: {e}")

    print(f"{'='*60}")
    return success

def test_daemon_background_start():
    """测试1: 后台守护进程启动"""
    print("测试后台守护进程启动...")

    # 清理旧进程
    for f in ['/tmp/codex-daemon.pid', '/tmp/codex-daemon.sock']:
        if os.path.exists(f):
            os.unlink(f)

    # 启动后台守护进程
    result = subprocess.run(['python3', 'codex_daemon.py', '--daemon'],
                          timeout=10, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 守护进程启动失败，返回码: {result.returncode}")
        if result.stderr:
            print(f"错误: {result.stderr}")
        return False

    # 等待启动
    time.sleep(3)

    # 检查PID文件
    if not os.path.exists('/tmp/codex-daemon.pid'):
        print("❌ PID文件未创建")
        return False

    # 检查进程
    with open('/tmp/codex-daemon.pid', 'r') as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, 0)
        print(f"✅ 守护进程运行，PID: {pid}")
    except OSError:
        print("❌ 守护进程未运行")
        return False

    # 停止守护进程
    os.kill(pid, 15)
    time.sleep(1)

    print("✅ 测试1完成")
    return True

def test_health_check():
    """测试2: 健康检查功能"""
    print("测试健康检查功能...")

    # 确保守护进程运行
    if not os.path.exists('/tmp/codex-daemon.pid'):
        print("❌ 守护进程未运行，跳过健康检查测试")
        return False

    # 执行健康检查
    result = subprocess.run(['python3', 'codex_daemon.py', '--health'],
                          timeout=5, capture_output=True, text=True)

    success = result.returncode == 0
    print(f"健康检查返回码: {result.returncode}")
    print(f"健康检查输出: {result.stdout}")

    if result.stderr:
        print(f"健康检查错误: {result.stderr}")

    print("✅ 测试2完成")
    return success

def test_claude_codex_no_args():
    """测试3: claude-codex 无参数启动"""
    print("测试 claude-codex 无参数启动...")

    # 清理旧进程
    subprocess.run(['pkill', '-f', 'claude-codex'], shell=True)
    time.sleep(1)

    # 启动 claude-codex（无参数，应该启动交互模式）
    process = subprocess.Popen(['python3', 'claude-codex'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        # 等待2秒看是否还在运行
        time.sleep(2)

        if process.poll() is None:
            print("✅ claude-codex 进程正在运行")

            # 发送终止信号
            process.terminate()
            try:
                process.wait(timeout=3)
                print("✅ 进程正常终止")
            except subprocess.TimeoutExpired:
                process.kill()
                print("🔧 强制终止进程")

            return True
        else:
            print(f"❌ claude-codex 进程意外退出，返回码: {process.returncode}")
            return False

    except Exception as e:
        print(f"💥 测试异常: {e}")
        return False

def main():
    """主测试流程"""
    print("🚀 Codex 守护进程回归测试")
    print("="*60)

    tests = [
        ("后台守护进程启动", test_daemon_background_start),
        ("健康检查功能", test_health_check),
        ("claude-codex 无参数启动", test_claude_codex_no_args),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print(f"\n{'='*60}")
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("="*60)

    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())